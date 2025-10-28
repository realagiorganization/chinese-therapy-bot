from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AuthProvider(str, Enum):
    SMS = "sms"
    GOOGLE = "google"


class SMSLoginRequest(BaseModel):
    phone_number: str = Field(..., example="+8613800000000")
    country_code: str = Field(default="+86", example="+86")
    locale: Optional[str] = Field(default=None, example="zh-CN")


class LoginChallengeResponse(BaseModel):
    channel: AuthProvider
    expires_in: int = Field(..., description="Seconds until the current challenge expires.")
    detail: str = Field(..., description="Human-readable status for product analytics.")


class TokenExchangeRequest(BaseModel):
    provider: AuthProvider
    code: str = Field(..., description="Verification code or OAuth authorization code.")
    redirect_uri: Optional[str] = None
    session_id: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = Field(default="bearer")
    expires_in: int = Field(default=3600)
