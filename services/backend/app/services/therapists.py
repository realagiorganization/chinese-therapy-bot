from __future__ import annotations

import asyncio
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
from app.services.analytics import ProductAnalyticsService
from app.services.translation import TranslationService


logger = logging.getLogger(__name__)


class TherapistService:
    """Therapist directory interactions backed by persistence with S3 import support."""

    def __init__(
        self,
        session: AsyncSession,
        storage: TherapistDataStorage | None = None,
        analytics_service: ProductAnalyticsService | None = None,
        translation_service: TranslationService | None = None,
    ):
        self._session = session
        self._storage = storage
        self._analytics = analytics_service
        self._translator = translation_service
        self._target_locales = (
            translation_service.default_locales
            if translation_service
            else ("zh-CN", "zh-TW", "en-US", "ru-RU")
        )

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
            await self._record_profile_view(therapist, locale=locale)
            return therapist

        for seed in self._SEED_THERAPISTS:
            if seed.therapist_id == therapist_id:
                localized_seed = await self._localize_seed_detail(seed, locale)
                await self._record_profile_view(localized_seed, locale=locale)
                return localized_seed
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
        if self._translator and records:
            target_locales = locales if locales else list(self._target_locales)
            records = await self._translator.ensure_therapist_localizations(
                records,
                target_locales=target_locales,
            )
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

        return await self._serialize_detail(record, locale)

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
            return await (
                self._seed_details(locale)
                if detail
                else self._seed_summaries(locale)
            )

        if detail:
            return await asyncio.gather(
                *[self._serialize_detail(record, locale) for record in records]
            )

        return await asyncio.gather(
            *[self._serialize_summary(record, locale) for record in records]
        )

    async def _record_profile_view(
        self,
        therapist: TherapistDetailResponse,
        *,
        locale: str,
    ) -> None:
        if not self._analytics:
            return

        try:
            therapist_uuid = self._parse_uuid(therapist.therapist_id)
            await self._analytics.track_therapist_profile_view(
                user_id=None,
                therapist_id=therapist_uuid,
                locale=locale,
            )
        except Exception as exc:  # pragma: no cover - analytics should not block therapist flows
            logger.debug("Failed to record therapist analytics event: %s", exc, exc_info=exc)

    def _build_summary_base(
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

    def _build_detail_base(
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

    async def _serialize_summary(
        self,
        record: TherapistModel,
        locale: str,
    ) -> TherapistSummary:
        summary = self._build_summary_base(record, locale)
        source_locale = self._determine_record_locale(record)
        return await self._localize_summary_payload(
            summary,
            locale,
            source_locale=source_locale,
        )

    async def _serialize_detail(
        self,
        record: TherapistModel,
        locale: str,
    ) -> TherapistDetailResponse:
        detail = self._build_detail_base(record, locale)
        source_locale = self._determine_record_locale(record)
        return await self._localize_detail_payload(
            detail,
            locale,
            source_locale=source_locale,
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

    async def _seed_summaries(self, locale: str) -> list[TherapistSummary]:
        summaries = self._seed_as_summaries()
        if not self._translator or self._translator.are_locales_equivalent(locale, "zh-CN"):
            return summaries
        localized = await asyncio.gather(
            *[
                self._localize_summary_payload(summary, locale, source_locale="zh-CN")
                for summary in summaries
            ]
        )
        return localized

    async def _seed_details(self, locale: str) -> list[TherapistDetailResponse]:
        if not self._translator:
            return [therapist.model_copy() for therapist in self._SEED_THERAPISTS]
        localized = await asyncio.gather(
            *[self._localize_seed_detail(therapist, locale) for therapist in self._SEED_THERAPISTS]
        )
        return localized

    async def _localize_seed_detail(
        self,
        detail: TherapistDetailResponse,
        locale: str,
    ) -> TherapistDetailResponse:
        copy = detail.model_copy()
        if not self._translator or self._translator.are_locales_equivalent(locale, "zh-CN"):
            return copy
        return await self._localize_detail_payload(copy, locale, source_locale="zh-CN")

    async def _localize_summary_payload(
        self,
        summary: TherapistSummary,
        locale: str,
        *,
        source_locale: str,
    ) -> TherapistSummary:
        if not self._translator:
            return summary
        if self._translator.are_locales_equivalent(locale, source_locale):
            return summary

        translated_title = await self._translator.translate_text(
            summary.title,
            target_locale=locale,
            source_locale=source_locale,
        )
        translated_specialties = await self._translator.translate_list(
            summary.specialties,
            target_locale=locale,
            source_locale=source_locale,
        )

        return summary.model_copy(
            update={
                "title": translated_title or summary.title,
                "specialties": translated_specialties or summary.specialties,
            }
        )

    async def _localize_detail_payload(
        self,
        detail: TherapistDetailResponse,
        locale: str,
        *,
        source_locale: str,
    ) -> TherapistDetailResponse:
        if not self._translator:
            return detail
        if self._translator.are_locales_equivalent(locale, source_locale):
            return detail

        translated_title = await self._translator.translate_text(
            detail.title,
            target_locale=locale,
            source_locale=source_locale,
        )
        translated_bio = await self._translator.translate_text(
            detail.biography,
            target_locale=locale,
            source_locale=source_locale,
        )
        translated_specialties = await self._translator.translate_list(
            detail.specialties,
            target_locale=locale,
            source_locale=source_locale,
        )

        return detail.model_copy(
            update={
                "title": translated_title or detail.title,
                "biography": translated_bio or detail.biography,
                "specialties": translated_specialties or detail.specialties,
            }
        )

    def _determine_record_locale(self, record: TherapistModel) -> str:
        if not self._translator:
            return "zh-CN"

        preferred: str | None = None
        for localization in record.localizations or []:
            locale = localization.locale or ""
            if not locale:
                continue
            if locale.lower().startswith("zh"):
                return locale
            preferred = preferred or locale

        for language in record.languages or []:
            if language and language.lower().startswith(("zh", "en", "ru")):
                return language

        probe_fields = [record.title, record.biography, record.name]
        for field in probe_fields:
            if field:
                detected = self._translator.detect_locale(field, fallback="zh-CN")
                if detected:
                    return detected

        return preferred or "zh-CN"

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
            filters.price_min is not None
            and therapist.price_per_session is not None
            and therapist.price_per_session < filters.price_min
        ):
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
