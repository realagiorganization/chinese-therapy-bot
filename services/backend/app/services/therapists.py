from __future__ import annotations

import logging
from typing import Iterable, Sequence
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.therapists import TherapistDataStorage
from app.models import Therapist as TherapistModel
from app.models import TherapistLocalization
from app.schemas.therapists import (
    TherapistDetailResponse,
    TherapistFilter,
    TherapistImportRecord,
    TherapistImportSummary,
    TherapistListResponse,
    TherapistLocalePayload,
    TherapistSummary,
)


logger = logging.getLogger(__name__)


class TherapistService:
    """Therapist directory interactions backed by persistence with S3 import support."""

    def __init__(
        self,
        session: AsyncSession,
        storage: TherapistDataStorage | None = None,
    ):
        self._session = session
        self._storage = storage

    _SEED_THERAPISTS = [
        TherapistDetailResponse(
            therapist_id="00000000-0000-0000-0000-000000000101",
            name="刘心语",
            title="注册心理咨询师",
            specialties=["认知行为疗法", "焦虑管理"],
            languages=["zh-CN"],
            price_per_session=680.0,
            biography="拥有 8 年临床经验，擅长职场压力与情绪调节。",
            availability=["2025-01-10T02:00:00Z", "2025-01-12T10:00:00Z"],
            is_recommended=True,
        ),
        TherapistDetailResponse(
            therapist_id="00000000-0000-0000-0000-000000000102",
            name="王晨",
            title="国家二级心理咨询师",
            specialties=["家庭治疗", "青少年成长"],
            languages=["zh-CN", "en-US"],
            price_per_session=520.0,
            biography="关注家庭关系修复，结合正念减压技巧。",
            availability=["2025-01-11T08:00:00Z"],
        ),
    ]

    async def list_therapists(self, filters: TherapistFilter) -> TherapistListResponse:
        therapists = await self._load_therapists(locale=filters.locale)
        filtered = [
            therapist
            for therapist in therapists
            if self._matches_filters(therapist, filters)
        ]
        return TherapistListResponse(items=filtered)

    async def get_therapist(
        self,
        therapist_id: str,
        *,
        locale: str = "zh-CN",
    ) -> TherapistDetailResponse:
        therapist = await self._fetch_single(therapist_id, locale=locale)
        if therapist:
            return therapist

        for seed in self._SEED_THERAPISTS:
            if seed.therapist_id == therapist_id:
                return seed
        raise ValueError(f"Therapist {therapist_id} not found")

    async def sync_from_storage(
        self,
        *,
        prefix: str | None = None,
        locales: list[str] | None = None,
        dry_run: bool = False,
    ) -> TherapistImportSummary:
        if not self._storage:
            raise RuntimeError("Therapist storage integration is not configured.")

        records = await self._storage.fetch_records(prefix=prefix, locales=locales)
        summary = TherapistImportSummary(total=len(records), dry_run=dry_run)
        if not records:
            return summary

        for record in records:
            try:
                action = await self._apply_record(record, dry_run=dry_run)
            except Exception as exc:  # pragma: no cover - defensive path
                logger.exception("Failed to import therapist %s", record.slug)
                summary.errors.append(f"{record.slug}: {exc}")
                continue

            if action == "created":
                summary.created += 1
            elif action == "updated":
                summary.updated += 1
            elif action == "unchanged":
                summary.unchanged += 1

        return summary

    async def _fetch_single(
        self,
        therapist_id: str,
        *,
        locale: str,
    ) -> TherapistDetailResponse | None:
        stmt = select(TherapistModel).options(selectinload(TherapistModel.localizations))
        identifier_uuid = self._parse_uuid(therapist_id)
        if identifier_uuid:
            stmt = stmt.where(TherapistModel.id == identifier_uuid)
        else:
            stmt = stmt.where(TherapistModel.slug == therapist_id)

        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None

        return self._serialize_detail(record, locale)

    async def _load_therapists(
        self,
        *,
        locale: str,
        detail: bool = False,
    ) -> Sequence[TherapistSummary | TherapistDetailResponse]:
        stmt = select(TherapistModel).options(selectinload(TherapistModel.localizations))
        result = await self._session.execute(stmt)
        records = result.scalars().all()

        if not records:
            return (
                self._SEED_THERAPISTS if detail else self._seed_as_summaries()
            )

        if detail:
            return [self._serialize_detail(record, locale) for record in records]

        return [self._serialize_summary(record, locale) for record in records]

    def _serialize_summary(
        self,
        record: TherapistModel,
        locale: str,
    ) -> TherapistSummary:
        localization = self._select_localization(record, locale)
        title = localization.title if localization and localization.title else record.title
        return TherapistSummary(
            therapist_id=str(record.id),
            name=record.name,
            title=title or record.title,
            specialties=record.specialties or [],
            languages=record.languages or [],
            price_per_session=record.price_per_session or 0.0,
            currency=record.currency,
            is_recommended=record.is_recommended,
        )

    def _serialize_detail(
        self,
        record: TherapistModel,
        locale: str,
    ) -> TherapistDetailResponse:
        localization = self._select_localization(record, locale)
        title = localization.title if localization and localization.title else record.title
        biography = (
            localization.biography
            if localization and localization.biography
            else record.biography or ""
        )
        return TherapistDetailResponse(
            therapist_id=str(record.id),
            name=record.name,
            title=title or record.title,
            specialties=record.specialties or [],
            languages=record.languages or [],
            price_per_session=record.price_per_session or 0.0,
            biography=biography,
            availability=record.availability or [],
            is_recommended=record.is_recommended,
        )

    def _seed_as_summaries(self) -> list[TherapistSummary]:
        return [
            TherapistSummary(
                therapist_id=therapist.therapist_id,
                name=therapist.name,
                title=therapist.title,
                specialties=therapist.specialties,
                languages=therapist.languages,
                price_per_session=therapist.price_per_session,
                currency=therapist.currency,
                is_recommended=therapist.is_recommended,
            )
            for therapist in self._SEED_THERAPISTS
        ]

    def _matches_filters(
        self,
        therapist: TherapistSummary | TherapistDetailResponse,
        filters: TherapistFilter,
    ) -> bool:
        if filters.specialty:
            specialty = filters.specialty.lower()
            if not any(s.lower() == specialty for s in therapist.specialties):
                return False
        if filters.language:
            language = filters.language.lower()
            if not any(lang.lower() == language for lang in therapist.languages):
                return False
        if (
            filters.price_max is not None
            and therapist.price_per_session is not None
            and therapist.price_per_session > filters.price_max
        ):
            return False
        if filters.is_recommended is not None and therapist.is_recommended != filters.is_recommended:
            return False
        return True

    async def _apply_record(
        self,
        record: TherapistImportRecord,
        *,
        dry_run: bool,
    ) -> str:
        existing = await self._find_existing(record)
        if not existing:
            if dry_run:
                return "created"
            therapist = self._build_new_therapist(record)
            self._session.add(therapist)
            await self._session.flush()
            return "created"

        changed = self._update_therapist(existing, record, dry_run=dry_run)
        if dry_run:
            return "updated" if changed else "unchanged"

        if changed:
            await self._session.flush()
            return "updated"
        return "unchanged"

    async def _find_existing(self, record: TherapistImportRecord) -> TherapistModel | None:
        stmt = select(TherapistModel).options(selectinload(TherapistModel.localizations))
        identifier_uuid = self._parse_uuid(record.therapist_id)
        if identifier_uuid:
            stmt = stmt.where(TherapistModel.id == identifier_uuid)
        else:
            stmt = stmt.where(TherapistModel.slug == record.slug)

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_new_therapist(self, record: TherapistImportRecord) -> TherapistModel:
        therapist_id = self._parse_uuid(record.therapist_id) or uuid4()
        therapist = TherapistModel(
            id=therapist_id,
            slug=record.slug,
            name=record.name,
            title=record.title or record.name,
            specialties=record.specialties or [],
            languages=record.languages or [],
            price_per_session=record.price_per_session,
            currency=record.currency,
            biography=record.biography or "",
            is_recommended=record.is_recommended,
            availability=record.availability or [],
        )
        therapist.localizations = self._build_localizations(
            therapist, record.localizations, fallback_title=record.title, fallback_bio=record.biography
        )
        return therapist

    def _update_therapist(
        self,
        therapist: TherapistModel,
        record: TherapistImportRecord,
        *,
        dry_run: bool,
    ) -> bool:
        changed = False
        changed |= self._maybe_assign(therapist, "slug", record.slug)
        changed |= self._maybe_assign(therapist, "name", record.name)
        if record.title:
            changed |= self._maybe_assign(therapist, "title", record.title)

        changed |= self._maybe_assign(therapist, "price_per_session", record.price_per_session)
        changed |= self._maybe_assign(therapist, "currency", record.currency)
        changed |= self._maybe_assign(therapist, "is_recommended", record.is_recommended)

        if record.biography is not None:
            changed |= self._maybe_assign(therapist, "biography", record.biography or "")

        changed |= self._update_list_field(therapist, "specialties", record.specialties)
        changed |= self._update_list_field(therapist, "languages", record.languages)
        changed |= self._update_list_field(therapist, "availability", record.availability)

        locales_changed = self._update_localizations(
            therapist,
            record.localizations,
            fallback_title=record.title or therapist.title,
            fallback_bio=record.biography or therapist.biography,
            dry_run=dry_run,
        )
        changed |= locales_changed

        return changed

    def _maybe_assign(self, obj: TherapistModel, attr: str, value: object) -> bool:
        current = getattr(obj, attr)
        if current != value:
            setattr(obj, attr, value)
            return True
        return False

    def _update_list_field(
        self,
        therapist: TherapistModel,
        attr: str,
        incoming: Iterable[str],
    ) -> bool:
        normalized = sorted(set(incoming or []))
        current = getattr(therapist, attr) or []
        if sorted(current) != normalized:
            setattr(therapist, attr, normalized)
            return True
        return False

    def _update_localizations(
        self,
        therapist: TherapistModel,
        localizations: list[TherapistLocalePayload],
        *,
        fallback_title: str | None,
        fallback_bio: str | None,
        dry_run: bool,
    ) -> bool:
        incoming = self._to_locale_map(localizations, fallback_title, fallback_bio)
        existing = {
            loc.locale.lower(): (loc.title or "", loc.biography or "")
            for loc in therapist.localizations
        }

        changed = incoming != existing
        if dry_run or not changed:
            return changed

        therapist.localizations.clear()
        for locale, (title, biography) in incoming.items():
            therapist.localizations.append(
                TherapistLocalization(
                    locale=locale,
                    title=title,
                    biography=biography,
                )
            )
        return changed

    def _build_localizations(
        self,
        therapist: TherapistModel,
        localizations: list[TherapistLocalePayload],
        *,
        fallback_title: str | None,
        fallback_bio: str | None,
    ) -> list[TherapistLocalization]:
        locale_map = self._to_locale_map(localizations, fallback_title, fallback_bio)
        return [
            TherapistLocalization(locale=locale, title=title, biography=biography)
            for locale, (title, biography) in locale_map.items()
        ]

    def _to_locale_map(
        self,
        localizations: list[TherapistLocalePayload],
        fallback_title: str | None,
        fallback_bio: str | None,
    ) -> dict[str, tuple[str, str]]:
        if not localizations:
            locale = "zh-CN"
            title = fallback_title or ""
            biography = fallback_bio or ""
            return {locale.lower(): (title, biography)}

        mapping: dict[str, tuple[str, str]] = {}
        for item in localizations:
            locale = (item.locale or "zh-CN").lower()
            title = item.title or fallback_title or ""
            biography = item.biography or fallback_bio or ""
            mapping[locale] = (title, biography)
        return mapping

    def _select_localization(
        self,
        therapist: TherapistModel,
        locale: str,
    ) -> TherapistLocalization | None:
        normalized = locale.lower()
        for loc in therapist.localizations:
            if loc.locale.lower() == normalized:
                return loc
        return None

    def _parse_uuid(self, value: str | None) -> UUID | None:
        if not value:
            return None
        try:
            return UUID(value)
        except ValueError:
            return None
