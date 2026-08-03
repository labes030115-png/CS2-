import asyncio
import json
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from backend.app.sources.base import PriceMetric, SourceRole
from backend.app.sources.csqaq import (
    CSQAQAdapter,
    CSQAQAuthenticationError,
    CSQAQConfig,
    CSQAQConfigurationError,
    CSQAQRateLimitError,
    CSQAQUnavailableError,
)


API_TOKEN = "test-token-must-never-leak"
BASE_URL = "https://api.csqaq.com/api/v1"
TEST_ITEM = "AWP | Snake Camo (Factory New)"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def config() -> CSQAQConfig:
    return CSQAQConfig(api_token=API_TOKEN, base_url=BASE_URL)


async def fetch_with_handler(handler, item_names=None):
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url=BASE_URL,
    ) as client:
        adapter = CSQAQAdapter(
            config(),
            client=client,
            minimum_interval_seconds=0,
        )
        return await adapter.fetch_current_prices(item_names or [TEST_ITEM])


def test_config_requires_environment_token_and_redacts_it() -> None:
    with pytest.raises(CSQAQConfigurationError, match="CSQAQ_TOKEN"):
        CSQAQConfig.from_env({})

    loaded = CSQAQConfig.from_env({"CSQAQ_TOKEN": API_TOKEN})

    assert loaded.api_token == API_TOKEN
    assert API_TOKEN not in repr(loaded)


def test_current_prices_only_expose_yyyp_lowest_listing() -> None:
    steam_only_item = "Steam-only response item"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/goods/getPriceByMarketHashName"
        assert request.headers["ApiToken"] == API_TOKEN
        assert json.loads(request.content) == {
            "marketHashNameList": [TEST_ITEM, steam_only_item]
        }
        return httpx.Response(
            200,
            json={
                "code": 200,
                "msg": "Success",
                "data": {
                    "success": {
                        TEST_ITEM: {
                            "goodId": 301,
                            "name": "AWP | 蛇窟迷彩",
                            "marketHashName": TEST_ITEM,
                            "yyypSellPrice": 1309.0,
                            "yyypBuyPrice": 1200.5,
                            "yyypSellNum": 35,
                            "buffSellPrice": 1340.0,
                            "steamSellPrice": 1947.77,
                        },
                        steam_only_item: {
                            "goodId": 999,
                            "marketHashName": steam_only_item,
                            "steamSellPrice": 100.0,
                        },
                    }
                },
            },
        )

    prices = asyncio.run(
        fetch_with_handler(handler, [TEST_ITEM, steam_only_item])
    )

    assert len(prices) == 1
    assert prices[0].source_code == "YYYP"
    assert prices[0].source_item_id == TEST_ITEM
    assert prices[0].metric is PriceMetric.LOWEST_LISTING
    assert prices[0].value == Decimal("1309.0")
    assert "steam" not in repr(prices).lower()
    assert API_TOKEN not in repr(prices)


def test_current_prices_skip_empty_nonpositive_and_failed_items() -> None:
    item_names = [
        "valid-item",
        "null-item",
        "zero-item",
        "negative-item",
        "failed-item",
    ]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 200,
                "msg": "Success",
                "data": {
                    "success": {
                        "valid-item": {
                            "goodId": 1,
                            "yyypSellPrice": 12.34,
                        },
                        "null-item": {
                            "goodId": 2,
                            "yyypSellPrice": None,
                        },
                        "zero-item": {
                            "goodId": 3,
                            "yyypSellPrice": 0,
                        },
                        "negative-item": {
                            "goodId": 4,
                            "yyypSellPrice": -1,
                        },
                    },
                    "error": ["failed-item"],
                },
            },
        )

    prices = asyncio.run(fetch_with_handler(handler, item_names))

    assert [price.source_item_id for price in prices] == ["valid-item"]
    assert prices[0].metric is PriceMetric.LOWEST_LISTING
    assert prices[0].value == Decimal("12.34")


def test_adapter_does_not_expose_unsupported_price_capability() -> None:
    adapter = CSQAQAdapter(config(), minimum_interval_seconds=0)

    assert not hasattr(adapter, "fetch_current_detail_prices")

    asyncio.run(adapter.aclose())


def test_adapter_is_primary_and_rejects_batches_over_fifty() -> None:
    adapter = CSQAQAdapter(config(), minimum_interval_seconds=0)

    assert adapter.source_code == "YYYP"
    assert adapter.role is SourceRole.PRIMARY
    with pytest.raises(ValueError, match="50"):
        asyncio.run(adapter.fetch_current_prices([f"item-{i}" for i in range(51)]))

    asyncio.run(adapter.aclose())


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, CSQAQAuthenticationError),
        (429, CSQAQRateLimitError),
        (503, CSQAQUnavailableError),
    ],
)
def test_http_errors_are_classified_without_leaking_token(
    status_code: int,
    error_type: type[Exception],
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={"code": status_code, "msg": f"rejected {API_TOKEN}"},
        )

    with pytest.raises(error_type) as caught:
        asyncio.run(fetch_with_handler(handler))

    assert API_TOKEN not in str(caught.value)


@pytest.mark.parametrize("http_status", [401, 403])
def test_ip_whitelist_errors_are_distinct_and_redacted(
    http_status: int,
) -> None:
    exposed_ip = "203.0.113.10"

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            http_status,
            json={
                "code": http_status,
                "msg": f"当前IP {exposed_ip} 不在白名单 {API_TOKEN}",
            },
        )

    with pytest.raises(CSQAQAuthenticationError) as caught:
        asyncio.run(fetch_with_handler(handler))

    assert type(caught.value).__name__ == "CSQAQIPAuthorizationError"
    assert exposed_ip not in str(caught.value)
    assert API_TOKEN not in str(caught.value)


def test_business_ip_whitelist_error_is_distinct() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 401, "msg": "IP白名单未绑定"},
        )

    with pytest.raises(CSQAQAuthenticationError) as caught:
        asyncio.run(fetch_with_handler(handler))

    assert type(caught.value).__name__ == "CSQAQIPAuthorizationError"


def test_redacted_current_price_sample_is_synthetic_and_secret_free() -> None:
    sample_path = (
        PROJECT_ROOT
        / "research"
        / "samples"
        / "csqaq_current_price_redacted.json"
    )
    sample_text = sample_path.read_text(encoding="utf-8")
    sample = json.loads(sample_text)

    assert sample["_meta"]["synthetic"] is True
    assert sample["_meta"]["metric"] == "lowest_listing"
    assert sample["response"]["data"]["error"] == ["EXAMPLE_MISSING"]
    assert "ApiToken" not in sample_text
    assert "Authorization" not in sample_text
    assert "Cookie" not in sample_text
    assert API_TOKEN not in sample_text


def test_timeout_becomes_unavailable_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(CSQAQUnavailableError, match="timed out"):
        asyncio.run(fetch_with_handler(handler))
