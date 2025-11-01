from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


class SMSProvider:
    """Abstract SMS provider interface."""

    async def send_otp(
        self,
        phone_number: str,
        code: str,
        *,
        sender_id: str | None = None,
        locale: str | None = None,
    ) -> None:
        raise NotImplementedError


class ConsoleSMSProvider(SMSProvider):
    """Development provider that logs OTP payloads instead of sending them."""

    async def send_otp(
        self,
        phone_number: str,
        code: str,
        *,
        sender_id: str | None = None,
        locale: str | None = None,
    ) -> None:
        logger.info(
            "[SMS] Dispatching OTP %s to %s (sender=%s locale=%s)",
            code,
            phone_number,
            sender_id or "default",
            locale or "zh-CN",
        )

