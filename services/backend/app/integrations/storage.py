from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import aioboto3

from app.core.config import AppSettings


logger = logging.getLogger(__name__)


class ChatTranscriptStorage:
    """Persist chat transcripts to S3-compatible storage."""

    def __init__(self, settings: AppSettings):
        self._settings = settings

    async def persist_transcript(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        messages: list[dict[str, Any]],
    ) -> str | None:
        bucket = self._settings.s3_conversation_logs_bucket
        if not bucket:
            logger.debug("S3 conversation logs bucket absent; skipping transcript upload.")
            return None

        key_prefix = self._settings.s3_conversation_logs_prefix or "conversations/"
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key = f"{key_prefix.rstrip('/')}/{session_id}/{timestamp}.json"

        payload = {
            "session_id": str(session_id),
            "user_id": str(user_id),
            "exported_at": timestamp,
            "messages": messages,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        client_kwargs: dict[str, Any] = {}
        if self._settings.aws_region:
            client_kwargs["region_name"] = self._settings.aws_region
        if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = self._settings.aws_access_key_id.get_secret_value()
            client_kwargs["aws_secret_access_key"] = self._settings.aws_secret_access_key.get_secret_value()

        try:
            async with aioboto3.client("s3", **client_kwargs) as client:
                await client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=body,
                    ContentType="application/json",
                )
            logger.info("Persisted chat transcript to s3://%s/%s", bucket, key)
            return key
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Failed to persist chat transcript to S3", exc_info=exc)
            return None


class SummaryStorage:
    """Persist generated summaries to the configured summaries bucket."""

    def __init__(self, settings: AppSettings):
        self._settings = settings

    async def persist_daily_summary(
        self,
        *,
        user_id: UUID,
        summary_date: date,
        payload: dict[str, Any],
    ) -> str | None:
        return await self._put_object(
            key=f"daily/{user_id}/{summary_date.isoformat()}.json",
            body=payload,
        )

    async def persist_weekly_summary(
        self,
        *,
        user_id: UUID,
        week_start: date,
        payload: dict[str, Any],
    ) -> str | None:
        return await self._put_object(
            key=f"weekly/{user_id}/{week_start.isoformat()}.json",
            body=payload,
        )

    async def _put_object(self, *, key: str, body: dict[str, Any]) -> str | None:
        bucket = self._settings.s3_summaries_bucket
        if not bucket:
            logger.debug("S3 summaries bucket absent; skipping summary upload.")
            return None

        serialized = json.dumps(body, ensure_ascii=False).encode("utf-8")

        client_kwargs: dict[str, Any] = {}
        if self._settings.aws_region:
            client_kwargs["region_name"] = self._settings.aws_region
        if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = self._settings.aws_access_key_id.get_secret_value()
            client_kwargs["aws_secret_access_key"] = self._settings.aws_secret_access_key.get_secret_value()

        try:
            async with aioboto3.client("s3", **client_kwargs) as client:
                await client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=serialized,
                    ContentType="application/json",
                )
            logger.info("Persisted summary payload to s3://%s/%s", bucket, key)
            return key
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Failed to persist summary payload to S3", exc_info=exc)
            return None
