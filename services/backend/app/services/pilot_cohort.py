from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PilotCohortParticipant
from app.schemas.pilot_cohort import (
    FollowUpUrgency,
    PilotFollowUp,
    PilotFollowUpList,
    PilotParticipantCreate,
    PilotParticipantFilters,
    PilotParticipantListResponse,
    PilotParticipantResponse,
    PilotParticipantSummary,
    PilotParticipantSummaryBucket,
    PilotParticipantStatus,
    PilotParticipantUpdate,
)


logger = logging.getLogger(__name__)


class PilotCohortService:
    """Manage pilot cohort participant roster and engagement lifecycle."""

    _FOLLOW_UP_RULES: dict[PilotParticipantStatus, dict[str, Any]] = {
        PilotParticipantStatus.INVITED: {
            "interval": timedelta(days=3),
            "template": "invite_reminder",
            "reason": "Invitation was sent {days_phrase} with no confirmation yet.",
        },
        PilotParticipantStatus.CONTACTED: {
            "interval": timedelta(days=4),
            "template": "contact_followup",
            "reason": "Last outreach occurred {days_phrase} without a reply.",
        },
        PilotParticipantStatus.ONBOARDING: {
            "interval": timedelta(days=2),
            "template": "onboarding_nudge",
            "reason": "Participant started onboarding but stalled {days_phrase}.",
        },
        PilotParticipantStatus.ACTIVE: {
            "interval": timedelta(days=14),
            "template": "active_checkin",
            "reason": "No check-in recorded since {days_phrase}; prompt a wellness touchpoint.",
        },
    }

    _MESSAGE_TEMPLATES: dict[str, dict[str, dict[str, str]]] = {
        "invite_reminder": {
            "zh-CN": {
                "subject": "MindWell 体验邀约提醒",
                "body": (
                    "{greeting}，这里是 MindWell 关怀团队。我们在{days_phrase}向你发送了体验邀约，"
                    "尚未看到注册完成。如果你还想体验 MindWell，可以直接点击邀请邮件中的链接完成账号设置；"
                    "若需要协助，回复此消息即可，我们会安排专人跟进。"
                ),
            },
            "en-US": {
                "subject": "MindWell pilot invitation check-in",
                "body": (
                    "{greeting}, this is the MindWell care team. We sent your pilot invitation {days_phrase} "
                    "and haven't seen the sign-up completed yet. If you're still interested, simply open the link "
                    "in the invitation email to finish onboarding. Need a hand? Reply here and we'll set up support."
                ),
            },
        },
        "contact_followup": {
            "zh-CN": {
                "subject": "MindWell 体验跟进",
                "body": (
                    "{greeting}，感谢你上次与我们沟通。为了帮助你顺利开始体验，我们整理了入门提示并可以安排一对一指导。"
                    "如果你方便的话，回复此消息，我们会根据你的时间安排下一步。"
                ),
            },
            "en-US": {
                "subject": "MindWell pilot follow-up",
                "body": (
                    "{greeting}, thanks again for chatting with us earlier. We'd love to help you get started and "
                    "can share quick-start tips or schedule a guided walkthrough. Let us know what works best for you—"
                    "just reply to this message."
                ),
            },
        },
        "onboarding_nudge": {
            "zh-CN": {
                "subject": "完成 MindWell 体验设置",
                "body": (
                    "{greeting}，你的 MindWell 账户还差最后一步就可以开启体验。登录后按照提示完成资料，就能收到每日关怀建议。"
                    "如果遇到问题，回复我们即可获取协助。"
                ),
            },
            "en-US": {
                "subject": "Finish setting up your MindWell pilot access",
                "body": (
                    "{greeting}, you're one step away from using MindWell. Sign in to finish the setup checklist and "
                    "you'll start receiving daily support. If anything is unclear, reply here and we'll walk through it together."
                ),
            },
        },
        "active_checkin": {
            "zh-CN": {
                "subject": "MindWell 关怀问候",
                "body": (
                    "{greeting}，我们想了解你最近的体验情况。如果有新的关注点或需要额外支持，回复这条消息，我们会尽快为你安排。"
                ),
            },
            "en-US": {
                "subject": "MindWell wellness check-in",
                "body": (
                    "{greeting}, checking in to see how MindWell has been working for you. If there's anything new on your mind "
                    "or you need extra support, reply and we'll connect you with the right resources."
                ),
            },
        },
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_participant(
        self,
        payload: PilotParticipantCreate,
    ) -> PilotCohortParticipant:
        record = PilotCohortParticipant(
            cohort=self._normalize_text(payload.cohort),
            participant_alias=self._normalize_optional(payload.participant_alias),
            contact_email=self._normalize_optional(payload.contact_email),
            contact_phone=self._normalize_optional(payload.contact_phone),
            channel=self._normalize_text(payload.channel or "web"),
            locale=self._normalize_text(payload.locale or "zh-CN"),
            status=payload.status.value,
            source=self._normalize_optional(payload.source),
            tags=self._normalize_tags(payload.tags),
            invite_sent_at=payload.invite_sent_at,
            onboarded_at=payload.onboarded_at,
            last_contacted_at=payload.last_contacted_at,
            consent_received=payload.consent_received,
            notes=self._normalize_optional(payload.notes),
            metadata_json=payload.metadata or {},
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_participants(
        self,
        filters: PilotParticipantFilters | None = None,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> PilotParticipantListResponse:
        filters = filters or PilotParticipantFilters()
        base_stmt = select(PilotCohortParticipant)
        filtered_stmt = self._apply_filters(base_stmt, filters)
        total_stmt = self._apply_filters(
            select(func.count()),
            filters,
        )

        result = await self._session.execute(
            filtered_stmt.order_by(PilotCohortParticipant.created_at.asc())
            .offset(max(offset, 0))
            .limit(max(limit, 1))
        )
        participants = result.scalars().all()

        total_result = await self._session.execute(total_stmt)
        total = int(total_result.scalar_one())

        items = [self._to_response(participant) for participant in participants]
        return PilotParticipantListResponse(
            total=total,
            items=items,
        )

    async def summarize_participants(
        self,
        filters: PilotParticipantFilters | None = None,
    ) -> PilotParticipantSummary:
        """Return aggregate metrics for the filtered participant set."""
        filters = filters or PilotParticipantFilters()
        stmt = self._apply_filters(select(PilotCohortParticipant), filters)
        result = await self._session.execute(
            stmt.order_by(PilotCohortParticipant.created_at.asc())
        )
        participants = list(result.scalars().all())

        total = len(participants)
        if total == 0:
            return PilotParticipantSummary(
                total=0,
                with_consent=0,
                without_consent=0,
                by_status=[],
                by_channel=[],
                by_locale=[],
                top_tags=[],
            )

        with_consent = sum(1 for participant in participants if participant.consent_received)
        status_counts = Counter(
            (participant.status or "unspecified").lower() for participant in participants
        )
        channel_counts = Counter(
            (participant.channel or "unspecified").lower() for participant in participants
        )
        locale_counts = Counter(
            (participant.locale or "unspecified").lower() for participant in participants
        )
        tag_counts = Counter(
            tag.lower()
            for participant in participants
            for tag in participant.tags or []
            if tag and tag.strip()
        )

        def _buckets(counter: Counter[str]) -> list[PilotParticipantSummaryBucket]:
            return [
                PilotParticipantSummaryBucket(key=key, total=count)
                for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
            ]

        top_tags = _buckets(tag_counts)[:10]

        return PilotParticipantSummary(
            total=total,
            with_consent=with_consent,
            without_consent=total - with_consent,
            by_status=_buckets(status_counts),
            by_channel=_buckets(channel_counts),
            by_locale=_buckets(locale_counts),
            top_tags=top_tags,
        )

    async def plan_followups(
        self,
        filters: PilotParticipantFilters | None = None,
        *,
        horizon_days: int = 7,
    ) -> PilotFollowUpList:
        """Compute upcoming engagement follow-ups for cohort participants."""
        filters = filters or PilotParticipantFilters()
        stmt = self._apply_filters(select(PilotCohortParticipant), filters)
        result = await self._session.execute(
            stmt.order_by(PilotCohortParticipant.created_at.asc())
        )
        participants = result.scalars().all()

        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=max(horizon_days, 1))

        followups: list[PilotFollowUp] = []
        for participant in participants:
            suggestion = self._build_followup(participant, now, horizon)
            if suggestion is not None:
                followups.append(suggestion)

        followups.sort(key=lambda item: item.due_at)
        return PilotFollowUpList(
            generated_at=now,
            total=len(followups),
            items=followups,
        )

    async def get_participant(self, participant_id: UUID) -> PilotCohortParticipant | None:
        return await self._session.get(PilotCohortParticipant, participant_id)

    async def update_participant(
        self,
        participant_id: UUID,
        payload: PilotParticipantUpdate,
    ) -> PilotCohortParticipant:
        participant = await self.get_participant(participant_id)
        if not participant:
            raise ValueError("Participant not found.")

        if payload.cohort is not None:
            participant.cohort = self._normalize_text(payload.cohort)
        if payload.participant_alias is not None:
            participant.participant_alias = self._normalize_optional(payload.participant_alias)
        if payload.contact_email is not None:
            participant.contact_email = self._normalize_optional(payload.contact_email)
        if payload.contact_phone is not None:
            participant.contact_phone = self._normalize_optional(payload.contact_phone)
        if payload.channel is not None:
            participant.channel = self._normalize_text(payload.channel)
        if payload.locale is not None:
            participant.locale = self._normalize_text(payload.locale)
        if payload.status is not None:
            participant.status = payload.status.value
            if payload.status == PilotParticipantStatus.ACTIVE and not participant.onboarded_at:
                participant.onboarded_at = payload.onboarded_at or datetime.now(timezone.utc)
            if payload.status == PilotParticipantStatus.INVITED and not participant.invite_sent_at:
                participant.invite_sent_at = payload.invite_sent_at or datetime.now(timezone.utc)
        if payload.source is not None:
            participant.source = self._normalize_optional(payload.source)
        if payload.tags is not None:
            participant.tags = self._normalize_tags(payload.tags)
        if payload.invite_sent_at is not None:
            participant.invite_sent_at = payload.invite_sent_at
        if payload.onboarded_at is not None:
            participant.onboarded_at = payload.onboarded_at
        if payload.last_contacted_at is not None:
            participant.last_contacted_at = payload.last_contacted_at
        if payload.consent_received is not None:
            participant.consent_received = payload.consent_received
        if payload.notes is not None:
            participant.notes = self._normalize_optional(payload.notes)
        if payload.metadata is not None:
            participant.metadata_json = payload.metadata

        participant.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return participant

    def _apply_filters(
        self,
        stmt,
        filters: PilotParticipantFilters,
    ):
        if filters.cohort:
            stmt = stmt.where(
                func.lower(PilotCohortParticipant.cohort) == filters.cohort.lower()
            )
        if filters.status:
            stmt = stmt.where(PilotCohortParticipant.status == filters.status.value)
        if filters.channel:
            stmt = stmt.where(
                func.lower(PilotCohortParticipant.channel) == filters.channel.lower()
            )
        if filters.source:
            stmt = stmt.where(
                func.lower(PilotCohortParticipant.source) == filters.source.lower()
            )
        if filters.consent_received is not None:
            stmt = stmt.where(PilotCohortParticipant.consent_received == filters.consent_received)
        if filters.search:
            like_pattern = f"%{filters.search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(PilotCohortParticipant.contact_email).like(like_pattern),
                    func.lower(PilotCohortParticipant.participant_alias).like(like_pattern),
                    func.lower(PilotCohortParticipant.contact_phone).like(like_pattern),
                )
            )
        return stmt

    def _normalize_tags(self, tags: Iterable[str] | None) -> list[str]:
        normalized: list[str] = []
        if not tags:
            return normalized
        seen: set[str] = set()
        for tag in tags:
            value = (tag or "").strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(value)
        return normalized

    def _normalize_text(self, value: str) -> str:
        return value.strip()

    def _normalize_optional(self, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    def _build_followup(
        self,
        participant: PilotCohortParticipant,
        now: datetime,
        horizon: datetime,
    ) -> PilotFollowUp | None:
        status = PilotParticipantStatus(participant.status)
        config = self._FOLLOW_UP_RULES.get(status)
        if not config:
            return None

        reference = self._resolve_reference_timestamp(participant)
        interval: timedelta = config["interval"]
        due_at = reference + interval

        if due_at > horizon:
            return None

        stale_threshold = now - timedelta(days=30)
        if due_at < stale_threshold:
            return None

        urgency = self._resolve_urgency(due_at, now)
        days_since = max(int((now - reference).total_seconds() // 86400), 0)
        reason = config["reason"].format(days_phrase=self._format_days_phrase(days_since))

        subject, message = self._render_followup_message(
            config["template"],
            participant,
            days_since,
            due_at,
        )

        return PilotFollowUp(
            participant_id=participant.id,
            cohort=participant.cohort,
            participant_alias=participant.participant_alias,
            channel=participant.channel,
            locale=self._normalize_locale(participant.locale),
            status=status,
            due_at=due_at,
            urgency=urgency,
            reason=reason,
            subject=subject,
            message=message,
        )

    def _resolve_reference_timestamp(self, participant: PilotCohortParticipant) -> datetime:
        candidates = (
            participant.last_contacted_at,
            participant.onboarded_at,
            participant.invite_sent_at,
            participant.created_at,
        )
        for candidate in candidates:
            aware = self._ensure_aware(candidate)
            if aware is not None:
                return aware
        return datetime.now(timezone.utc)

    def _ensure_aware(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _resolve_urgency(self, due_at: datetime, now: datetime) -> FollowUpUrgency:
        if due_at <= now:
            return FollowUpUrgency.OVERDUE
        if due_at <= now + timedelta(days=1):
            return FollowUpUrgency.DUE
        return FollowUpUrgency.UPCOMING

    def _render_followup_message(
        self,
        template_key: str,
        participant: PilotCohortParticipant,
        days_since: int,
        due_at: datetime,
    ) -> tuple[str, str]:
        locale = self._normalize_locale(participant.locale)
        templates = self._MESSAGE_TEMPLATES.get(template_key, {})
        content = templates.get(locale)

        if content is None and locale.startswith("zh"):
            content = templates.get("zh-CN")
        if content is None:
            content = templates.get("en-US")
        if content is None:
            content = next(
                iter(templates.values()),
                {"subject": "MindWell follow-up", "body": "{greeting}"},
            )

        greeting = self._build_greeting(locale, participant)
        days_phrase_localized = self._format_days_for_locale(locale, days_since)
        due_date_str = due_at.astimezone(timezone.utc).strftime("%Y-%m-%d")

        subject_template = content.get("subject", "MindWell follow-up")
        body_template = content.get("body", "{greeting}")

        subject = subject_template.format(
            days_phrase=days_phrase_localized,
            due_date=due_date_str,
        )
        message = body_template.format(
            greeting=greeting,
            days_phrase=days_phrase_localized,
            due_date=due_date_str,
        )
        return subject, message

    def _normalize_locale(self, value: str | None) -> str:
        if not value:
            return "zh-CN"
        normalized = value.replace("_", "-").strip()
        lowered = normalized.lower()
        if lowered.startswith("zh"):
            return "zh-CN"
        if lowered.startswith("en"):
            return "en-US"
        return "en-US"

    def _build_greeting(self, locale: str, participant: PilotCohortParticipant) -> str:
        name = self._resolve_display_name(participant)
        if locale.startswith("zh"):
            return f"嗨{name}" if name else "你好"
        return f"Hi {name}" if name else "Hi there"

    def _resolve_display_name(self, participant: PilotCohortParticipant) -> str | None:
        if participant.participant_alias:
            return participant.participant_alias
        if participant.contact_email:
            prefix = participant.contact_email.split("@", 1)[0]
            return prefix or participant.contact_email
        if participant.contact_phone:
            return participant.contact_phone
        return None

    def _format_days_for_locale(self, locale: str, days: int) -> str:
        if locale.startswith("zh"):
            if days <= 0:
                return "今天"
            if days == 1:
                return "1 天前"
            return f"{days} 天前"
        if days <= 0:
            return "today"
        if days == 1:
            return "1 day ago"
        return f"{days} days ago"

    def _format_days_phrase(self, days: int) -> str:
        if days <= 0:
            return "today"
        if days == 1:
            return "1 day ago"
        return f"{days} days ago"

    def as_response(self, participant: PilotCohortParticipant) -> PilotParticipantResponse:
        """Public helper to serialize ORM instances for API responses."""
        return self._to_response(participant)

    def _to_response(self, participant: PilotCohortParticipant) -> PilotParticipantResponse:
        return PilotParticipantResponse(
            id=participant.id,
            cohort=participant.cohort,
            participant_alias=participant.participant_alias,
            contact_email=participant.contact_email,
            contact_phone=participant.contact_phone,
            channel=participant.channel,
            locale=participant.locale,
            status=PilotParticipantStatus(participant.status),
            source=participant.source,
            tags=list(participant.tags or []),
            invite_sent_at=participant.invite_sent_at,
            onboarded_at=participant.onboarded_at,
            last_contacted_at=participant.last_contacted_at,
            consent_received=participant.consent_received,
            notes=participant.notes,
            metadata=participant.metadata_json or {},
            created_at=participant.created_at,
            updated_at=participant.updated_at,
        )
