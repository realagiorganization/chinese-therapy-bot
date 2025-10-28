from secrets import token_urlsafe

from app.schemas.auth import (
    AuthProvider,
    LoginChallengeResponse,
    SMSLoginRequest,
    TokenExchangeRequest,
    TokenResponse,
)


class AuthService:
    """Stubbed authentication workflows for SMS and Google providers."""

    async def initiate_sms_login(self, payload: SMSLoginRequest) -> LoginChallengeResponse:
        # In production we would dispatch an OTP through SMS provider and persist the challenge.
        return LoginChallengeResponse(
            channel=AuthProvider.SMS,
            expires_in=300,
            detail=f"OTP dispatched to {payload.phone_number} (stub).",
        )

    async def exchange_token(self, payload: TokenExchangeRequest) -> TokenResponse:
        # Real implementation would verify OTP or OAuth code and mint JWT/refresh tokens.
        access = token_urlsafe(32)
        refresh = token_urlsafe(48)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=3600,
            token_type="bearer",
        )
