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
        context_prompt: str | None = None,
    ) -> str:
        """Return a chat completion response using configured providers."""
        if self._azure_client:
            try:
                response = await self._azure_client.chat.completions.create(
                    model=self._settings.azure_openai_deployment,
                    messages=self._augment_history(history, language, context_prompt=context_prompt),
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
                    messages=self._augment_history(history, language, context_prompt=context_prompt),
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

        return self._heuristic_reply(history, language=language, context_prompt=context_prompt)

    async def stream_reply(
        self,
        history: list[dict[str, str]],
        *,
        language: str = "zh-CN",
        max_tokens: int = 512,
        context_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield token fragments for a chat completion request."""
        if self._azure_client:
            try:
                stream = await self._azure_client.chat.completions.create(
                    model=self._settings.azure_openai_deployment,
                    messages=self._augment_history(history, language, context_prompt=context_prompt),
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
                    messages=self._augment_history(history, language, context_prompt=context_prompt),
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
            history, language=language, max_tokens=max_tokens, context_prompt=context_prompt
        )
        for chunk in self._chunk_text(fallback_reply):
            yield chunk

    async def translate_text(
        self,
        text: str,
        *,
        target_locale: str,
        source_locale: str | None = None,
        max_tokens: int = 320,
    ) -> str:
        """Translate free-form text to the specified locale."""
        if not text:
            return ""

        normalized_target = self._normalize_locale(target_locale)
        normalized_source = self._normalize_locale(source_locale) if source_locale else None
        if normalized_source and normalized_source == normalized_target:
            return text

        messages = self._build_translation_messages(
            text,
            target_locale=normalized_target,
            source_locale=normalized_source,
        )

        if self._azure_client:
            try:
                response = await self._azure_client.chat.completions.create(
                    model=self._settings.azure_openai_deployment,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content if response.choices else None
                if content:
                    return content.strip()
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("Azure OpenAI translation failed; attempting fallback.", exc_info=exc)

        if self._openai_client:
            try:
                response = await self._openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=max_tokens,
                )
                content = response.choices[0].message.content if response.choices else None
                if content:
                    return content.strip()
            except Exception as exc:  # pragma: no cover - network failure path
                logger.warning("OpenAI translation failed; attempting heuristic fallback.", exc_info=exc)

        return self._heuristic_translation_text(
            text,
            target_locale=normalized_target,
            source_locale=normalized_source,
        )

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

    def _augment_history(
        self,
        history: list[dict[str, str]],
        language: str,
        *,
        context_prompt: str | None = None,
    ) -> list[dict[str, str]]:
        """Prepend a system prompt tailored for the preferred locale."""
        normalized = (language or "").lower()
        is_chinese = normalized.startswith("zh")
        is_russian = normalized.startswith("ru")

        if is_chinese:
            system_prompt = (
                "你是一名中文心理健康支持教练。提供温柔、结构化、务实的建议，并强调自我觉察。"
                "保持简洁的段落，并在需要时给出可执行的小练习。"
                " 回答请使用简体中文。"
            )
        elif is_russian:
            system_prompt = (
                "Вы — эмпатичный русскоязычный ментальный помощник MindWell. "
                "Поддерживайте клиента тёплым, структурированным тоном, предлагайте небольшие шаги "
                "и напоминайте о заботе о себе. Отвечайте на чистом русском языке, с понятными абзацами и практичными рекомендациями."
            )
        else:
            system_prompt = (
                "You are a compassionate MindWell mental health coach. Offer gentle, structured, and pragmatic guidance "
                "while nurturing self-awareness. Respond in clear English unless the user explicitly prefers another language."
            )

        prompts = [{"role": "system", "content": system_prompt}]
        if context_prompt:
            prompts.append({"role": "system", "content": context_prompt})

        return [*prompts, *history]

    async def _invoke_bedrock(
        self,
        history: list[dict[str, str]],
        *,
        language: str,
        max_tokens: int,
    ) -> str | None:
        prompt = self._serialize_history(history, language)

        try:
            async with self._bedrock_client() as client:
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
        normalized = (language or "").lower()
        is_chinese = normalized.startswith("zh")
        is_russian = normalized.startswith("ru")

        if is_chinese:
            lines = [
                "你是 MindWell 的虚拟治疗师助手，请根据对话记录给出下一句温和的回应。",
                f"语言偏好: {language}",
                "对话记录：",
            ]
            for message in history[-10:]:
                role = "来访者" if message["role"] == "user" else "助手"
                lines.append(f"{role}: {message['content']}")
            lines.append("助手:")
        elif is_russian:
            lines = [
                "Вы — виртуальный помощник MindWell. Опираясь на контекст, предложите следующий поддерживающий ответ.",
                f"Предпочтительный язык: {language}",
                "Диалог:",
            ]
            for message in history[-10:]:
                role = "Клиент" if message["role"] == "user" else "Ассистент"
                lines.append(f"{role}: {message['content']}")
            lines.append("Ассистент:")
        else:
            lines = [
                "You are MindWell's therapeutic assistant. Provide the next compassionate, actionable reply.",
                f"Preferred language: {language}",
                "Transcript:",
            ]
            for message in history[-10:]:
                role = "User" if message["role"] == "user" else "Assistant"
                lines.append(f"{role}: {message['content']}")
            lines.append("Assistant:")
        return "\n".join(lines)

    def _heuristic_reply(
        self,
        history: list[dict[str, str]],
        *,
        language: str,
        context_prompt: str | None = None,
    ) -> str:
        """Fallback deterministic reply mirroring legacy placeholder logic."""
        last_user_message = next(
            (message["content"] for message in reversed(history) if message["role"] == "user"),
            "",
        )

        content_lower = last_user_message.lower()
        normalized = (language or "").lower()
        is_chinese = normalized.startswith("zh")
        is_russian = normalized.startswith("ru")
        is_english = normalized.startswith("en")

        anxiety_keywords = ("焦虑", "恐慌", "anxiety", "panic", "тревог", "паник")
        sleep_keywords = ("睡", "失眠", "sleep", "insom", "сон", "бессон")
        stress_keywords = ("压力", "加班", "stress", "burnout", "pressure", "стресс", "выгор")

        def _matches(keywords: tuple[str, ...]) -> bool:
            return any(keyword in last_user_message for keyword in keywords) or any(
                keyword in content_lower for keyword in keywords
            )

        if _matches(anxiety_keywords):
            if is_chinese:
                response = "我听见你感到焦虑。先做三次腹式呼吸，观察身体的紧绷部位，然后写下触发情境。"
            elif is_russian:
                response = "Я слышу, что тревога ощущается телом. Давайте попробуем три медленных цикла дыхания и отметим, где возникает напряжение, а затем запишем, что запускает волну."
            else:
                response = "I hear how anxiety is landing in your body. Let’s take three slow belly breaths, notice the tension points, and jot down what tends to trigger the surge."
        elif _matches(sleep_keywords):
            if is_chinese:
                response = "睡眠的稳定离不开规律。我们可以一起建立放松流程，比如睡前30分钟远离屏幕。"
            elif is_russian:
                response = "Сон стабилизируется благодаря ритуалам. Давайте соберём спокойный вечерний сценарий, например, 30 минут без экранов перед сном и мягкое расслабление."
            else:
                response = "Sleep steadies when routines feel predictable. We can co-create a wind-down, like unplugging screens 30 minutes before bed and adding a short relaxation cue."
        elif _matches(stress_keywords):
            if is_chinese:
                response = "长期压力会消耗精力。试试番茄钟，将任务拆成25分钟的小块，并安排奖励性的休息。"
            elif is_russian:
                response = "Длительное напряжение истощает. Попробуйте разбить задачи на 25-минутные отрезки с короткими приятными паузами, чтобы нервная система успевала восстанавливаться."
            else:
                response = "Sustained pressure drains energy. Consider 25-minute focus blocks with brief nourishing breaks so your nervous system can reset."
        else:
            if is_chinese:
                response = "谢谢你的分享。我在这里陪你，可以继续描述最困扰你的情绪或事件，我们一起找出下一个可行的行动。"
            elif is_russian:
                response = "Спасибо, что делитесь. Я рядом, можете продолжить рассказывать о том, что беспокоит сильнее всего, и мы вместе найдём следующий посильный шаг."
            else:
                response = "Thank you for opening up. I’m here with you—feel free to share what feels heaviest so we can co-create the next doable step."

        if context_prompt:
            if is_chinese:
                response += " 如果你愿意，也可以考虑与推荐的治疗师进一步交流。"
            elif is_russian:
                response += " Если почувствуете отклик, можно мягко рассмотреть контакт с рекомендованным терапевтом."
            else:
                response += " When it feels right, you could also consider connecting with one of the recommended therapists."

        if not (is_chinese or is_russian or is_english):
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

    def _build_translation_messages(
        self,
        text: str,
        *,
        target_locale: str,
        source_locale: str | None,
    ) -> list[dict[str, str]]:
        instructions = self._translation_instructions(target_locale, source_locale)
        return [
            {"role": "system", "content": instructions},
            {"role": "user", "content": text},
        ]

    def _translation_instructions(self, target_locale: str, source_locale: str | None) -> str:
        target_label = self._locale_label(target_locale)
        if source_locale:
            source_label = self._locale_label(source_locale)
            return (
                f"You are a certified clinical translator. Convert the user message from {source_label} "
                f"into {target_label}. Preserve the original meaning, tone, and formatting. "
                "Do not include footnotes or additional commentary. Return only the translated text."
            )
        return (
            f"You are a certified clinical translator. Render the user message in {target_label}. "
            "Preserve the meaning, tone, and formatting. Return only the translated text."
        )

    def _locale_label(self, locale: str) -> str:
        normalized = self._normalize_locale(locale)
        return {
            "zh-cn": "Simplified Chinese",
            "zh-tw": "Traditional Chinese",
            "en-us": "English",
            "ru-ru": "Russian",
        }.get(normalized, locale or "the target language")

    def _normalize_locale(self, locale: str | None) -> str:
        if not locale:
            return ""
        return locale.replace("_", "-").lower()

    def _heuristic_translation_text(
        self,
        text: str,
        *,
        target_locale: str,
        source_locale: str | None,
    ) -> str:
        normalized_source = source_locale or ""
        if target_locale == normalized_source:
            return text

        if normalized_source == "zh-cn" and target_locale == "zh-tw":
            return (
                text.replace("疗", "療")
                .replace("虑", "慮")
                .replace("复", "復")
                .replace("国", "國")
                .replace("专", "專")
                .replace("级", "級")
                .replace("术", "術")
            )
        if normalized_source == "zh-tw" and target_locale == "zh-cn":
            return (
                text.replace("療", "疗")
                .replace("慮", "虑")
                .replace("復", "复")
                .replace("國", "国")
                .replace("專", "专")
                .replace("級", "级")
                .replace("術", "术")
            )
        return text

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
        ru = language.startswith("ru")
        if summary_type == "memory":
            if zh:
                return (
                    "你是一名中文心理健康教练。请根据用户与助手的对话记录，提炼一段简洁的记忆摘要。"
                    "返回 JSON，字段包括: memory (字符串，总结用户关注点)、keywords (字符串数组，列出核心主题)。"
                    "只输出有效 JSON。"
                )
            if ru:
                return (
                    "Вы — русскоязычный ментальный помощник. Проанализируйте диалог и верните JSON "
                    "с полями memory (строка с фокусом клиента) и keywords (массив строк). "
                    "Ответьте строго валидным JSON."
                )
            return (
                "You are a bilingual mental health coach. Review the transcript and return JSON "
                "with fields memory (string summary of the user's focus) and keywords (array of strings). "
                "Respond with strictly valid JSON."
            )

        if summary_type == "weekly":
            if zh:
                return (
                    "你是一名中文心理健康教练。请阅读以下对话记录，生成一份 JSON，总结本周重点。"
                    "JSON 字段必须包含: themes (字符串数组), highlights (字符串), "
                    "action_items (字符串数组), risk_level (low/medium/high)。"
                    "输出必须是有效 JSON，避免任何额外文本。"
                )
            if ru:
                return (
                    "Вы — русскоязычный ментальный помощник. Проанализируйте диалог и составьте JSON-отчёт за неделю. "
                    "Обязательные поля: themes (массив строк), highlights (строка), "
                    "action_items (массив строк), risk_level (low/medium/high). "
                    "Верните только корректный JSON без дополнительного текста."
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
        if ru:
            return (
                "Вы — русскоязычный ментальный помощник. На основе диалога создайте ежедневную сводку в формате JSON. "
                "Обязательные поля: title (строка), spotlight (строка), summary (строка). "
                "Ответьте строго валидным JSON без лишнего текста."
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
            if language.startswith("zh"):
                return "没有对话记录。"
            if language.startswith("ru"):
                return "Диалогов пока нет."
            return "No transcript available."

        normalized = (language or "").lower()
        is_chinese = normalized.startswith("zh")
        is_russian = normalized.startswith("ru")

        if is_chinese:
            heading = "以下是按时间排序的对话记录："
        elif is_russian:
            heading = "Диалог в хронологическом порядке:"
        else:
            heading = "Chronological transcript:"

        lines: list[str] = [heading]
        for message in history[-max_messages:]:
            role = message.get("role", "")
            if is_chinese:
                prefix = "来访者" if role == "user" else "助手"
            elif is_russian:
                prefix = "Клиент" if role == "user" else "Ассистент"
            else:
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

        if summary_type == "memory":
            keywords = parsed.get("keywords") if isinstance(parsed.get("keywords"), list) else []
            memory_text = parsed.get("memory") or parsed.get("summary") or ""
            return {
                "summary": str(memory_text),
                "keywords": [str(item).strip() for item in keywords if str(item).strip()],
            }

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
        try:
            async with self._bedrock_client() as client:
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

    def _bedrock_client(self):
        session_kwargs: dict[str, Any] = {"region_name": self._settings.bedrock_region}
        if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
            session_kwargs.update(
                {
                    "aws_access_key_id": self._settings.aws_access_key_id.get_secret_value(),
                    "aws_secret_access_key": self._settings.aws_secret_access_key.get_secret_value(),
                }
            )

        session = aioboto3.Session()
        return session.client("bedrock-runtime", **session_kwargs)
