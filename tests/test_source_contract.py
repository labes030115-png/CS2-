import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from backend.app.sources.base import (
    BlockedSourceError,
    Completeness,
    CurrentPrice,
    HistoricalPoint,
    PriceMetric,
    PriceSourceAdapter,
    SourceItem,
    SourceResolution,
    SourceRole,
)
from backend.app.sources.mock import MockPriceSource


NOW = datetime(2026, 8, 3, 8, 0, tzinfo=timezone.utc)


def current_price(source_code: str, value: str) -> CurrentPrice:
    return CurrentPrice(
        source_code=source_code,
        source_item_id="ak47-test-fn",
        observed_at=NOW,
        currency="CNY",
        metric=PriceMetric.LOWEST_LISTING,
        value=Decimal(value),
        resolution=SourceResolution.POINT,
        completeness=Completeness.COMPLETE,
        raw_reference=f"mock://{source_code.lower()}/current/ak47-test-fn",
    )


def test_lowest_listing_is_the_only_supported_price_metric() -> None:
    assert list(PriceMetric) == [PriceMetric.LOWEST_LISTING]


def test_primary_and_external_adapters_keep_prices_separate() -> None:
    yyyp = MockPriceSource(
        source_code="YYYP",
        role=SourceRole.PRIMARY,
        items=[SourceItem("YYYP", "ak47-test-fn", "测试饰品")],
        current_prices=[current_price("YYYP", "1000")],
    )
    c5 = MockPriceSource(
        source_code="C5",
        role=SourceRole.EXTERNAL_REFERENCE,
        items=[SourceItem("C5", "ak47-test-fn", "测试饰品")],
        current_prices=[current_price("C5", "980")],
    )

    assert isinstance(yyyp, PriceSourceAdapter)
    assert asyncio.run(yyyp.fetch_current_prices(["ak47-test-fn"])) == [
        current_price("YYYP", "1000")
    ]
    assert asyncio.run(c5.fetch_current_prices(["ak47-test-fn"])) == [
        current_price("C5", "980")
    ]


def test_steam_source_is_rejected_before_collection() -> None:
    with pytest.raises(BlockedSourceError, match="STEAM"):
        MockPriceSource(source_code="steam", role=SourceRole.EXTERNAL_REFERENCE)


def test_price_observation_rejects_unsupported_metric() -> None:
    with pytest.raises(ValueError, match="highest_buy_order"):
        CurrentPrice(
            source_code="C5",
            source_item_id="ak47-test-fn",
            observed_at=NOW,
            currency="CNY",
            metric="highest_buy_order",  # type: ignore[arg-type]
            value=Decimal("980"),
            resolution=SourceResolution.POINT,
            completeness=Completeness.COMPLETE,
            raw_reference="mock://c5/current/ak47-test-fn",
        )


def test_mock_history_preserves_gaps_without_interpolation() -> None:
    points = [
        HistoricalPoint(
            source_code="YYYP",
            source_item_id="ak47-test-fn",
            observed_at=NOW,
            currency="CNY",
            metric=PriceMetric.LOWEST_LISTING,
            value=Decimal("1000"),
            resolution=SourceResolution.FIFTEEN_MINUTES,
            completeness=Completeness.COMPLETE,
            raw_reference="mock://yyyp/history/0",
        ),
        HistoricalPoint(
            source_code="YYYP",
            source_item_id="ak47-test-fn",
            observed_at=NOW + timedelta(minutes=30),
            currency="CNY",
            metric=PriceMetric.LOWEST_LISTING,
            value=Decimal("1010"),
            resolution=SourceResolution.FIFTEEN_MINUTES,
            completeness=Completeness.COMPLETE,
            raw_reference="mock://yyyp/history/2",
        ),
    ]
    adapter = MockPriceSource(
        source_code="YYYP",
        role=SourceRole.PRIMARY,
        historical_points={"ak47-test-fn": points},
    )

    result = asyncio.run(
        adapter.fetch_historical_points(
            "ak47-test-fn",
            NOW,
            NOW + timedelta(minutes=30),
        )
    )

    assert [point.observed_at for point in result] == [
        NOW,
        NOW + timedelta(minutes=30),
    ]
    assert NOW + timedelta(minutes=15) not in {
        point.observed_at for point in result
    }
