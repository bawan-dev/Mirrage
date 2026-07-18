"""Typed relationship, personalization, shared-context, and session models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ResponseTone = Literal["neutral", "direct", "warm", "formal"]
ResponseLength = Literal["concise", "balanced", "detailed"]
GreetingStyle = Literal["none", "minimal", "standard", "warm"]
HumourLevel = Literal["off", "light"]
ProactivityLevel = Literal["silent", "low", "standard", "high"]
Visibility = Literal["private", "relationship", "household", "public"]
RelationshipType = Literal[
    "partner",
    "parent",
    "child",
    "sibling",
    "relative",
    "friend",
    "close_friend",
    "colleague",
    "housemate",
    "caregiver",
    "household_member",
    "custom",
]
RelationshipStatus = Literal["pending", "active", "rejected", "archived"]
SharedContextType = Literal["plan", "reminder", "fact", "project", "preference"]
SharedContextStatus = Literal["active", "archived"]
HumanSessionStatus = Literal["active", "ended", "expired"]

PROFILE_FIELDS = (
    "preferred_display_name",
    "preferred_language",
    "response_tone",
    "response_length",
    "greeting_style",
    "humour",
    "proactivity",
    "quiet_hours_start",
    "quiet_hours_end",
    "spoken_announcements",
    "personalized_greeting",
    "cloud_personalization_opt_in",
)


def default_profile_visibility() -> dict[str, Visibility]:
    return dict.fromkeys(PROFILE_FIELDS, "private")


class PersonalizationProfileResponse(BaseModel):
    user_id: str
    preferred_display_name: str
    preferred_language: str
    response_tone: ResponseTone
    response_length: ResponseLength
    greeting_style: GreetingStyle
    humour: HumourLevel
    proactivity: ProactivityLevel
    quiet_hours_start: str | None
    quiet_hours_end: str | None
    time_zone: str
    spoken_announcements: bool
    personalized_greeting: bool
    cloud_personalization_opt_in: bool
    visibility: dict[str, Visibility]
    created_at: str
    updated_at: str


class PersonalizationProfileUpdate(BaseModel):
    preferred_display_name: str | None = Field(
        default=None, min_length=1, max_length=120
    )
    preferred_language: str | None = Field(default=None, min_length=2, max_length=35)
    response_tone: ResponseTone | None = None
    response_length: ResponseLength | None = None
    greeting_style: GreetingStyle | None = None
    humour: HumourLevel | None = None
    proactivity: ProactivityLevel | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    time_zone: str | None = Field(default=None, min_length=1, max_length=80)
    spoken_announcements: bool | None = None
    personalized_greeting: bool | None = None
    cloud_personalization_opt_in: bool | None = None
    visibility: dict[str, Visibility] | None = None

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parts = value.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError("Quiet hours must use HH:MM format.")
        hour, minute = (int(part) for part in parts)
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("Quiet hours must use a valid 24-hour time.")
        return f"{hour:02d}:{minute:02d}"

    @field_validator("visibility")
    @classmethod
    def validate_visibility_fields(
        cls, value: dict[str, Visibility] | None
    ) -> dict[str, Visibility] | None:
        if value is None:
            return None
        unknown = set(value).difference(PROFILE_FIELDS)
        if unknown:
            raise ValueError(f"Unknown profile visibility field: {sorted(unknown)[0]}")
        return value


class VisibleProfileResponse(BaseModel):
    user_id: str
    fields: dict[str, str | bool | None]
    visible_fields: list[str]


class RelationshipCreateRequest(BaseModel):
    target_user_id: str = Field(..., min_length=1, max_length=80)
    relationship_type: RelationshipType
    custom_label: str | None = Field(default=None, min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_custom_label(self) -> RelationshipCreateRequest:
        if self.relationship_type == "custom" and not self.custom_label:
            raise ValueError("Custom relationships require a label.")
        if self.relationship_type != "custom" and self.custom_label:
            raise ValueError("Custom labels are only valid for custom relationships.")
        return self


class RelationshipResponse(BaseModel):
    public_id: str
    user_a_id: str
    user_b_id: str
    proposed_by_user_id: str
    proposed_to_user_id: str
    relationship_type: RelationshipType
    custom_label: str | None
    status: RelationshipStatus
    created_at: str
    updated_at: str
    responded_at: str | None
    archived_at: str | None


class RelationshipListResponse(BaseModel):
    items: list[RelationshipResponse]
    count: int


class SharedContextCreateRequest(BaseModel):
    context_type: SharedContextType
    title: str = Field(..., min_length=1, max_length=160)
    value: str = Field(..., min_length=1, max_length=2000)
    visibility: Visibility = "private"


class SharedContextUpdateRequest(BaseModel):
    context_type: SharedContextType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    value: str | None = Field(default=None, min_length=1, max_length=2000)
    visibility: Visibility | None = None


class SharedContextShareRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=80)


class SharedContextResponse(BaseModel):
    public_id: str
    owner_user_id: str
    context_type: SharedContextType
    title: str
    value: str
    visibility: Visibility
    status: SharedContextStatus
    shared_with_user_ids: list[str]
    created_at: str
    updated_at: str
    archived_at: str | None


class SharedContextListResponse(BaseModel):
    items: list[SharedContextResponse]
    count: int


class HumanSessionCreateRequest(BaseModel):
    duration_seconds: int | None = Field(default=None, ge=60, le=86400)


class HumanSessionResponse(BaseModel):
    public_id: str
    user_id: str
    device_id: str
    status: HumanSessionStatus
    created_at: str
    expires_at: str
    ended_at: str | None
    last_seen_at: str | None


class HumanSessionEnrollmentResponse(BaseModel):
    session: HumanSessionResponse
    token: str
    message: str = (
        "This confirms a temporary user selection; it is not biometric identity proof."
    )


class GreetingResponse(BaseModel):
    text: str
    personalized: bool
    quiet_hours: bool
    spoken_allowed: bool
    human_session_active: bool


class RelationshipHealthResponse(BaseModel):
    database_status: str
    profile_count: int
    active_relationship_count: int
    pending_relationship_count: int
    active_shared_context_count: int
    active_human_session_count: int


class SafePersonalizationContext(BaseModel):
    local_lines: list[str] = Field(default_factory=list)
    cloud_lines: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    quiet_hours: bool = False
    spoken_allowed: bool = False
    proactivity: ProactivityLevel = "silent"
