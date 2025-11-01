from fastapi.testclient import TestClient

from app.core.app import create_app
from app.services.templates import ChatTemplateService


def test_template_service_filters_by_topic() -> None:
    service = ChatTemplateService()

    templates = service.list_templates(locale="zh-CN", topic="anxiety", limit=5)
    assert templates, "Expected at least one anxiety template in zh-CN locale."
    assert all(template.topic == "anxiety" for template in templates)


def test_template_service_keyword_filter() -> None:
    service = ChatTemplateService()

    templates = service.list_templates(
        locale="en-US", keywords=["insomnia"], limit=5
    )
    assert templates, "Expected insomnia keyword to surface sleep templates."
    assert any("sleep" in template.topic for template in templates)


def test_chat_templates_endpoint_returns_payload() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/chat/templates", params={"locale": "en-US", "limit": 2})
    assert response.status_code == 200

    payload = response.json()
    assert payload["locale"] == "en-US"
    assert "topics" in payload and payload["topics"]
    assert "templates" in payload and payload["templates"]
    assert len(payload["templates"]) <= 2

    template = payload["templates"][0]
    assert template["topic"]
    assert template["userPrompt"]
    assert template["assistantExample"]


def test_chat_templates_endpoint_falls_back_for_unknown_locale() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/chat/templates", params={"locale": "fr-FR", "limit": 1})
    assert response.status_code == 200

    payload = response.json()
    assert payload["locale"] == "fr-FR"
    assert payload["templates"], "Fallback templates should be returned."
