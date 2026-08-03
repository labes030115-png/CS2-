"""Create the initial CS2 collection and price schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
    )


def upgrade() -> None:
    """Create all version-one tables and indexes."""
    op.create_table(
        "taxonomy_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name_zh", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
        *timestamp_columns(),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_name", sa.String(length=200), nullable=False),
        sa.Column("yyyp_name", sa.String(length=200)),
        sa.Column("name_en", sa.String(length=200)),
        sa.Column("collection_kind", sa.String(length=80)),
        sa.Column("first_release_at", sa.DateTime(timezone=True)),
        sa.Column("current_status", sa.String(length=100)),
        sa.Column("description", sa.Text()),
        sa.Column("primary_source_confidence", sa.String(length=20)),
        *timestamp_columns(),
        sa.UniqueConstraint("canonical_name"),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("canonical_name", sa.String(length=240), nullable=False),
        sa.Column("yyyp_display_name", sa.String(length=240)),
        sa.Column("weapon_type", sa.String(length=80)),
        sa.Column("finish_name", sa.String(length=160)),
        sa.Column("wear", sa.String(length=40)),
        sa.Column("rarity", sa.String(length=40)),
        sa.Column(
            "is_souvenir",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_stattrak",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_gem_variant",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "is_template_variant",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("market_hash_name", sa.String(length=240)),
        sa.Column("collection_id", sa.Integer()),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "asset_type IN ('gun_skin', 'knife', 'glove', 'case')",
            name="ck_asset_type",
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_table(
        "collection_group_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("taxonomy_group_id", sa.Integer(), nullable=False),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("label_text", sa.String(length=200), nullable=False),
        sa.Column(
            "label_emphasis",
            sa.String(length=20),
            nullable=False,
            server_default="high",
        ),
        sa.Column(
            "is_visible",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["taxonomy_group_id"],
            ["taxonomy_groups.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "collection_id",
            "taxonomy_group_id",
            name="uq_collection_group_membership",
        ),
    )
    op.create_table(
        "source_item_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.String(length=20), nullable=False),
        sa.Column("external_item_id", sa.String(length=200), nullable=False),
        sa.Column("external_name", sa.String(length=240)),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "mapping_status",
            sa.String(length=30),
            nullable=False,
            server_default="verified",
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("raw_metadata_json", sa.Text()),
        sa.CheckConstraint(
            "upper(trim(source_code)) <> 'STEAM'",
            name="ck_mapping_no_steam",
        ),
        sa.CheckConstraint(
            "length(currency) = 3",
            name="ck_mapping_currency",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "source_code",
            "external_item_id",
            name="uq_source_external_item",
        ),
    )
    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.String(length=20), nullable=False),
        sa.Column("metric", sa.String(length=40), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("observed_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("listing_count", sa.Integer()),
        sa.Column("data_quality", sa.String(length=30), nullable=False),
        sa.Column(
            "is_backfilled",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("raw_reference", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.CheckConstraint(
            "upper(trim(source_code)) <> 'STEAM'",
            name="ck_snapshot_no_steam",
        ),
        sa.CheckConstraint(
            "metric = 'lowest_listing'",
            name="ck_snapshot_metric",
        ),
        sa.CheckConstraint(
            "price_minor >= 0",
            name="ck_snapshot_nonnegative_price",
        ),
        sa.CheckConstraint(
            "length(currency) = 3",
            name="ck_snapshot_currency",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_snapshot_asset_source_metric_observed",
        "price_snapshots",
        ["asset_id", "source_code", "metric", "observed_at_utc"],
    )
    op.create_index(
        "ix_snapshot_scheduled",
        "price_snapshots",
        ["scheduled_at_utc"],
    )
    op.create_index(
        "ix_snapshot_quality",
        "price_snapshots",
        ["data_quality"],
    )
    op.execute("PRAGMA user_version=1")


def downgrade() -> None:
    """Remove all version-one tables and reset SQLite's schema marker."""
    op.drop_index("ix_snapshot_quality", table_name="price_snapshots")
    op.drop_index("ix_snapshot_scheduled", table_name="price_snapshots")
    op.drop_index(
        "ix_snapshot_asset_source_metric_observed",
        table_name="price_snapshots",
    )
    op.drop_table("price_snapshots")
    op.drop_table("source_item_mappings")
    op.drop_table("collection_group_memberships")
    op.drop_table("assets")
    op.drop_table("collections")
    op.drop_table("taxonomy_groups")
    op.execute("PRAGMA user_version=0")
