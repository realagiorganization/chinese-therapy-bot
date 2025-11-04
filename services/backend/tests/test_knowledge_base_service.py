from __future__ import annotations

import pytest

from app.services.knowledge_base import KnowledgeBaseService


@pytest.mark.asyncio
async def test_search_returns_relevant_entries_for_locale() -> None:
    service = KnowledgeBaseService(None)

    results = await service.search("晚上经常睡不着，担心明天没精神。", locale="zh-CN", limit=2)

    assert results, "Expected at least one knowledge base entry."
    assert any(entry.entry_id == "sleep_regulation_cn" for entry in results)
    assert any("睡眠" in entry.summary for entry in results)


@pytest.mark.asyncio
async def test_search_respects_limit_and_locale_fallback() -> None:
    service = KnowledgeBaseService(None)

    results = await service.search("Panic makes my heart race.", locale="en-US", limit=1)

    assert len(results) <= 1
    assert any(entry.locale == "en-US" for entry in results)
    assert any("Grounding" in entry.title for entry in results)
