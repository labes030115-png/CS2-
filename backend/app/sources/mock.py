from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone

from backend.app.sources.base import (
    CurrentPrice,
    HistoricalPoint,
    SourceHealth,
    SourceItem,
    SourceRole,
    normalize_source_code,
    require_aware_datetime,
)


class MockPriceSource:
    """Deterministic in-memory adapter used only by tests and development."""

    def __init__(
        self,
        *,
        source_code: str,
        role: SourceRole,
        items: Iterable[SourceItem] = (),
        current_prices: Iterable[CurrentPrice] = (),
        historical_points: Mapping[
            str,
            Iterable[HistoricalPoint],
        ]
        | None = None,
        is_available: bool = True,
    ) -> None:
        self.source_code = normalize_source_code(source_code)
        self.role = SourceRole(role)
        self._validate_role()
        self._items = tuple(items)
        self._current_prices = tuple(current_prices)
        self._historical_points = {
            external_id: tuple(points)
            for external_id, points in (historical_points or {}).items()
        }
        self._is_available = is_available
        self._validate_injected_sources()

    def _validate_role(self) -> None:
        if self.source_code == "YYYP" and self.role is not SourceRole.PRIMARY:
            raise ValueError("YYYP must use the primary source role")
        if self.source_code != "YYYP" and self.role is SourceRole.PRIMARY:
            raise ValueError("Only YYYP may use the primary source role")

    def _validate_injected_sources(self) -> None:
        records = [
            *self._items,
            *self._current_prices,
            *(
                point
                for points in self._historical_points.values()
                for point in points
            ),
        ]
        for record in records:
            if record.source_code != self.source_code:
                raise ValueError(
                    "Injected record source does not match adapter source"
                )

    async def health_check(self) -> SourceHealth:
        return SourceHealth(
            source_code=self.source_code,
            is_available=self._is_available,
            checked_at=datetime.now(timezone.utc),
            message=(
                "mock source available"
                if self._is_available
                else "mock source unavailable"
            ),
        )

    async def fetch_catalog(self) -> list[SourceItem]:
        return list(self._items)

    async def fetch_current_prices(
        self,
        external_ids: list[str],
    ) -> list[CurrentPrice]:
        requested = set(external_ids)
        return [
            price
            for price in self._current_prices
            if price.source_item_id in requested
        ]

    async def fetch_historical_points(
        self,
        external_id: str,
        start: datetime,
        end: datetime,
    ) -> list[HistoricalPoint]:
        require_aware_datetime(start, "start")
        require_aware_datetime(end, "end")
        if start > end:
            raise ValueError("start cannot be after end")
        return sorted(
            (
                point
                for point in self._historical_points.get(external_id, ())
                if start <= point.observed_at <= end
            ),
            key=lambda point: point.observed_at,
        )
