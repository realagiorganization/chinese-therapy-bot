from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.config import AppSettings


@dataclass(slots=True)
class GoogleProfile:
    """Normalized Google user profile fields."""

    subject: str
    email: str
    email_verified: bool = True
    name: str | None = None


class GoogleOAuthClient:
    """Stub Google OAuth client used for exchanging authorization codes."""

    def __init__(self, settings: AppSettings):
        self._settings = settings

    async def exchange_code(self, code: str, redirect_uri: str | None = None) -> GoogleProfile:
        """Simulate exchanging an authorization code for an ID token."""
        if not code:
            raise ValueError("Authorization code is missing.")

        # In production we would call Google OAuth endpoints. In development we derive deterministic
        # values to unblock flows without external calls.
        digest = hashlib.sha256(code.encode("utf-8")).hexdigest()
        pseudo_subject = f"google-{digest[:16]}"
        email = f"{digest[:10]}@gmail.com"
        name = f"Google User {digest[:6]}"

        return GoogleProfile(
            subject=pseudo_subject,
            email=email,
            email_verified=True,
            name=name,
        )

