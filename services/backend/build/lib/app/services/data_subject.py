from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID

import aioboto3
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import AppSettings
from app.models.entities import (
    AnalyticsEvent,
    ChatMessage,
    ChatSession,
    ConversationMemory,
    DailySummary,
    LoginChallenge,
    RefreshToken,
    User,
    WeeklySummary,
)
from app.schemas.data_subject import (
    DataDeletionReport,
    DataSubjectExport,
    ExportAnalyticsEvent,
    ExportChatMessage,
    ExportChatSession,
    ExportConversationMemory,
    ExportDailySummary,
    ExportUserProfile,
    ExportWeeklySummary,
    UserMatch,
)


logger = logging.getLogger(__name__)


class StorageRetentionClient(Protocol):
    """Interface for deleting stored conversation artefacts."""

    async def delete_transcripts(self, session_ids: Sequence[UUID]) -> int:
        ...

    async def delete_summaries(self, user_id: UUID) -> int:
        ...


class S3RetentionClient:
    """S3-backed implementation for transcript and summary cleanup."""

    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._client_kwargs: dict[str, str] = {}
        if settings.aws_region:
            self._client_kwargs["region_name"] = settings.aws_region
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            self._client_kwargs["aws_access_key_id"] = (
                settings.aws_access_key_id.get_secret_value()
            )
            self._client_kwargs["aws_secret_access_key"] = (
                settings.aws_secret_access_key.get_secret_value()
            )

    async def delete_transcripts(self, session_ids: Sequence[UUID]) -> int:
        bucket = self._settings.s3_conversation_logs_bucket
        if not bucket or not session_ids:
            return 0

        prefix_root = self._settings.s3_conversation_logs_prefix or "conversations/"
        total_deleted = 0
        async with aioboto3.client("s3", **self._client_kwargs) as client:
            for session_id in session_ids:
                prefix = f"{prefix_root.rstrip('/')}/{session_id}/"
                total_deleted += await self._delete_prefix(client, bucket, prefix)
        return total_deleted

    async def delete_summaries(self, user_id: UUID) -> int:
        bucket = self._settings.s3_summaries_bucket
        if not bucket:
            return 0

        prefixes = (
            f"daily/{user_id}/",
            f"weekly/{user_id}/",
        )
        total_deleted = 0
        async with aioboto3.client("s3", **self._client_kwargs) as client:
            for prefix in prefixes:
                total_deleted += await self._delete_prefix(client, bucket, prefix)
        return total_deleted

    async def _delete_prefix(self, client: Any, bucket: str, prefix: str) -> int:
        """Delete all objects under the supplied prefix."""
        deleted = 0
        continuation: str | None = None
        while True:
            kwargs = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
            if continuation:
                kwargs["ContinuationToken"] = continuation
            response = await client.list_objects_v2(**kwargs)
            objects = [
                {"Key": obj["Key"]}
                for obj in response.get("Contents", [])
                if obj.get("Key")
            ]
            if objects:
                await client.delete_objects(Bucket=bucket, Delete={"Objects": objects})
                deleted += len(objects)
            if not response.get("IsTruncated"):
                break
            continuation = response.get("NextContinuationToken")
        if deleted:
            logger.info("Deleted %s objects from s3://%s/%s", deleted, bucket, prefix)
        else:
            logger.debug("No objects found for s3://%s/%s", bucket, prefix)
        return deleted


