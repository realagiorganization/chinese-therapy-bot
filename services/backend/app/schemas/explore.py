from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class ExploreModuleType(str, Enum):
    """Supported Explore module categories."""

    BREATHING_EXERCISE = "breathing_exercise"
    PSYCHOEDUCATION = "psychoeducation"
    TRENDING_TOPICS = "trending_topics"


class ExploreModuleBase(BaseModel):
    """Shared fields returned for every Explore module."""

    id: str
    module_type: ExploreModuleType
    title: str
    description: str
    feature_flag: str | None = Field(
        default=None, description="Feature flag key controlling the module visibility."
    )
    cta_label: str | None = None
    cta_action: str | None = None


class BreathingStep(BaseModel):
    label: str
    instruction: str
    duration_seconds: int


class BreathingExerciseModule(ExploreModuleBase):
    module_type: Literal[ExploreModuleType.BREATHING_EXERCISE] = (
        ExploreModuleType.BREATHING_EXERCISE
    )
    duration_minutes: int = 5
    cadence_label: str
    steps: list[BreathingStep] = Field(default_factory=list)
    recommended_frequency: str


class PsychoeducationResource(BaseModel):
    id: str
    title: str
    summary: str
    read_time_minutes: int
    tags: list[str] = Field(default_factory=list)
    resource_type: str = "article"
    url: str | None = None


class PsychoeducationModule(ExploreModuleBase):
    module_type: Literal[ExploreModuleType.PSYCHOEDUCATION] = ExploreModuleType.PSYCHOEDUCATION
    resources: list[PsychoeducationResource] = Field(default_factory=list)


class TrendingTopic(BaseModel):
    name: str
    momentum: int = Field(ge=0, le=100)
    trend: Literal["up", "steady", "down"] = "steady"
    summary: str


class TrendingTopicsModule(ExploreModuleBase):
    module_type: Literal[ExploreModuleType.TRENDING_TOPICS] = ExploreModuleType.TRENDING_TOPICS
    topics: list[TrendingTopic] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)


ExploreModule = Annotated[
    Union[BreathingExerciseModule, PsychoeducationModule, TrendingTopicsModule],
    Field(discriminator="module_type"),
]


class ExploreModulesResponse(BaseModel):
    locale: str
    modules: list[ExploreModule] = Field(default_factory=list)
    evaluated_flags: dict[str, bool] = Field(default_factory=dict)
