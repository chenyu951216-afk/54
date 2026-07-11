from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.dependencies import state_from_request
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health(request: Request) -> HealthResponse:
    state = state_from_request(request)
    return HealthResponse(
        status="ok", service=state.settings.app_name, timestamp=datetime.now(timezone.utc),
        database="connected" if state.repository.mode == "postgresql" else "memory", gate_api="configured", 
        discord="enabled" if state.notifier.discord.enabled else "disabled", scheduler="running" if state.scheduler and state.scheduler.running else "disabled",
    )

