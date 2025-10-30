from typing import Optional

from pydantic import BaseModel, Field


class TherapistFilter(BaseModel):
    specialty: Optional[str] = None
    language: Optional[str] = None
    price_max: Optional[float] = Field(default=None, ge=0)
    locale: str = Field(default="zh-CN", description="Preferred locale for localized fields.")
    is_recommended: Optional[bool] = Field(default=None, description="Filter by recommendation flag.")


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


class TherapistLocalePayload(BaseModel):
    locale: str
    title: Optional[str] = None
    biography: Optional[str] = None


class TherapistImportRecord(BaseModel):
    therapist_id: Optional[str] = None
    slug: str
    name: str
    title: Optional[str] = None
    biography: Optional[str] = None
    specialties: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    availability: list[str] = Field(default_factory=list)
    price_per_session: Optional[float] = None
    currency: str = "CNY"
    is_recommended: bool = False
    localizations: list[TherapistLocalePayload] = Field(default_factory=list)


class TherapistImportSummary(BaseModel):
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: list[str] = Field(default_factory=list)
    dry_run: bool = False
    total: int = 0


class TherapistSyncRequest(BaseModel):
    prefix: Optional[str] = Field(
        default=None,
        description="Override therapist data prefix if different from configuration.",
    )
    locales: Optional[list[str]] = Field(
        default=None,
        description="Restrict import to the specified locales.",
    )
    dry_run: bool = Field(
        default=False,
        description="When true, only evaluate changes without writing to the database.",
    )
