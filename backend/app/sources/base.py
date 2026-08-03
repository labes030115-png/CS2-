from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol, runtime_checkable


BLOCKED_SOURCE_CODES = frozenset({"STEAM"})


class BlockedSourceError(ValueError):
    """Raised when project policy forbids a price source."""


class SourceRole(StrEnum):
    PRIMARY = "primary"
    EXTERNAL_REFERENCE = "external_reference"


class PriceMetric(StrEnum):
    LOWEST_LISTING = "lowest_listing"


class SourceResolution(StrEnum):
    POINT = "point"
    FIFTEEN_MINUTES = "15m"
    HOUR = "1h"
    DAY = "1d"
    WEEK = "1w"


class Completeness(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    GAP = "gap"


def normalize_source_code(source_code: str) -> str:
    normalized = source_code.strip().upper()
    if not normalized:
        raise ValueError("source_code cannot be empty")
    if normalized in BLOCKED_SOURCE_CODES:
        raise BlockedSourceError(
            f"Source {normalized} is forbidden by project policy"
        )
    return normalized


def require_aware_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")


@dataclass(frozen=True, slots=True)
class SourceHealth:
    source_code: str
    is_available: bool
    checked_at: datetime
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_code",
            normalize_source_code(self.source_code),
        )
        require_aware_datetime(self.checked_at, "checked_at")


@dataclass(frozen=True, slots=True)
class SourceItem:
    source_code: str
    source_item_id: str
    display_name: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_code",
            normalize_source_code(self.source_code),
        )
        if not self.source_item_id.strip():
            raise ValueError("source_item_id cannot be empty")
        if not self.display_name.strip():
            raise ValueError("display_name cannot be empty")


@dataclass(frozen=True, slots=True)
class PriceObservation:
    source_code: str
    source_item_id: str
    observed_at: datetime
    currency: str
    metric: PriceMetric
    value: Decimal
    resolution: SourceResolution
    completeness: Completeness
    raw_reference: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_code",
            normalize_source_code(self.source_code),
        )
        require_aware_datetime(self.observed_at, "observed_at")
        normalized_currency = self.currency.strip().upper()
        if len(normalized_currency) != 3:
            raise ValueError("currency must be a three-letter code")
        object.__setattr__(self, "currency", normalized_currency)
        object.__setattr__(self, "metric", PriceMetric(self.metric))
        if not self.source_item_id.strip():
            raise ValueError("source_item_id cannot be empty")
        if self.value < 0:
            raise ValueError("price value cannot be negative")
        if not self.raw_reference.strip():
            raise ValueError("raw_reference cannot be empty")


@dataclass(frozen=True, slots=True)
class CurrentPrice(PriceObservation):
    pass


@dataclass(frozen=True, slots=True)
class HistoricalPoint(PriceObservation):
    pass


@runtime_checkable
class PriceSourceAdapter(Protocol):
    source_code: str
    role: SourceRole

    async def health_check(self) -> SourceHealth: ...

    async def fetch_catalog(self) -> list[SourceItem]: ...

    async def fetch_current_prices(
        self,
        external_ids: list[str],
    ) -> list[CurrentPrice]: ...

    async def fetch_historical_points(
        self,
        external_id: str,
        start: datetime,
        end: datetime,
    ) -> list[HistoricalPoint]: ...
