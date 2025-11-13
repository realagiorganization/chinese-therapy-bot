from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def healthcheck() -> dict[str, str]:
    """Lightweight health endpoint for liveness probes."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
