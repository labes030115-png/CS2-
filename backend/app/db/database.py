from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    func,
)
from sqlalchemy.engine import Engine, URL


SCHEMA_VERSION = 1
metadata = MetaData()


def timestamp_columns() -> tuple[Column, Column]:
    return (
        Column(
            "created_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.current_timestamp(),
        ),
        Column(
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.current_timestamp(),
        ),
    )


taxonomy_groups = Table(
    "taxonomy_groups",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("code", String(80), nullable=False, unique=True),
    Column("name_zh", String(160), nullable=False),
    Column("description", Text),
    Column("display_order", Integer, nullable=False, server_default="0"),
    Column("is_active", Boolean, nullable=False, server_default="1"),
    *timestamp_columns(),
)

collections = Table(
    "collections",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("canonical_name", String(200), nullable=False, unique=True),
    Column("yyyp_name", String(200)),
    Column("name_en", String(200)),
    Column("collection_kind", String(80)),
    Column("first_release_at", DateTime(timezone=True)),
    Column("current_status", String(100)),
    Column("description", Text),
    Column("primary_source_confidence", String(20)),
    *timestamp_columns(),
)

collection_group_memberships = Table(
    "collection_group_memberships",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "collection_id",
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "taxonomy_group_id",
        ForeignKey("taxonomy_groups.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("display_order", Integer, nullable=False, server_default="0"),
    Column("label_text", String(200), nullable=False),
    Column("label_emphasis", String(20), nullable=False, server_default="high"),
    Column("is_visible", Boolean, nullable=False, server_default="1"),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    ),
    UniqueConstraint(
        "collection_id",
        "taxonomy_group_id",
        name="uq_collection_group_membership",
    ),
)

assets = Table(
    "assets",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("asset_type", String(20), nullable=False),
    Column("canonical_name", String(240), nullable=False),
    Column("yyyp_display_name", String(240)),
    Column("weapon_type", String(80)),
    Column("finish_name", String(160)),
    Column("wear", String(40)),
    Column("rarity", String(40)),
    Column("is_souvenir", Boolean, nullable=False, server_default="0"),
    Column("is_stattrak", Boolean, nullable=False, server_default="0"),
    Column("is_gem_variant", Boolean, nullable=False, server_default="0"),
    Column("is_template_variant", Boolean, nullable=False, server_default="0"),
    Column("market_hash_name", String(240)),
    Column("collection_id", ForeignKey("collections.id", ondelete="SET NULL")),
    Column("active", Boolean, nullable=False, server_default="1"),
    CheckConstraint(
        "asset_type IN ('gun_skin', 'knife', 'glove', 'case')",
        name="ck_asset_type",
    ),
    *timestamp_columns(),
)

source_item_mappings = Table(
    "source_item_mappings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "asset_id",
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("source_code", String(20), nullable=False),
    Column("external_item_id", String(200), nullable=False),
    Column("external_name", String(240)),
    Column("currency", String(3), nullable=False),
    Column("mapping_status", String(30), nullable=False, server_default="verified"),
    Column("verified_at", DateTime(timezone=True)),
    Column("raw_metadata_json", Text),
    CheckConstraint(
        "upper(trim(source_code)) <> 'STEAM'",
        name="ck_mapping_no_steam",
    ),
    CheckConstraint("length(currency) = 3", name="ck_mapping_currency"),
    UniqueConstraint(
        "source_code",
        "external_item_id",
        name="uq_source_external_item",
    ),
)

price_snapshots = Table(
    "price_snapshots",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "asset_id",
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("source_code", String(20), nullable=False),
    Column("metric", String(40), nullable=False),
    Column("price_minor", Integer, nullable=False),
    Column("currency", String(3), nullable=False),
    Column("observed_at_utc", DateTime(timezone=True), nullable=False),
    Column("scheduled_at_utc", DateTime(timezone=True), nullable=False),
    Column("listing_count", Integer),
    Column("data_quality", String(30), nullable=False),
    Column("is_backfilled", Boolean, nullable=False, server_default="0"),
    Column("raw_reference", String(500), nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
    ),
    CheckConstraint(
        "upper(trim(source_code)) <> 'STEAM'",
        name="ck_snapshot_no_steam",
    ),
    CheckConstraint(
        "metric = 'lowest_listing'",
        name="ck_snapshot_metric",
    ),
    CheckConstraint("price_minor >= 0", name="ck_snapshot_nonnegative_price"),
    CheckConstraint("length(currency) = 3", name="ck_snapshot_currency"),
)

Index(
    "ix_snapshot_asset_source_metric_observed",
    price_snapshots.c.asset_id,
    price_snapshots.c.source_code,
    price_snapshots.c.metric,
    price_snapshots.c.observed_at_utc,
)
Index("ix_snapshot_scheduled", price_snapshots.c.scheduled_at_utc)
Index("ix_snapshot_quality", price_snapshots.c.data_quality)


def create_sqlite_engine(database_path: str | Path) -> Engine:
    resolved_path = Path(database_path).resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(resolved_path)),
        future=True,
    )

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()

    return engine


def initialize_database(engine: Engine) -> None:
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(f"PRAGMA user_version={SCHEMA_VERSION}")
