import copy
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.database.models import ReplayJob, ScanRun


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


class MemoryRepository:
    mode = "memory"

    def __init__(self):
        self.scans: list[dict[str, Any]] = []
        self.replays: dict[str, dict[str, Any]] = {}
        self.notifications: list[dict[str, Any]] = []
        self.backtests: dict[str, dict[str, Any]] = {}

    async def save_scan(self, result: dict[str, Any]) -> None:
        self.scans.append(copy.deepcopy(_json_safe(result)))
        self.scans = self.scans[-100:]

    async def latest_scan(self) -> dict[str, Any] | None:
        return copy.deepcopy(self.scans[-1]) if self.scans else None

    async def scan_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return copy.deepcopy(self.scans[-limit:][::-1])

    async def save_replay(self, job: dict[str, Any]) -> None:
        self.replays[job["job_id"]] = copy.deepcopy(_json_safe(job))

    async def get_replay(self, job_id: str) -> dict[str, Any] | None:
        value = self.replays.get(job_id)
        return copy.deepcopy(value) if value else None

    async def save_notification(self, delivery: dict[str, Any]) -> None:
        self.notifications.append(copy.deepcopy(_json_safe(delivery)))
        self.notifications = self.notifications[-200:]

    async def notification_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return copy.deepcopy(self.notifications[-limit:][::-1])

    async def save_backtest(self, result: dict[str, Any]) -> None:
        self.backtests[result["run_id"]] = copy.deepcopy(_json_safe(result))


class PostgresRepository(MemoryRepository):
    mode = "postgresql"

    def __init__(self, session_factory: Any):
        super().__init__()
        self.session_factory = session_factory

    async def save_scan(self, result: dict[str, Any]) -> None:
        await super().save_scan(result)
        payload = _json_safe(result)
        async with self.session_factory() as session:
            session.add(
                ScanRun(
                    scan_id=result["scan_id"], status=result["status"], started_at=result["started_at"],
                    finished_at=result.get("finished_at"), elapsed_seconds=result.get("elapsed_seconds"),
                    universe_total=result.get("universe_total", 0), payload=payload,
                )
            )
            await session.commit()

    async def save_replay(self, job: dict[str, Any]) -> None:
        await super().save_replay(job)
        async with self.session_factory() as session:
            existing = await session.get(ReplayJob, job["job_id"])
            if existing is None:
                session.add(ReplayJob(job_id=job["job_id"], status=job["status"], created_at=job["created_at"], payload=_json_safe(job)))
            else:
                existing.status = job["status"]
                existing.payload = _json_safe(job)
            await session.commit()

    async def try_advisory_lock(self, key: int = 20260711) -> bool:
        async with self.session_factory() as session:
            row = await session.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
            return bool(row.scalar())