class DataSubjectService:
    """Implements SAR export and deletion workflows for MindWell data subjects."""

    def __init__(
        self,
        session: AsyncSession,
        settings: AppSettings,
        storage_client: StorageRetentionClient | None = None,
    ):
        self._session = session
        self._settings = settings
        self._storage_client = storage_client or S3RetentionClient(settings)

    async def find_user(
        self,
        *,
        user_id: UUID | None = None,
        email: str | None = None,
        phone_number: str | None = None,
        external_id: str | None = None,
    ) -> list[UserMatch]:
        filters = []
        if user_id:
            filters.append(User.id == user_id)
        if email:
            filters.append(User.email == email)
        if phone_number:
            filters.append(User.phone_number == phone_number)
        if external_id:
            filters.append(User.external_id == external_id)

        if not filters:
            raise ValueError("At least one identifier must be provided.")

        stmt = select(User).where(*filters)
        result = await self._session.execute(stmt)
        users = result.scalars().all()
        return [UserMatch.model_validate(user, from_attributes=True) for user in users]

    async def export_user_data(self, user_id: UUID) -> DataSubjectExport:
        user = await self._session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")

        sessions_stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
            .order_by(ChatSession.started_at)
        )
        sessions_result = await self._session.execute(sessions_stmt)
        sessions = sessions_result.scalars().all()

        daily_stmt = (
            select(DailySummary)
            .where(DailySummary.user_id == user_id)
            .order_by(DailySummary.summary_date)
        )
        daily_summaries = (await self._session.execute(daily_stmt)).scalars().all()

        weekly_summaries: list[WeeklySummary] = []
        try:
            weekly_stmt = (
                select(WeeklySummary)
                .where(WeeklySummary.user_id == user_id)
                .order_by(WeeklySummary.week_start)
            )
            weekly_summaries = (
                await self._session.execute(weekly_stmt)
            ).scalars().all()
        except SQLAlchemyError as exc:  # pragma: no cover - sqlite fallback
            logger.debug("Skipping weekly summaries during export: %s", exc)

        memories_stmt = (
            select(ConversationMemory)
            .where(ConversationMemory.user_id == user_id)
            .order_by(ConversationMemory.last_message_at.desc())
        )
        conversation_memories = (
            await self._session.execute(memories_stmt)
        ).scalars().all()

        analytics_stmt = (
            select(AnalyticsEvent)
            .where(AnalyticsEvent.user_id == user_id)
            .order_by(AnalyticsEvent.occurred_at)
        )
        analytics_events = (
            await self._session.execute(analytics_stmt)
        ).scalars().all()

        export = DataSubjectExport(
            user=ExportUserProfile.model_validate(user, from_attributes=True),
            sessions=[
                ExportChatSession(
                    id=session.id,
                    sessionState=session.session_state,
                    startedAt=session.started_at,
                    updatedAt=session.updated_at,
                    therapistId=session.therapist_id,
                    messages=[
                        ExportChatMessage.model_validate(message, from_attributes=True)
                        for message in sorted(
                            session.messages, key=lambda msg: msg.sequence_index
                        )
                    ],
                )
                for session in sessions
            ],
            dailySummaries=[
                ExportDailySummary.model_validate(summary, from_attributes=True)
                for summary in daily_summaries
            ],
            weeklySummaries=[
                ExportWeeklySummary.model_validate(summary, from_attributes=True)
                for summary in weekly_summaries
            ],
            conversationMemories=[
                ExportConversationMemory.model_validate(memory, from_attributes=True)
                for memory in conversation_memories
            ],
            analyticsEvents=[
                ExportAnalyticsEvent.model_validate(event, from_attributes=True)
                for event in analytics_events
            ],
        )
        return export

    async def delete_user_data(
        self,
        user_id: UUID,
        *,
        redaction_token: str = "[redacted]",
        anonymise_timestamp: datetime | None = None,
    ) -> DataDeletionReport:
        user = await self._session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found.")

        anonymised_at = anonymise_timestamp or datetime.now(tz=timezone.utc)

        pii_fields_cleared: list[str] = []
        for field in ("email", "phone_number", "display_name", "external_id"):
            if getattr(user, field) is not None:
                setattr(user, field, None)
                pii_fields_cleared.append(field)

        messages_stmt = (
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id)
        )
        messages = (await self._session.execute(messages_stmt)).scalars().all()
        sessions_impacted = {message.session_id for message in messages}
        for message in messages:
            message.content = redaction_token
        messages_redacted = len(messages)

        daily_stmt = select(DailySummary).where(DailySummary.user_id == user_id)
        daily_summaries = (await self._session.execute(daily_stmt)).scalars().all()
        daily_deleted = len(daily_summaries)
        for summary in daily_summaries:
            await self._session.delete(summary)

        weekly_deleted = 0
        try:
            weekly_stmt = select(WeeklySummary).where(WeeklySummary.user_id == user_id)
            weekly_summaries = (
                await self._session.execute(weekly_stmt)
            ).scalars().all()
            weekly_deleted = len(weekly_summaries)
            for summary in weekly_summaries:
                await self._session.delete(summary)
        except SQLAlchemyError as exc:  # pragma: no cover - sqlite fallback
            logger.debug("Skipping weekly summary deletion: %s", exc)

        memories_stmt = select(ConversationMemory).where(
            ConversationMemory.user_id == user_id
        )
        memories = (await self._session.execute(memories_stmt)).scalars().all()
        memories_deleted = len(memories)
        for memory in memories:
            await self._session.delete(memory)

        analytics_stmt = select(AnalyticsEvent).where(
            AnalyticsEvent.user_id == user_id
        )
        analytics_events = (await self._session.execute(analytics_stmt)).scalars().all()
        analytics_anonymised = len(analytics_events)
        for event in analytics_events:
            event.user_id = None
            event.session_id = None
            props = dict(event.properties or {})
            props["anonymised_at"] = anonymised_at.isoformat()
            event.properties = props

        refresh_tokens_stmt = (
            select(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        refresh_tokens = (
            await self._session.execute(refresh_tokens_stmt)
        ).scalars().all()
        refresh_tokens_revoked = len(refresh_tokens)
        for token in refresh_tokens:
            await self._session.delete(token)

        login_stmt = select(LoginChallenge).where(LoginChallenge.user_id == user_id)
        login_challenges = (
            await self._session.execute(login_stmt)
        ).scalars().all()
        for challenge in login_challenges:
            challenge.phone_number = None
            challenge.payload = None

        transcripts_deleted = 0
        summaries_deleted = 0
        try:
            transcripts_deleted = await self._storage_client.delete_transcripts(
                sorted(sessions_impacted)
            )
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Failed to delete transcript objects: %s", exc)

        try:
            summaries_deleted = await self._storage_client.delete_summaries(user_id)
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Failed to delete summary objects: %s", exc)

        report = DataDeletionReport(
            userId=user_id,
            messagesRedacted=messages_redacted,
            sessionsImpacted=len(sessions_impacted),
            dailySummariesDeleted=daily_deleted,
            weeklySummariesDeleted=weekly_deleted,
            memoriesDeleted=memories_deleted,
            analyticsAnonymised=analytics_anonymised,
            refreshTokensRevoked=refresh_tokens_revoked,
            transcriptsDeleted=transcripts_deleted,
            summaryObjectsDeleted=summaries_deleted,
            piiFieldsCleared=sorted(pii_fields_cleared),
        )
        return report
