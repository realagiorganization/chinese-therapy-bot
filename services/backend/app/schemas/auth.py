from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AuthProvider(str, Enum):
    SMS = "sms"
    GOOGLE = "google"


class SMSLoginRequest(BaseModel):
    phone_number: str = Field(..., json_schema_extra={"example": "+8613800000000"})
    country_code: str = Field(
        default="+86",
        json_schema_extra={"example": "+86"},
    )
    locale: Optional[str] = Field(
        default=None,
        json_schema_extra={"example": "zh-CN"},
    )


class LoginChallengeResponse(BaseModel):
    channel: AuthProvider
    challenge_id: str = Field(..., description="Identifier required for completing the login flow.")
    expires_in: int = Field(..., description="Seconds until the current challenge expires.")
    detail: str = Field(..., description="Human-readable status for product analytics.")


class TokenExchangeRequest(BaseModel):
    provider: AuthProvider
    code: str = Field(..., description="Verification code or OAuth authorization code.")
    challenge_id: Optional[str] = Field(
        default=None,
        description="Challenge identifier (required for SMS OTP verification).",
    )
    redirect_uri: Optional[str] = None
    session_id: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Previously issued refresh token.")
    session_id: Optional[str] = Field(
        default=None, description="Optional session identifier for auditing."
    )
    user_agent: Optional[str] = Field(
        default=None, description="Client user agent string used for telemetry."
    )
    ip_address: Optional[str] = Field(
        default=None, description="Caller IP address recorded for fraud detection."
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer")
    expires_in: int = Field(default=3600)
