from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.config import AppSettings


@dataclass(slots=True)
class WeChatProfile:
    """Normalized subset of fields returned by the WeChat OAuth profile API."""

    open_id: str
    union_id: str | None
    nickname: str
    avatar_url: str | None = None
    locale: str = "zh-CN"


class WeChatOAuthClient:
    """Stub WeChat OAuth client used during development previews."""

    def __init__(self, settings: AppSettings):
        self._settings = settings

    async def exchange_code(self, code: str, redirect_uri: str | None = None) -> WeChatProfile:
        """Simulate exchanging a WeChat authorization code for a profile payload."""
        if not code:
            raise ValueError("Authorization code is missing.")

        salt = self._settings.wechat_app_id or "mindwell-wechat"
        digest = hashlib.sha1(f"{salt}:{code}".encode("utf-8")).hexdigest()
        open_id = f"wechat-{digest[:24]}"
        union_id = f"wechat-union-{digest[24:48]}"
        nickname = f"微信用户{digest[-5:].upper()}"
        avatar_url = f"https://cdn.mindwell.local/avatars/{digest[:12]}.png"

        return WeChatProfile(
            open_id=open_id,
            union_id=union_id,
            nickname=nickname,
            avatar_url=avatar_url,
            locale="zh-CN",
        )

