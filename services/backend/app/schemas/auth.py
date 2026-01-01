from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, constr


class SessionRequest(BaseModel):
    """Metadata attached to an OAuth2-proxy authenticated request."""

    session_id: Optional[str] = Field(
        default=None,
        description="Opaque session identifier propagated from the client.",
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Client user agent captured for audit trails.",
    )
    ip_address: Optional[str] = Field(
        default=None,
        description="Client IP address (overrides autodetected peer address).",
    )


class DemoLoginRequest(BaseModel):
    """Request payload for exchanging an approved demo code for API tokens."""

    code: constr(min_length=1, strip_whitespace=True) = Field(
        ...,
        description="Demo code defined in the administrator-maintained allowlist.",
    )
    session_id: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)


class GoogleLoginRequest(BaseModel):
    """Request payload for exchanging a Google authorization code for tokens."""

    code: constr(min_length=1, strip_whitespace=True) = Field(
        ...,
        description="Authorization code returned by Google OAuth.",
    )
    redirect_uri: Optional[str] = Field(
        default=None,
        description="Redirect URI used when requesting the authorization code.",
    )
    session_id: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)


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


class RegistrationRequest(BaseModel):
    email: constr(
        min_length=3,
        max_length=254,
        strip_whitespace=True,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    )
    display_name: constr(min_length=1, max_length=120) = Field(
        ...,
        description="Display name captured during registration.",
    )
    locale: Optional[str] = Field(
        default=None, description="Preferred locale for the new account."
    )
    accept_terms: bool = Field(
        default=False, description="User accepted the terms of service."
    )
    session_id: Optional[str] = Field(
        default=None, description="Optional client session identifier."
    )
    user_agent: Optional[str] = Field(
        default=None, description="Client user agent string used for telemetry."
    )
    ip_address: Optional[str] = Field(
        default=None, description="Caller IP address recorded for audit purposes."
    )


class RegistrationResponse(BaseModel):
    status: str = Field(
        ...,
        description="Registration status: registered, pending, or existing.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="User identifier created during registration.",
    )
