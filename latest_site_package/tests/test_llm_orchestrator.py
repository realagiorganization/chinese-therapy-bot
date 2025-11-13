from __future__ import annotations

import json

import pytest

from app.core.config import AppSettings
from app.integrations import llm as llm_module
from app.integrations.llm import ChatOrchestrator


@pytest.mark.asyncio
async def test_generate_reply_heuristic_fallback_returns_contextual_response() -> None:
    orchestrator = ChatOrchestrator(AppSettings())
    history = [{"role": "user", "content": "最近工作压力太大了"}]

    reply = await orchestrator.generate_reply(history, language="zh-CN")

    assert "长期压力会消耗精力" in reply


@pytest.mark.asyncio
async def test_generate_reply_uses_bedrock_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    invocations: list[dict[str, object]] = []

    class StubBody:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        async def read(self) -> bytes:
            return self._payload

    class StubBedrockClient:
        async def __aenter__(self) -> StubBedrockClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def invoke_model(self, *, modelId: str, body: str) -> dict[str, object]:
            invocations.append({"model_id": modelId, "body": json.loads(body)})
            payload = json.dumps(
                {"results": [{"outputText": "来自Bedrock的支持性回复。"}]}
            ).encode("utf-8")
            return {"body": StubBody(payload)}

    class StubSession:
        def client(self, *args, **kwargs):
            invocations.append({"client_args": args, "client_kwargs": kwargs})
            return StubBedrockClient()

    monkeypatch.setattr(
        llm_module.aioboto3,
        "Session",
        lambda: StubSession(),
    )

    settings = AppSettings(BEDROCK_REGION="us-east-1", BEDROCK_MODEL_ID="anthropic.claude-v2")
    orchestrator = ChatOrchestrator(settings)

    history = [{"role": "user", "content": "我感到有些焦虑"}]
    reply = await orchestrator.generate_reply(history, language="zh-CN")

    assert "来自Bedrock的支持性回复。" in reply
    assert any(entry.get("model_id") == "anthropic.claude-v2" for entry in invocations)


@pytest.mark.asyncio
async def test_stream_reply_falls_back_to_heuristic_when_providers_missing() -> None:
    orchestrator = ChatOrchestrator(AppSettings())
    history = [{"role": "user", "content": "最近总是失眠"}]

    fragments: list[str] = []
    async for fragment in orchestrator.stream_reply(history, language="zh-CN"):
        fragments.append(fragment)

    assert fragments, "Expected fallback streaming fragments."
    combined = "".join(fragments)
    assert "睡眠的稳定离不开规律" in combined
