from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    """Minimal representation of a conversation exchange for evaluation context."""

    role: Literal["user", "assistant", "system"] = Field(..., description="Message author.")
    content: str = Field(..., description="Message text content.")


class ResponseEvaluationRequest(BaseModel):
    """Request payload for evaluating an assistant response."""

    user_message: str = Field(..., description="Latest user utterance prompting the assistant reply.")
    assistant_response: str = Field(..., description="Assistant reply to evaluate.")
    locale: str = Field(default="zh-CN", description="Locale hint used for heuristics.")
    conversation_context: list[ConversationTurn] = Field(
        default_factory=list,
        description="Optional prior turns to provide additional context.",
    )
    require_disclaimer: bool = Field(
        default=True,
        description="Whether the response should contain a mental health support disclaimer.",
    )


class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvaluationIssue(BaseModel):
    """Represents a single rule violation or concern."""

    code: str = Field(..., description="Machine-readable identifier for the issue.")
    severity: IssueSeverity = Field(..., description="Severity of the detected issue.")
    detail: str = Field(..., description="Human-readable explanation of the issue.")
    guidance: str = Field(..., description="Suggested remediation guidance.")


class EvaluationMetric(BaseModel):
    """Represents a scored metric contributing to the overall evaluation."""

    name: str = Field(..., description="Metric name.")
    score: float = Field(..., ge=0, le=1, description="Normalized metric score between 0 and 1.")
    detail: str = Field(..., description="Supporting description for the score.")


class ResponseEvaluationResult(BaseModel):
    """Overall evaluation outcome for an assistant response."""

    overall_score: float = Field(..., ge=0, le=1, description="Aggregate health score 0-1.")
    risk_level: IssueSeverity = Field(..., description="Risk level derived from detected issues.")
    issues: list[EvaluationIssue] = Field(default_factory=list)
    metrics: list[EvaluationMetric] = Field(default_factory=list)
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up actions for operators or agents.",
    )


class ResponseEvaluationResponse(BaseModel):
    """API response envelope for response evaluation."""

    result: ResponseEvaluationResult
