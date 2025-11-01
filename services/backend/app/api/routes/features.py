from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_feature_flag_service
from app.schemas.features import (
    FeatureFlag,
    FeatureFlagEvaluationRequest,
    FeatureFlagEvaluationResponse,
    FeatureFlagUpsert,
)
from app.services.feature_flags import FeatureFlagService


router = APIRouter()


@router.get("/", response_model=list[FeatureFlag], summary="List all feature flags.")
async def list_feature_flags(
    service: FeatureFlagService = Depends(get_feature_flag_service),
) -> list[FeatureFlag]:
    return await service.list_flags()


@router.get(
    "/{key}",
    response_model=FeatureFlag,
    summary="Fetch a single feature flag by key.",
)
async def get_feature_flag(
    key: str,
    service: FeatureFlagService = Depends(get_feature_flag_service),
) -> FeatureFlag:
    try:
        return await service.get_flag(key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.put(
    "/{key}",
    response_model=FeatureFlag,
    summary="Create or update a feature flag.",
)
async def upsert_feature_flag(
    key: str,
    payload: FeatureFlagUpsert,
    service: FeatureFlagService = Depends(get_feature_flag_service),
) -> FeatureFlag:
    return await service.upsert_flag(key, payload)


@router.post(
    "/{key}/evaluate",
    response_model=FeatureFlagEvaluationResponse,
    summary="Evaluate whether a flag is enabled for a subject.",
)
async def evaluate_feature_flag(
    key: str,
    payload: FeatureFlagEvaluationRequest,
    service: FeatureFlagService = Depends(get_feature_flag_service),
) -> FeatureFlagEvaluationResponse:
    try:
        return await service.evaluate_flag(key, subject_id=payload.subject_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
