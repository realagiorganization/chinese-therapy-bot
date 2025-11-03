from __future__ import annotations

import pytest
import httpx

from app.integrations.sms import TwilioSMSProvider


class DummyAsyncClient:
    """Minimal async client stub recording Twilio requests."""

    def __init__(self, response: httpx.Response):
        self._response = response
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self) -> DummyAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    async def post(self, url: str, *, data: dict[str, str], auth: tuple[str, str]):
        self.calls.append({"url": url, "data": data, "auth": auth})
        return self._response


@pytest.mark.asyncio
async def test_twilio_sms_provider_sends_message_with_from_number() -> None:
    response = httpx.Response(201, json={"sid": "SM123"})
    client = DummyAsyncClient(response)
    provider = TwilioSMSProvider(
        account_sid="AC123456789",
        auth_token="secret-token",
        from_number="+12025550123",
        client_factory=lambda: client,
    )

    await provider.send_otp(
        "+8613800138000",
        "987654",
        sender_id="MindWell",
        locale="zh-CN",
    )

    assert client.calls
    call = client.calls[-1]
    assert str(call["url"]).endswith("/Accounts/AC123456789/Messages.json")
    assert call["auth"] == ("AC123456789", "secret-token")
    data = call["data"]
    assert data["From"] == "+12025550123"
    assert data["To"] == "+8613800138000"
    assert "987654" in data["Body"]
    assert "MindWell" in data["Body"]


@pytest.mark.asyncio
async def test_twilio_sms_provider_surfaces_error_payload() -> None:
    response = httpx.Response(
        400, json={"code": 21211, "message": "The 'To' number is not a valid phone number."}
    )
    client = DummyAsyncClient(response)
    provider = TwilioSMSProvider(
        account_sid="AC123456789",
        auth_token="secret-token",
        from_number="+12025550123",
        client_factory=lambda: client,
    )

    with pytest.raises(RuntimeError) as excinfo:
        await provider.send_otp("+16175550000", "123456")

    message = str(excinfo.value)
    assert "Twilio error 21211" in message or "Twilio error: " in message


@pytest.mark.asyncio
async def test_twilio_sms_provider_formats_russian_message() -> None:
    response = httpx.Response(201, json={"sid": "SM456"})
    client = DummyAsyncClient(response)
    provider = TwilioSMSProvider(
        account_sid="AC123456789",
        auth_token="secret-token",
        from_number="+12025550123",
        client_factory=lambda: client,
    )

    await provider.send_otp("+79990000000", "654321", locale="ru-RU")

    assert client.calls
    body = client.calls[-1]["data"]["Body"]
    assert "654321" in body
    assert "действителен" in body.lower()
