from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import aioboto3
from openai import AsyncAzureOpenAI, AsyncOpenAI

from app.core.config import AppSettings


logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """LLM orchestration with Azure OpenAI primary and AWS Bedrock fallback."""

    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._azure_client: AsyncAzureOpenAI | None = None
        self._openai_client: AsyncOpenAI | None = None

        if settings.azure_openai_api_key and settings.azure_openai_endpoint and settings.azure_openai_deployment:
            self._azure_client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key.get_secret_value(),
                azure_endpoint=settings.azure_openai_endpoint,
                api_version=settings.azure_openai_api_version or "2024-02-15-preview",
            )
        elif settings.openai_api_key:
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())

    async def generate_reply(
        self,
        history: list[dict[str, str]],
        *,
        language: str = "zh-CN",
        max_tokens: int = 512,
    ) -> str:
        """Return a chat completion response using configured providers."""
        if self._azure_client:
            try:
                response = await self._azure_client.chat.completions.create(
                    model=self._settings.azure_openai_deployment,
                    messages=self._augment_history(history, language),
                    temperature=0.3,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content if response.choices else None
                if content:
                    return content.strip()
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("Azure OpenAI call failed, falling back to Bedrock/OpenAI stub", exc_info=exc)

        if self._openai_client:
            try:
                response = await self._openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self._augment_history(history, language),
                    temperature=0.4,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content if response.choices else None
                if content:
                    return content.strip()
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("OpenAI fallback failed, attempting Bedrock stub", exc_info=exc)

        if self._settings.bedrock_region and self._settings.bedrock_model_id:
            bedrock_text = await self._invoke_bedrock(history, language=language, max_tokens=max_tokens)
            if bedrock_text:
                return bedrock_text

        return self._heuristic_reply(history, language=language)

    async def stream_reply(
        self,
        history: list[dict[str, str]],
        *,
        language: str = "zh-CN",
        max_tokens: int = 512,
    ) -> AsyncIterator[str]:
        """Yield token fragments for a chat completion request."""
        if self._azure_client:
            try:
                stream = await self._azure_client.chat.completions.create(
                    model=self._settings.azure_openai_deployment,
                    messages=self._augment_history(history, language),
                    temperature=0.3,
                    max_tokens=max_tokens,
                    stream=True,
                )
                async for event in stream:
                    for choice in getattr(event, "choices", []):
                        delta = getattr(choice, "delta", None)
                        if not delta:
                            continue
                        content = getattr(delta, "content", None)
                        if content:
                            yield content
                return
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("Azure OpenAI streaming failed; falling back.", exc_info=exc)

        if self._openai_client:
            try:
                stream = await self._openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self._augment_history(history, language),
                    temperature=0.4,
                    max_tokens=max_tokens,
                    stream=True,
                )
                async for event in stream:
                    for choice in getattr(event, "choices", []):
                        delta = getattr(choice, "delta", None)
                        if not delta:
                            continue
                        content = getattr(delta, "content", None)
                        if content:
                            yield content
                return
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("OpenAI streaming failed; falling back.", exc_info=exc)

        fallback_reply = await self.generate_reply(
            history, language=language, max_tokens=max_tokens
        )
        for chunk in self._chunk_text(fallback_reply):
            yield chunk

    async def summarize_conversation(
        self,
        history: list[dict[str, str]],
        *,
        summary_type: str,
        language: str = "zh-CN",
        max_tokens: int = 640,
    ) -> dict[str, Any]:
        """Generate structured conversation summaries."""
        messages = self._build_summary_messages(history, summary_type=summary_type, language=language)

        if self._azure_client:
            try:
                response = await self._azure_client.chat.completions.create(
                    model=self._settings.azure_openai_deployment,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content if response.choices else None
                if content:
                    return self._parse_summary_response(content, summary_type=summary_type)
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("Azure OpenAI summarization failed, falling back.", exc_info=exc)

        if self._openai_client:
            try:
                response = await self._openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.3,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content if response.choices else None
                if content:
                    return self._parse_summary_response(content, summary_type=summary_type)
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("OpenAI summarization failed, attempting Bedrock.", exc_info=exc)

        if self._settings.bedrock_region and self._settings.bedrock_model_id:
            prompt = self._build_summary_prompt(history, summary_type=summary_type, language=language)
            bedrock_text = await self._invoke_bedrock_prompt(prompt, max_tokens=max_tokens)
            if bedrock_text:
                return self._parse_summary_response(bedrock_text, summary_type=summary_type)

        raise RuntimeError("Unable to generate summary with configured providers.")

    def _augment_history(self, history: list[dict[str, str]], language: str) -> list[dict[str, str]]:
        """Prepend a system prompt tailored for Chinese therapy support."""
        system_prompt = (
            "你是一名中文心理健康支持教练。提供温柔、结构化、务实的建议，并强调自我觉察。"
            "保持简洁的段落，并在需要时给出可执行的小练习。"
        )
        if language.startswith("zh"):
            system_prompt += " 回答请使用简体中文。"
        else:
            system_prompt += " You may respond bilingually if the user prefers."

        return [{"role": "system", "content": system_prompt}, *history]

    async def _invoke_bedrock(
        self,
        history: list[dict[str, str]],
        *,
        language: str,
        max_tokens: int,
    ) -> str | None:
        prompt = self._serialize_history(history, language)
        session_kwargs: dict[str, Any] = {"region_name": self._settings.bedrock_region}
        if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
            session_kwargs.update(
                {
                    "aws_access_key_id": self._settings.aws_access_key_id.get_secret_value(),
                    "aws_secret_access_key": self._settings.aws_secret_access_key.get_secret_value(),
                }
            )

        try:
            async with aioboto3.client("bedrock-runtime", **session_kwargs) as client:
                body = json.dumps(
                    {
                        "inputText": prompt,
                        "textGenerationConfig": {
                            "maxTokenCount": max_tokens,
                            "temperature": 0.4,
                            "topP": 0.9,
                        },
                    }
                )
                response = await client.invoke_model(
                    modelId=self._settings.bedrock_model_id,
                    body=body,
                )
                payload = await response["body"].read()
                parsed = json.loads(payload)
                results = parsed.get("results")
                if results:
                    text = results[0].get("outputText")
                    if text:
                        return text.strip()
        except Exception as exc:  # pragma: no cover - network failure path
            logger.warning("Bedrock invocation failed; using heuristic fallback", exc_info=exc)

        return None

    def _serialize_history(self, history: list[dict[str, str]], language: str) -> str:
        lines = [
            "你是 MindWell 的虚拟治疗师助手，请根据对话记录给出下一句温和的回应。",
            f"语言偏好: {language}",
            "对话记录：",
        ]
        for message in history[-10:]:
            role = "来访者" if message["role"] == "user" else "助手"
            lines.append(f"{role}: {message['content']}")
        lines.append("助手:")
        return "\n".join(lines)

    def _heuristic_reply(self, history: list[dict[str, str]], *, language: str) -> str:
        """Fallback deterministic reply mirroring legacy placeholder logic."""
        last_user_message = next(
            (message["content"] for message in reversed(history) if message["role"] == "user"),
            "",
        )

        if "焦虑" in last_user_message:
            response = "我听见你感到焦虑。先做三次腹式呼吸，观察身体的紧绷部位，然后写下触发情境。"
        elif any(keyword in last_user_message for keyword in ("睡", "失眠")):
            response = "睡眠的稳定离不开规律。我们可以一起建立放松流程，比如睡前30分钟远离屏幕。"
        elif "压力" in last_user_message or "加班" in last_user_message:
            response = "长期压力会消耗精力。试试番茄钟，将任务拆成25分钟的小块，并安排奖励性的休息。"
        else:
            response = "谢谢你的分享。我在这里陪你，可以继续描述最困扰你的情绪或事件，我们一起找出下一个可行的行动。"

        if not language.startswith("zh"):
            response += " (Reply translated: I am here with you. Please tell me more so we can plan the next small step.)"

        return response

    def _chunk_text(self, text: str, chunk_size: int = 80) -> list[str]:
        """Split text into human-friendly chunks when streaming providers are unavailable."""
        if not text:
            return []

        chunks: list[str] = []
        buffer = ""
        for character in text:
            buffer += character
            if character in {"。", "！", "？", ".", "!", "?"} and len(buffer) >= 8:
                chunks.append(buffer.strip())
                buffer = ""
            elif len(buffer) >= chunk_size:
                chunks.append(buffer.strip())
                buffer = ""

        if buffer:
            chunks.append(buffer.strip())

        return chunks

    def _build_summary_messages(
        self,
        history: list[dict[str, str]],
        *,
        summary_type: str,
        language: str,
    ) -> list[dict[str, str]]:
        instructions = self._summary_instructions(summary_type, language)
        transcript = self._render_summary_history(history, language=language)
        return [
            {"role": "system", "content": instructions},
            {"role": "user", "content": transcript},
        ]

    def _build_summary_prompt(
        self,
        history: list[dict[str, str]],
        *,
        summary_type: str,
        language: str,
    ) -> str:
        instructions = self._summary_instructions(summary_type, language)
        transcript = self._render_summary_history(history, language=language)
        return f"{instructions}\n\n{transcript}"

    def _summary_instructions(self, summary_type: str, language: str) -> str:
        zh = language.startswith("zh")
        if summary_type == "weekly":
            if zh:
                return (
                    "你是一名中文心理健康教练。请阅读以下对话记录，生成一份 JSON，总结本周重点。"
                    "JSON 字段必须包含: themes (字符串数组), highlights (字符串), "
                    "action_items (字符串数组), risk_level (low/medium/high)。"
                    "输出必须是有效 JSON，避免任何额外文本。"
                )
            return (
                "You are a bilingual mental health coach. Review the transcript and produce a JSON summary for the week. "
                "The JSON must contain: themes (array of strings), highlights (string), action_items (array of strings), "
                "risk_level (low/medium/high). Respond with valid JSON only."
            )

        if zh:
            return (
                "你是一名中文心理健康教练。请阅读以下对话记录，生成当天的 JSON 总结。"
                "JSON 字段必须包含: title (字符串), spotlight (字符串), summary (字符串)。"
                "输出必须是有效 JSON，避免额外文本。"
            )
        return (
            "You are a bilingual mental health coach. Review the transcript and create a JSON payload for today's summary. "
            "The JSON must include: title (string), spotlight (string), summary (string). "
            "Return valid JSON only."
        )

    def _render_summary_history(
        self,
        history: list[dict[str, str]],
        *,
        language: str,
        max_messages: int = 40,
    ) -> str:
        if not history:
            return "没有对话记录。"

        lines: list[str] = ["以下是按时间排序的对话记录：" if language.startswith("zh") else "Chronological transcript:"]
        for message in history[-max_messages:]:
            role = message.get("role", "")
            prefix = "来访者" if role == "user" else "助手"
            if not language.startswith("zh"):
                prefix = "User" if role == "user" else "Assistant"
            content = message.get("content", "")
            timestamp = message.get("created_at")
            if timestamp:
                lines.append(f"[{timestamp}] {prefix}: {content}")
            else:
                lines.append(f"{prefix}: {content}")
        return "\n".join(lines)

    def _parse_summary_response(self, content: str, *, summary_type: str) -> dict[str, Any]:
        sanitized = self._strip_json_fences(content.strip())
        try:
            parsed = json.loads(sanitized)
        except json.JSONDecodeError:
            logger.debug("Summary response not valid JSON; returning heuristic structure.")
            parsed = {}

        if summary_type == "weekly":
            themes = parsed.get("themes") if isinstance(parsed.get("themes"), list) else []
            action_items = parsed.get("action_items") if isinstance(parsed.get("action_items"), list) else []
            highlights = parsed.get("highlights") or parsed.get("summary") or ""
            risk_level = parsed.get("risk_level") or "low"
            return {
                "themes": [str(item) for item in themes],
                "highlights": str(highlights),
                "action_items": [str(item) for item in action_items],
                "risk_level": str(risk_level).lower(),
            }

        title = parsed.get("title") or parsed.get("heading") or "Daily Reflection"
        spotlight = parsed.get("spotlight") or parsed.get("focus") or ""
        summary = parsed.get("summary") or parsed.get("highlights") or ""
        return {
            "title": str(title),
            "spotlight": str(spotlight),
            "summary": str(summary),
        }

    def _strip_json_fences(self, value: str) -> str:
        if value.startswith("```"):
            value = value.strip()
            if value.lower().startswith("```json"):
                value = value[7:]
            elif value.startswith("```"):
                value = value[3:]
            if value.endswith("```"):
                value = value[:-3]
        return value.strip()

    async def _invoke_bedrock_prompt(self, prompt: str, *, max_tokens: int) -> str | None:
        session_kwargs: dict[str, Any] = {"region_name": self._settings.bedrock_region}
        if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
            session_kwargs.update(
                {
                    "aws_access_key_id": self._settings.aws_access_key_id.get_secret_value(),
                    "aws_secret_access_key": self._settings.aws_secret_access_key.get_secret_value(),
                }
            )

        try:
            async with aioboto3.client("bedrock-runtime", **session_kwargs) as client:
                body = json.dumps(
                    {
                        "inputText": prompt,
                        "textGenerationConfig": {
                            "maxTokenCount": max_tokens,
                            "temperature": 0.3,
                            "topP": 0.9,
                        },
                    }
                )
                response = await client.invoke_model(
                    modelId=self._settings.bedrock_model_id,
                    body=body,
                )
                payload = await response["body"].read()
                parsed = json.loads(payload)
                results = parsed.get("results")
                if results:
                    text = results[0].get("outputText")
                    if text:
                        return text.strip()
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Bedrock summarization failed", exc_info=exc)

        return None
