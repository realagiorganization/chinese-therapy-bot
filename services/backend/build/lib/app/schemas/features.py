from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FeatureFlag(BaseModel):
    """Feature flag representation exposed via API."""

    key: str
    enabled: bool
    description: str | None = None
    rollout_percentage: int = 100
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_json")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class FeatureFlagUpsert(BaseModel):
    """Payload used to create or update a feature flag."""

    enabled: bool
    description: str | None = None
    rollout_percentage: int = Field(default=100, ge=0, le=100)
    metadata: dict[str, Any] | None = None


class FeatureFlagEvaluationRequest(BaseModel):
    """Request payload for evaluating whether a flag is active."""

    subject_id: str | None = Field(
        default=None,
        description="Optional stable identifier used for percentage rollouts.",
    )


class FeatureFlagEvaluationResponse(BaseModel):
    """Response returned when evaluating a feature flag."""

    key: str
    enabled: bool
    reason: str | None = None
