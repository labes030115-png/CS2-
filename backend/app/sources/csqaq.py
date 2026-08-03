from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from backend.app.sources.base import (
    Completeness,
    CurrentPrice,
    HistoricalPoint,
    PriceMetric,
    SourceHealth,
    SourceItem,
    SourceResolution,
    SourceRole,
)


DEFAULT_BASE_URL = "https://api.csqaq.com/api/v1"
DEFAULT_HEALTHCHECK_ITEM = "AWP | Snake Camo (Factory New)"
MAX_BATCH_SIZE = 50


class CSQAQError(RuntimeError):
    """Base error for safe CSQAQ adapter failures."""


class CSQAQConfigurationError(CSQAQError):
    """Raised when local CSQAQ configuration is invalid or incomplete."""


class CSQAQAuthenticationError(CSQAQError):
    """Raised when the token or IP authorization is rejected."""


class CSQAQIPAuthorizationError(CSQAQAuthenticationError):
    """Raised when CSQAQ rejects the caller's bound IP address."""


class CSQAQRateLimitError(CSQAQError):
    """Raised when CSQAQ rejects a request for excessive frequency."""


class CSQAQUnavailableError(CSQAQError):
    """Raised for timeouts, connection failures, and server errors."""


class CSQAQResponseError(CSQAQError):
    """Raised when a response does not match the documented contract."""


class CSQAQCapabilityUnavailableError(CSQAQError):
    """Raised for capabilities not yet validated for ordinary access."""


@dataclass(frozen=True, slots=True)
class CSQAQConfig:
    api_token: str = field(repr=False)
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 10.0
    healthcheck_item: str = DEFAULT_HEALTHCHECK_ITEM

    def __post_init__(self) -> None:
        token = self.api_token.strip()
        if not token:
            raise CSQAQConfigurationError(
                "CSQAQ_TOKEN is required and cannot be empty"
            )
        base_url = self.base_url.strip().rstrip("/")
        parsed_url = httpx.URL(base_url)
        if parsed_url.scheme != "https" or not parsed_url.host:
            raise CSQAQConfigurationError(
                "CSQAQ base URL must be an absolute HTTPS URL"
            )
        if self.timeout_seconds <= 0:
            raise CSQAQConfigurationError(
                "CSQAQ timeout must be greater than zero"
            )
        healthcheck_item = self.healthcheck_item.strip()
        if not healthcheck_item:
            raise CSQAQConfigurationError(
                "CSQAQ health-check item cannot be empty"
            )
        object.__setattr__(self, "api_token", token)
        object.__setattr__(self, "base_url", base_url)
        object.__setattr__(self, "healthcheck_item", healthcheck_item)

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> CSQAQConfig:
        values = os.environ if environ is None else environ
        raw_timeout = values.get("CSQAQ_TIMEOUT_SECONDS", "10")
        try:
            timeout_seconds = float(raw_timeout)
        except ValueError as exc:
            raise CSQAQConfigurationError(
                "CSQAQ_TIMEOUT_SECONDS must be a number"
            ) from exc
        return cls(
            api_token=values.get("CSQAQ_TOKEN", ""),
            base_url=values.get("CSQAQ_BASE_URL", DEFAULT_BASE_URL),
            timeout_seconds=timeout_seconds,
            healthcheck_item=values.get(
                "CSQAQ_HEALTHCHECK_ITEM",
                DEFAULT_HEALTHCHECK_ITEM,
            ),
        )


