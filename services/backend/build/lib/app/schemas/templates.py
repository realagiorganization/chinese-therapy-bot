from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.services.templates import ChatTemplate


class ChatTemplateItem(BaseModel):
    """Serialized representation of a curated chat template."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    topic: str
    locale: str
    title: str
    user_prompt: str = Field(
        ...,
        serialization_alias="userPrompt",
        description="Suggested user opening line for the scene.",
    )
    assistant_example: str = Field(
        ...,
        serialization_alias="assistantExample",
        description="Example of how the assistant might respond supportively.",
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        serialization_alias="followUpQuestions",
        description="Follow-up questions a therapist may explore.",
    )
    self_care_tips: list[str] = Field(
        default_factory=list,
        serialization_alias="selfCareTips",
        description="Self-care nudges that align with the template.",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Keywords this template targets.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Additional tags supporting filtering and grouping.",
    )

    @classmethod
    def from_domain(cls, template: ChatTemplate) -> "ChatTemplateItem":
        return cls(
            id=template.id,
            topic=template.topic,
            locale=template.locale,
            title=template.title,
            user_prompt=template.user_prompt,
            assistant_example=template.assistant_example,
            follow_up_questions=list(template.follow_up_questions),
            self_care_tips=list(template.self_care_tips),
            keywords=list(template.keywords),
            tags=list(template.tags),
        )


class ChatTemplateListResponse(BaseModel):
    """Response payload for template listing."""

    model_config = ConfigDict(populate_by_name=True)

    locale: str
    topics: list[str]
    templates: list[ChatTemplateItem]
