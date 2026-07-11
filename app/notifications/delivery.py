import uuid
from datetime import datetime, timezone
from typing import Any

from app.notifications.deduplication import FingerprintDeduplicator
from app.notifications.discord import DiscordWebhook
from app.notifications.formatter import format_replay_overview, format_replay_timepoint, format_scan


class NotificationService:
    def __init__(self, settings: Any, repository: Any):
        self.repository = repository
        self.settings = settings
        self.discord = DiscordWebhook(settings.discord_webhook_url)
        self.dedup = FingerprintDeduplicator(settings.discord_cooldown_seconds)

    async def send_messages(self, messages: list[str], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = metadata or {}
        if not self.discord.enabled:
            result = {"delivery_id": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc), "channel": "discord", "status": "disabled", "message_count": 0, "metadata": metadata}
            await self.repository.save_notification(result)
            return result
        sent = 0
        error = None
        for message in messages:
            if not self.dedup.accept(message):
                continue
            ok, error = await self.discord.send(message, self.settings.discord_max_retries)
            if not ok:
                break
            sent += 1
        result = {"delivery_id": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc), "channel": "discord", "status": "sent" if error is None else "failed", "message_count": sent, "error": error, "metadata": metadata}
        await self.repository.save_notification(result)
        return result

    async def send_scan(self, result: dict[str, Any]) -> dict[str, Any]:
        return await self.send_messages(format_scan(result), {"scan_id": result.get("scan_id")})

    async def send_replay(self, job: dict[str, Any], include_all: bool) -> list[dict[str, Any]]:
        deliveries = [await self.send_messages(format_replay_overview(job), {"job_id": job.get("job_id")})]
        timepoints = job.get("results", [])[: self.settings.discord_max_timepoints]
        for timepoint in timepoints:
            deliveries.append(await self.send_messages(format_replay_timepoint(timepoint, include_all), {"job_id": job.get("job_id"), "timestamp": timepoint.get("aligned_time")}))
        return deliveries

