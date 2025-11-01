from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppSettings
from app.models import FeatureFlag as FeatureFlagModel
from app.schemas.features import (
    FeatureFlag,
    FeatureFlagEvaluationResponse,
    FeatureFlagUpsert,
)


class FeatureFlagService:
    """Manage runtime feature flags backed by the database with config defaults."""

    def __init__(self, session: AsyncSession, settings: AppSettings):
        self._session = session
        self._settings = settings
        self._defaults = self._parse_defaults(settings.feature_flags)

    async def list_flags(self) -> list[FeatureFlag]:
        """Return all known feature flags, merging DB values with config defaults."""
        result = await self._session.execute(select(FeatureFlagModel))
        records = {record.key: record for record in result.scalars().all()}

        flags: list[FeatureFlag] = [
            FeatureFlag.model_validate(record) for record in records.values()
        ]

        for key, enabled in self._defaults.items():
            if key in records:
                continue
            flags.append(
                FeatureFlag(
                    key=key,
                    enabled=enabled,
                    description="Default flag from FEATURE_FLAGS config.",
                )
            )

        flags.sort(key=lambda flag: flag.key)
        return flags

    async def get_flag(self, key: str) -> FeatureFlag:
        """Return a single feature flag, falling back to config defaults."""
        record = await self._session.get(FeatureFlagModel, key)
        if record:
            return FeatureFlag.model_validate(record)

        if key in self._defaults:
            return FeatureFlag(
                key=key,
                enabled=self._defaults[key],
                description="Default flag from FEATURE_FLAGS config.",
            )

        raise ValueError(f"Feature flag '{key}' not found.")

    async def upsert_flag(self, key: str, payload: FeatureFlagUpsert) -> FeatureFlag:
        """Create or update a feature flag."""
        record = await self._session.get(FeatureFlagModel, key)
        if record is None:
            record = FeatureFlagModel(
                key=key,
                enabled=payload.enabled,
                description=payload.description,
                rollout_percentage=payload.rollout_percentage,
                metadata_json=self._normalize_metadata(payload.metadata),
            )
            self._session.add(record)
        else:
            record.enabled = payload.enabled
            record.rollout_percentage = payload.rollout_percentage
            record.description = payload.description
            record.metadata_json = self._normalize_metadata(payload.metadata)

        await self._session.flush()
        return FeatureFlag.model_validate(record)

    async def evaluate_flag(
        self,
        key: str,
        *,
        subject_id: str | None = None,
    ) -> FeatureFlagEvaluationResponse:
        """Determine whether a flag is enabled for an optional subject identifier."""
        flag = await self.get_flag(key)
        if not flag.enabled:
            return FeatureFlagEvaluationResponse(
                key=key,
                enabled=False,
                reason="Flag disabled.",
            )

        rollout = flag.rollout_percentage or 0
        if rollout >= 100 or not subject_id:
            return FeatureFlagEvaluationResponse(
                key=key,
                enabled=True,
                reason="Enabled globally." if rollout >= 100 else "No subject provided.",
            )

        bucket = self._deterministic_bucket(subject_id)
        enabled = bucket < rollout
        reason = f"Subject bucket {bucket} under rollout {rollout}%." if enabled else (
            f"Subject bucket {bucket} exceeds rollout {rollout}%."
        )
        return FeatureFlagEvaluationResponse(
            key=key,
            enabled=enabled,
            reason=reason,
        )

    def _parse_defaults(self, raw: str | None) -> dict[str, bool]:
        if not raw:
            return {}

        defaults: dict[str, bool] = {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = self._parse_delimited_flags(raw)

        if isinstance(parsed, dict):
            for key, value in parsed.items():
                defaults[str(key).strip()] = self._to_bool(value)
        return defaults

    def _parse_delimited_flags(self, raw: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for token in raw.split(","):
            item = token.strip()
            if not item:
                continue
            delimiter = "=" if "=" in item else (":" if ":" in item else None)
            if delimiter:
                key, raw_value = item.split(delimiter, 1)
                result[key.strip()] = self._to_bool(raw_value)
            else:
                result[item] = True
        return result

    def _to_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        str_value = str(value).strip().lower()
        return str_value in {"1", "true", "yes", "on", "enabled"}

    def _normalize_metadata(
        self,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return metadata if metadata else None

    def _deterministic_bucket(self, subject_id: str) -> int:
        digest = hashlib.sha256(subject_id.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 100
