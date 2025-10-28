from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service
from app.schemas.auth import (
    LoginChallengeResponse,
    SMSLoginRequest,
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
    return await service.initiate_sms_login(payload)


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Exchange verification code for access tokens",
)
async def exchange_token(
    payload: TokenExchangeRequest, service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    return await service.exchange_token(payload)
