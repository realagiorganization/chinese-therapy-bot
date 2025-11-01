from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterable

import aioboto3

from app.core.config import AppSettings
from app.schemas.therapists import (
    TherapistImportRecord,
    TherapistLocalePayload,
)


logger = logging.getLogger(__name__)


class TherapistDataStorage:
    """Fetch therapist profile payloads from S3-compatible storage."""

    _LOCALE_PATTERN = re.compile(r"profile[_-](?P<locale>[a-z]{2}(?:-[A-Z]{2})?)\.json$")

    def __init__(self, settings: AppSettings):
        self._settings = settings

    async def fetch_records(
        self,
        *,
        prefix: str | None = None,
        locales: list[str] | None = None,
    ) -> list[TherapistImportRecord]:
        bucket = self._settings.s3_therapists_bucket
        if not bucket:
            raise RuntimeError("S3_BUCKET_THERAPISTS is not configured.")

        key_prefix = prefix or self._settings.therapist_data_s3_prefix or "therapists/"
        client_kwargs: dict[str, Any] = {}

        if self._settings.aws_region:
            client_kwargs["region_name"] = self._settings.aws_region
        if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = self._settings.aws_access_key_id.get_secret_value()
            client_kwargs["aws_secret_access_key"] = self._settings.aws_secret_access_key.get_secret_value()

        raw_items: list[dict[str, Any]] = []

        async with aioboto3.client("s3", **client_kwargs) as client:
            continuation_token: str | None = None
            while True:
                params: dict[str, Any] = {"Bucket": bucket, "Prefix": key_prefix}
                if continuation_token:
                    params["ContinuationToken"] = continuation_token

                response = await client.list_objects_v2(**params)
                objects = response.get("Contents", [])
                for obj in objects:
                    key = obj.get("Key")
                    if not key or not key.endswith(".json"):
                        continue

                    locale = self._infer_locale_from_key(key)
                    if locales and locale and locale not in locales:
                        continue

                    try:
                        payload = await client.get_object(Bucket=bucket, Key=key)
                        body = await payload["Body"].read()
                        data = json.loads(body.decode("utf-8"))
                    except Exception as exc:  # pragma: no cover - network/error path
                        logger.warning("Failed to read therapist profile %s: %s", key, exc)
                        continue

                    if locale and "locale" not in data:
                        data["locale"] = locale
                    data.setdefault("s3_key", key)
                    raw_items.append(data)

                if not response.get("IsTruncated"):
                    break
                continuation_token = response.get("NextContinuationToken")

        if not raw_items:
            logger.info(
                "No therapist profiles discovered in s3://%s/%s",
                bucket,
                key_prefix,
            )
            return []

        return self._normalize_items(raw_items, locales=locales)

    def _normalize_items(
        self,
        items: Iterable[dict[str, Any]],
        *,
        locales: list[str] | None = None,
    ) -> list[TherapistImportRecord]:
        grouped: dict[str, dict[str, Any]] = {}

        for item in items:
            locale = (item.get("locale") or item.get("language") or "").strip() or "zh-CN"
            if locales and locale not in locales:
                continue

            therapist_id = item.get("therapist_id") or item.get("id")
            slug = item.get("slug") or self._slugify(item.get("name") or therapist_id or "")
            if not slug:
                logger.debug("Skipping therapist entry missing slug and name: %s", item)
                continue

            key = (therapist_id or slug).lower()
            record = grouped.setdefault(
                key,
                {
                    "therapist_id": therapist_id,
                    "slug": slug,
                    "name": item.get("name") or "",
                    "title": item.get("title"),
                    "biography": item.get("biography"),
                    "specialties": set(),
                    "languages": set(),
                    "availability": set(),
                    "price_per_session": item.get("price_per_session"),
                    "currency": item.get("currency") or "CNY",
                    "is_recommended": bool(item.get("is_recommended")),
                    "localizations": {},
                },
            )

            record["therapist_id"] = record.get("therapist_id") or therapist_id
            if not record.get("name") and item.get("name"):
                record["name"] = item["name"]
            if not record.get("title") and item.get("title"):
                record["title"] = item.get("title")
            if not record.get("biography") and item.get("biography"):
                record["biography"] = item.get("biography")

            specialties = self._ensure_list(item.get("specialties"))
            languages = self._ensure_list(item.get("languages"))
            availability = [str(slot) for slot in self._ensure_list(item.get("availability"))]

            record["specialties"].update(specialties)
            record["languages"].update(languages)
            record["availability"].update(availability)

            price = self._coerce_price(item.get("price_per_session"))
            if price is not None:
                record["price_per_session"] = price
            if item.get("currency"):
                record["currency"] = item["currency"]
            if item.get("is_recommended"):
                record["is_recommended"] = True

            record_localizations: dict[str, TherapistLocalePayload] = record["localizations"]
            biography = item.get("biography") or ""
            title = item.get("title") or record.get("title") or ""
            record_localizations[locale] = TherapistLocalePayload(
                locale=locale,
                title=title,
                biography=biography,
            )

        normalized: list[TherapistImportRecord] = []
        for payload in grouped.values():
            normalized.append(
                TherapistImportRecord(
                    therapist_id=payload.get("therapist_id"),
                    slug=payload["slug"],
                    name=payload.get("name") or payload["slug"],
                    title=payload.get("title"),
                    biography=payload.get("biography"),
                    specialties=sorted(payload["specialties"]),
                    languages=sorted(payload["languages"]),
                    availability=sorted(payload["availability"]),
                    price_per_session=payload.get("price_per_session"),
                    currency=payload.get("currency") or "CNY",
                    is_recommended=bool(payload.get("is_recommended")),
                    localizations=list(payload["localizations"].values()),
                )
            )

        return normalized

    def _infer_locale_from_key(self, key: str) -> str | None:
        match = self._LOCALE_PATTERN.search(key)
        if match:
            return match.group("locale")
        return None

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
        return slug

    def _ensure_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        try:
            return [str(item) for item in value if item not in (None, "")]
        except TypeError:
            return [str(value)]

    def _coerce_price(self, value: Any) -> float | None:
        if value in (None, "", "null"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            logger.debug("Unable to parse price value %s", value)
            return None