class CSQAQAdapter:
    """Ordinary-access CSQAQ adapter restricted to YYYP primary prices."""

    source_code = "YYYP"
    role = SourceRole.PRIMARY

    def __init__(
        self,
        config: CSQAQConfig | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        minimum_interval_seconds: float = 1.0,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        if minimum_interval_seconds < 0:
            raise ValueError("minimum_interval_seconds cannot be negative")
        self._config = config or CSQAQConfig.from_env()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=f"{self._config.base_url}/",
            timeout=self._config.timeout_seconds,
            headers={"Accept": "application/json"},
        )
        self._minimum_interval_seconds = minimum_interval_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._monotonic = monotonic or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._request_lock = asyncio.Lock()
        self._last_request_started_at: float | None = None

    async def __aenter__(self) -> CSQAQAdapter:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def health_check(self) -> SourceHealth:
        checked_at = self._aware_now()
        try:
            await self.fetch_current_prices([self._config.healthcheck_item])
        except CSQAQError as exc:
            return SourceHealth(
                source_code=self.source_code,
                is_available=False,
                checked_at=checked_at,
                message=str(exc),
            )
        return SourceHealth(
            source_code=self.source_code,
            is_available=True,
            checked_at=checked_at,
            message="CSQAQ ordinary-access endpoint is available",
        )

    async def fetch_catalog(self) -> list[SourceItem]:
        raise CSQAQCapabilityUnavailableError(
            "CSQAQ catalog access has not been validated for ordinary accounts"
        )

    async def fetch_current_prices(
        self,
        external_ids: list[str],
    ) -> list[CurrentPrice]:
        item_names = self._validate_item_names(external_ids)
        if not item_names:
            return []
        envelope = await self._post(
            "goods/getPriceByMarketHashName",
            {"marketHashNameList": item_names},
        )
        data = envelope.get("data")
        if not isinstance(data, dict):
            raise CSQAQResponseError("CSQAQ response data must be an object")
        successful = data.get("success", {})
        if not isinstance(successful, dict):
            raise CSQAQResponseError(
                "CSQAQ response success field must be an object"
            )

        observed_at = self._aware_now()
        prices: list[CurrentPrice] = []
        for item_name in item_names:
            item = successful.get(item_name)
            if not isinstance(item, dict):
                continue
            price = self._yyyp_sell_price(item)
            if price is None:
                continue
            good_id = item.get("goodId")
            reference_id = str(good_id) if good_id is not None else "unknown"
            prices.append(
                CurrentPrice(
                    source_code=self.source_code,
                    source_item_id=item_name,
                    observed_at=observed_at,
                    currency="CNY",
                    metric=PriceMetric.LOWEST_LISTING,
                    value=price,
                    resolution=SourceResolution.POINT,
                    completeness=Completeness.COMPLETE,
                    raw_reference=(
                        f"csqaq://yyyp/goods/{reference_id}/sell-price"
                    ),
                )
            )
        return prices

    async def fetch_historical_points(
        self,
        external_id: str,
        start: datetime,
        end: datetime,
    ) -> list[HistoricalPoint]:
        raise CSQAQCapabilityUnavailableError(
            "CSQAQ historical access is deferred until its platform and period "
            "parameters are verified with an ordinary account"
        )

    async def _post(
        self,
        path: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        await self._wait_for_request_slot()
        try:
            response = await self._client.post(
                path,
                headers={"ApiToken": self._config.api_token},
                json=body,
            )
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            raise CSQAQUnavailableError(
                "CSQAQ request timed out or could not connect"
            ) from exc

        if response.status_code < 200 or response.status_code >= 300:
            self._raise_for_status(
                response.status_code,
                self._response_message(response),
            )
        try:
            envelope = response.json()
        except ValueError as exc:
            raise CSQAQResponseError(
                "CSQAQ response was not valid JSON"
            ) from exc
        if not isinstance(envelope, dict):
            raise CSQAQResponseError("CSQAQ response must be an object")
        code = envelope.get("code")
        if code != 200:
            if isinstance(code, int):
                message = envelope.get("msg")
                self._raise_for_status(
                    code,
                    message if isinstance(message, str) else None,
                )
            raise CSQAQResponseError(
                "CSQAQ response did not contain a successful status code"
            )
        return envelope

    async def _wait_for_request_slot(self) -> None:
        async with self._request_lock:
            now = self._monotonic()
            if self._last_request_started_at is not None:
                wait_seconds = (
                    self._last_request_started_at
                    + self._minimum_interval_seconds
                    - now
                )
                if wait_seconds > 0:
                    await self._sleep(wait_seconds)
                    now += wait_seconds
            self._last_request_started_at = now

    def _aware_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise CSQAQConfigurationError(
                "CSQAQ adapter clock must return a timezone-aware datetime"
            )
        return value

    @staticmethod
    def _validate_item_names(external_ids: list[str]) -> list[str]:
        if len(external_ids) > MAX_BATCH_SIZE:
            raise ValueError("CSQAQ batches cannot contain more than 50 items")
        normalized: list[str] = []
        for item_name in external_ids:
            stripped = item_name.strip()
            if not stripped:
                raise ValueError("CSQAQ item names cannot be empty")
            normalized.append(stripped)
        return normalized

    @staticmethod
    def _yyyp_sell_price(item: dict[str, Any]) -> Decimal | None:
        return CSQAQAdapter._positive_decimal(
            item,
            "yyypSellPrice",
            "CSQAQ YYYP sell price",
        )

    @staticmethod
    def _positive_decimal(
        item: dict[str, Any],
        field_name: str,
        label: str,
    ) -> Decimal | None:
        raw_price = item.get(field_name)
        if raw_price is None or isinstance(raw_price, bool):
            return None
        try:
            price = Decimal(str(raw_price))
        except (InvalidOperation, ValueError) as exc:
            raise CSQAQResponseError(f"{label} was not numeric") from exc
        if not price.is_finite():
            raise CSQAQResponseError(f"{label} must be finite")
        if price <= 0:
            return None
        return price

    @staticmethod
    def _response_message(response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        message = payload.get("msg")
        return message if isinstance(message, str) else None

    @staticmethod
    def _is_ip_authorization_message(message: str | None) -> bool:
        if not message:
            return False
        normalized = message.casefold()
        return "ip" in normalized and any(
            marker in normalized for marker in ("白名单", "绑定", "授权")
        )

    @staticmethod
    def _raise_for_status(
        status_code: int,
        message: str | None = None,
    ) -> None:
        if status_code in {400, 401, 403}:
            if CSQAQAdapter._is_ip_authorization_message(message):
                raise CSQAQIPAuthorizationError(
                    "CSQAQ IP authorization or whitelist binding failed"
                )
            raise CSQAQAuthenticationError(
                "CSQAQ token authentication failed"
            )
        if status_code == 429:
            raise CSQAQRateLimitError("CSQAQ request rate limit exceeded")
        if status_code >= 500:
            raise CSQAQUnavailableError(
                f"CSQAQ service is unavailable (status {status_code})"
            )
        raise CSQAQResponseError(
            f"CSQAQ request failed (status {status_code})"
        )
