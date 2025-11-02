from __future__ import annotations

import logging
from typing import Callable

import httpx


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


class TwilioSMSProvider(SMSProvider):
    """Twilio-backed SMS provider for production OTP delivery."""

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        *,
        from_number: str | None = None,
        messaging_service_sid: str | None = None,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ):
        if not from_number and not messaging_service_sid:
            raise ValueError(
                "TwilioSMSProvider requires either from_number or messaging_service_sid."
            )

        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number
        self._messaging_service_sid = messaging_service_sid
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        )
        self._endpoint = (
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        )

    async def send_otp(
        self,
        phone_number: str,
        code: str,
        *,
        sender_id: str | None = None,
        locale: str | None = None,
    ) -> None:
        payload = {
            "To": phone_number,
            "Body": self._format_message(code, locale=locale, sender_id=sender_id),
        }
        if self._messaging_service_sid:
            payload["MessagingServiceSid"] = self._messaging_service_sid
        else:
            payload["From"] = self._from_number

        try:
            async with self._client_factory() as client:
                response = await client.post(
                    self._endpoint,
                    data=payload,
                    auth=(self._account_sid, self._auth_token),
                )
        except httpx.HTTPError as exc:
            raise RuntimeError("Failed to send SMS via Twilio.") from exc

        if response.status_code < 200 or response.status_code >= 300:
            message = self._extract_error(response)
            raise RuntimeError(message)

        logger.info("[SMS] Twilio delivered OTP to %s", phone_number)

    def _format_message(
        self,
        code: str,
        *,
        locale: str | None,
        sender_id: str | None,
    ) -> str:
        brand = sender_id or "MindWell"
        normalized_locale = (locale or "zh-CN").lower()
        if normalized_locale.startswith("zh"):
            return f"【{brand}】您的验证码是 {code}，5 分钟内有效。"
        return f"{brand} verification code: {code}. It expires in 5 minutes."

    def _extract_error(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        message = None
        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("Message")
            code = payload.get("code") or payload.get("status")
            if message and code:
                return f"Twilio error {code}: {message}"
            if message:
                return f"Twilio error: {message}"

        return f"Twilio SMS request failed with status {response.status_code}."
