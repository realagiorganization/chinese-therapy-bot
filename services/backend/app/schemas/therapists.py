from typing import Optional

from pydantic import BaseModel, Field


class TherapistFilter(BaseModel):
    specialty: Optional[str] = None
    language: Optional[str] = None
    price_max: Optional[float] = Field(default=None, ge=0)


class TherapistSummary(BaseModel):
    therapist_id: str
    name: str
    title: str
    specialties: list[str]
    languages: list[str]
    price_per_session: float
    currency: str = "CNY"
    is_recommended: bool = False


class TherapistListResponse(BaseModel):
    items: list[TherapistSummary]


class TherapistDetailResponse(TherapistSummary):
    biography: str
    availability: list[str] = Field(default_factory=list)
