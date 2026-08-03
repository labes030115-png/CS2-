from typing import Literal, TypedDict

from fastapi import FastAPI

SERVICE_NAME = "cs2-collection-tracker"
SERVICE_VERSION = "0.1.0"


class HealthPayload(TypedDict):
    status: Literal["ok"]
    service: str
    version: str


app = FastAPI(
    title="CS2 收藏品价格研究看板",
    version=SERVICE_VERSION,
    redoc_url=None,
)


@app.get("/health", tags=["system"])
async def health_check() -> HealthPayload:
    """Report process health without contacting external services."""
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
    }
