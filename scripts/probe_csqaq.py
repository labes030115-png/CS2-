from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Protocol

from backend.app.sources.base import CurrentPrice


PROBE_TARGETS = (
    {
        "asset_kind": "target_skin",
        "market_hash_name": (
            "AK-47 | Consequence of the Jinn (Factory New)"
        ),
    },
    {
        "asset_kind": "case",
        "market_hash_name": "Fracture Case",
    },
    {
        "asset_kind": "knife",
        "market_hash_name": (
            "★ Huntsman Knife | Tiger Tooth (Factory New)"
        ),
    },
    {
        "asset_kind": "glove",
        "market_hash_name": "★ Sport Gloves | Vice (Minimal Wear)",
    },
)


class CurrentPriceFetcher(Protocol):
    async def fetch_current_prices(
        self,
        external_ids: list[str],
    ) -> list[CurrentPrice]: ...


def utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("probe timestamps must include timezone information")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


async def run_probe(
    adapter: CurrentPriceFetcher,
    *,
    checked_at: datetime | None = None,
) -> dict[str, object]:
    """Probe four approved samples and return a strictly redacted result."""
    request_names = [target["market_hash_name"] for target in PROBE_TARGETS]
    observations = await adapter.fetch_current_prices(request_names)
    by_name = {item.source_item_id: item for item in observations}

    targets: list[dict[str, object]] = []
    for target in PROBE_TARGETS:
        market_hash_name = target["market_hash_name"]
        observation = by_name.get(market_hash_name)
        result: dict[str, object] = {
            "asset_kind": target["asset_kind"],
            "market_hash_name": market_hash_name,
        }
        if observation is None:
            result["status"] = "no_current_yyyp_listing"
        else:
            result.update(
                {
                    "status": "available",
                    "price_cny": format(observation.value, "f"),
                    "observed_at_utc": utc_text(observation.observed_at),
                }
            )
        targets.append(result)

    probe_time = checked_at or datetime.now(timezone.utc)
    return {
        "source_code": "YYYP",
        "metric": "lowest_listing",
        "currency": "CNY",
        "checked_at_utc": utc_text(probe_time),
        "requested_count": len(PROBE_TARGETS),
        "returned_count": len(observations),
        "targets": targets,
    }


if __name__ == "__main__":
    from scripts.csqaq_local import main

    raise SystemExit(asyncio.run(main(("probe", "current"))))
