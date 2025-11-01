from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_auth_service
from app.schemas.auth import (
    LoginChallengeResponse,
    SMSLoginRequest,
    TokenRefreshRequest,
    TokenExchangeRequest,
    TokenResponse,
)
from app.services.auth import AuthService

router = APIRouter()


@router.post(
    "/sms",
    response_model=LoginChallengeResponse,
    summary="Initiate SMS login challenge",
)
async def initiate_sms_login(
    payload: SMSLoginRequest, service: AuthService = Depends(get_auth_service)
) -> LoginChallengeResponse:
    try:
        return await service.initiate_sms_login(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Exchange verification code for access tokens",
)
async def exchange_token(
    payload: TokenExchangeRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    try:
        return await service.exchange_token(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/token/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and mint a new access token pair.",
)
async def refresh_token(
    payload: TokenRefreshRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    try:
        return await service.refresh_token(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
