from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError

from backend.app.db.database import (
    assets,
    collection_group_memberships,
    collections,
    create_sqlite_engine,
    initialize_database,
    price_snapshots,
    source_item_mappings,
    taxonomy_groups,
)


NOW = datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc)


def initialized_engine(database_path: Path):
    engine = create_sqlite_engine(database_path)
    initialize_database(engine)
    return engine


def test_initial_schema_enables_sqlite_safety_pragmas(tmp_path: Path) -> None:
    engine = initialized_engine(tmp_path / "tracker.sqlite3")

    with engine.connect() as connection:
        table_names = {
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        journal_mode = connection.exec_driver_sql(
            "PRAGMA journal_mode"
        ).scalar_one()
        foreign_keys = connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar_one()
        schema_version = connection.exec_driver_sql(
            "PRAGMA user_version"
        ).scalar_one()

    assert {
        "taxonomy_groups",
        "collections",
        "collection_group_memberships",
        "assets",
        "source_item_mappings",
        "price_snapshots",
    }.issubset(table_names)
    assert journal_mode == "wal"
    assert foreign_keys == 1
    assert schema_version == 1


def test_collection_can_repeat_across_groups_without_duplicate_asset(
    tmp_path: Path,
) -> None:
    engine = initialized_engine(tmp_path / "tracker.sqlite3")

    with engine.begin() as connection:
        group_ids = []
        for code, name in (
            ("operation", "大行动系列"),
            ("active-map", "比赛地图系列"),
        ):
            group_ids.append(
                connection.execute(
                    insert(taxonomy_groups)
                    .values(code=code, name_zh=name)
                    .returning(taxonomy_groups.c.id)
                ).scalar_one()
            )
        collection_id = connection.execute(
            insert(collections)
            .values(canonical_name="Ancient Collection")
            .returning(collections.c.id)
        ).scalar_one()
        asset_id = connection.execute(
            insert(assets)
            .values(
                asset_type="gun_skin",
                canonical_name="Test Asset",
                collection_id=collection_id,
            )
            .returning(assets.c.id)
        ).scalar_one()
        for group_id in group_ids:
            connection.execute(
                insert(collection_group_memberships).values(
                    collection_id=collection_id,
                    taxonomy_group_id=group_id,
                    label_text="醒目来源标签",
                )
            )
        connection.execute(
            insert(source_item_mappings).values(
                asset_id=asset_id,
                source_code="YYYP",
                external_item_id="test-asset-fn",
                currency="CNY",
            )
        )

        asset_count = connection.scalar(
            select(func.count()).select_from(assets)
        )
        membership_count = connection.scalar(
            select(func.count()).select_from(collection_group_memberships)
        )

    assert asset_count == 1
    assert membership_count == 2


@pytest.mark.parametrize("source_code", ["STEAM", "steam", " steam "])
def test_database_rejects_steam_price_source(
    tmp_path: Path,
    source_code: str,
) -> None:
    engine = initialized_engine(tmp_path / "tracker.sqlite3")

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            asset_id = connection.execute(
                insert(assets)
                .values(asset_type="case", canonical_name="Test Case")
                .returning(assets.c.id)
            ).scalar_one()
            connection.execute(
                insert(price_snapshots).values(
                    asset_id=asset_id,
                    source_code=source_code,
                    metric="lowest_listing",
                    price_minor=100,
                    currency="CNY",
                    observed_at_utc=NOW,
                    scheduled_at_utc=NOW,
                    data_quality="complete",
                    raw_reference="forbidden://steam/test",
                )
            )


def test_database_rejects_unsupported_price_metric(tmp_path: Path) -> None:
    engine = initialized_engine(tmp_path / "tracker.sqlite3")

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            asset_id = connection.execute(
                insert(assets)
                .values(asset_type="case", canonical_name="Metric Test Case")
                .returning(assets.c.id)
            ).scalar_one()
            connection.execute(
                insert(price_snapshots).values(
                    asset_id=asset_id,
                    source_code="YYYP",
                    metric="highest_buy_order",
                    price_minor=100,
                    currency="CNY",
                    observed_at_utc=NOW,
                    scheduled_at_utc=NOW,
                    data_quality="complete",
                    raw_reference="test://unsupported-metric",
                )
            )


def test_database_accepts_lowest_listing_snapshot(tmp_path: Path) -> None:
    engine = initialized_engine(tmp_path / "tracker.sqlite3")

    with engine.begin() as connection:
        asset_id = connection.execute(
            insert(assets)
            .values(asset_type="case", canonical_name="Listing Test Case")
            .returning(assets.c.id)
        ).scalar_one()
        connection.execute(
            insert(price_snapshots).values(
                asset_id=asset_id,
                source_code="YYYP",
                metric="lowest_listing",
                price_minor=100,
                currency="CNY",
                observed_at_utc=NOW,
                scheduled_at_utc=NOW,
                data_quality="complete",
                raw_reference="test://lowest-listing",
            )
        )
        stored_metrics = connection.scalars(
            select(price_snapshots.c.metric)
        ).all()

    assert stored_metrics == ["lowest_listing"]
