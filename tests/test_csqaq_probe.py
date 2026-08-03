import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal

from backend.app.sources.base import (
    Completeness,
    CurrentPrice,
    PriceMetric,
    SourceResolution,
)
from scripts.probe_csqaq import PROBE_TARGETS, run_probe


NOW = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)


class FakeCSQAQAdapter:
    def __init__(self, prices: list[CurrentPrice]) -> None:
        self.prices = prices
        self.requested_items: list[str] = []

    async def fetch_current_prices(
        self,
        external_ids: list[str],
    ) -> list[CurrentPrice]:
        self.requested_items = external_ids
        return self.prices


def current_price(item_name: str, value: str) -> CurrentPrice:
    return CurrentPrice(
        source_code="YYYP",
        source_item_id=item_name,
        observed_at=NOW,
        currency="CNY",
        metric=PriceMetric.LOWEST_LISTING,
        value=Decimal(value),
        resolution=SourceResolution.POINT,
        completeness=Completeness.COMPLETE,
        raw_reference="csqaq://yyyp/redacted",
    )


def test_probe_output_is_redacted_and_preserves_missing_items() -> None:
    returned_item = PROBE_TARGETS[0]["market_hash_name"]
    adapter = FakeCSQAQAdapter([current_price(returned_item, "12.34")])

    result = asyncio.run(run_probe(adapter, checked_at=NOW))

    assert adapter.requested_items == [
        target["market_hash_name"] for target in PROBE_TARGETS
    ]
    assert result["source_code"] == "YYYP"
    assert result["metric"] == "lowest_listing"
    assert result["requested_count"] == 3
    assert result["returned_count"] == 1
    assert result["targets"][0]["price_cny"] == "12.34"
    assert result["targets"][1]["status"] == "no_current_yyyp_listing"

    serialized = json.dumps(result, ensure_ascii=False)
    assert "test-token-must-never-leak" not in serialized
    assert "steamSellPrice" not in serialized
    assert "buffSellPrice" not in serialized
    assert "raw_reference" not in serialized
