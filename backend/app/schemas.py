"""API request and response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MemoryKind = Literal["preference", "fact", "goal", "routine"]
MemoryStatus = Literal["active", "archived", "done"]
PresenceState = Literal[
    "sleeping",
    "idle",
    "wake_detected",
    "listening",
    "processing",
    "speaking",
    "returning_to_idle",
]


class AssistantMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class AssistantMessageResponse(BaseModel):
    reply: str
    provider: str
    model: str | None
    memory_action: str | None = None
    context_action: str | None = None


class PresenceSettings(BaseModel):
    wake_word_enabled: bool
    wake_phrase: str
    wake_word_engine: str
    sensitivity: float
    microphone_device: str | None
    inactivity_timeout_seconds: int
    automatic_sleep: bool
    privacy_mode: str
    message: str


class PresenceSettingsUpdate(BaseModel):
    wake_word_enabled: bool | None = None
    wake_phrase: str | None = Field(default=None, min_length=2, max_length=80)
    wake_word_engine: str | None = Field(default=None, min_length=2, max_length=80)
    sensitivity: float | None = Field(default=None, ge=0.0, le=1.0)
    microphone_device: str | None = Field(default=None, max_length=160)
    inactivity_timeout_seconds: int | None = Field(default=None, ge=5, le=3600)
    automatic_sleep: bool | None = None


class PresenceSnapshot(BaseModel):
    state: PresenceState
    previous_state: PresenceState | None
    event: str
    sequence: int
    wake_phrase: str
    wake_word_enabled: bool
    wake_word_engine: str
    transcript: str | None = None
    interim_transcript: str | None = None
    assistant_reply: str | None = None
    source: str
    message: str
    updated_at: str


class PresenceTransitionRequest(BaseModel):
    state: PresenceState
    event: str | None = Field(default=None, max_length=120)
    transcript: str | None = Field(default=None, max_length=4000)
    interim_transcript: str | None = Field(default=None, max_length=4000)
    assistant_reply: str | None = Field(default=None, max_length=4000)
    source: str = Field(default="frontend", max_length=120)
    message: str | None = Field(default=None, max_length=4000)


class WakeWordDetectionRequest(BaseModel):
    phrase: str = Field(..., min_length=1, max_length=200)
    engine: str | None = Field(default=None, max_length=120)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str = Field(default="wake_word_engine", max_length=120)


class AIRuntimeStatusResponse(BaseModel):
    runtime_mode: str
    configured_provider: str
    fallback_provider: str
    local_first: bool
    local_only: bool
    streaming_enabled: bool
    privacy_mode: str
    available_providers: list[str]
    default_task_model: str | None
    summary_model: str | None
    planning_model: str | None


class AIProviderInfoResponse(BaseModel):
    name: str
    kind: str
    configured: bool
    supports_streaming: bool
    default_model: str | None


class AIProvidersResponse(BaseModel):
    providers: list[AIProviderInfoResponse]


class MemoryCreateRequest(BaseModel):
    kind: MemoryKind
    key: str = Field(..., min_length=1, max_length=120)
    value: str = Field(..., min_length=1, max_length=2000)
    status: MemoryStatus = "active"
    source: str | None = Field(default=None, max_length=120)


class MemoryUpdateRequest(BaseModel):
    key: str | None = Field(default=None, min_length=1, max_length=120)
    value: str | None = Field(default=None, min_length=1, max_length=2000)
    status: MemoryStatus | None = None
    source: str | None = Field(default=None, max_length=120)


class MemoryRecordResponse(BaseModel):
    id: int
    kind: MemoryKind
    key: str
    value: str
    status: MemoryStatus
    source: str | None
    created_at: str
    updated_at: str


class MemorySearchResponse(BaseModel):
    items: list[MemoryRecordResponse]
    count: int


class MemorySummaryResponse(BaseModel):
    preferences: list[MemoryRecordResponse]
    facts: list[MemoryRecordResponse]
    goals: list[MemoryRecordResponse]
    routines: list[MemoryRecordResponse]
    count: int
    message: str


class ContextWeatherSummary(BaseModel):
    status: str
    location: str
    temperature_c: float | None
    condition: str
    summary: str
    updated: str | None
    message: str


class ContextCalendarSummary(BaseModel):
    status: str
    authenticated: bool
    today_event_count: int
    upcoming_event_count: int
    today_events: list[CalendarEventResponse]
    upcoming_events: list[CalendarEventResponse]
    message: str


class ContextMemorySummary(BaseModel):
    status: str
    preferences: list[MemoryRecordResponse]
    goals: list[MemoryRecordResponse]
    routines: list[MemoryRecordResponse]
    facts_count: int
    message: str


class ContextFocusSuggestion(BaseModel):
    title: str
    reason: str
    source: str
    priority: str


class DailyContext(BaseModel):
    status: str
    date: str
    generated_at: str
    weather: ContextWeatherSummary
    calendar: ContextCalendarSummary
    memory: ContextMemorySummary
    suggested_focus: list[ContextFocusSuggestion]
    message: str


class ProactiveSummaryResponse(BaseModel):
    status: str
    generated_at: str
    priority: str
    headline: str
    message: str
    suggestions: list[str]
    sources: list[str]
    should_interrupt: bool


class WeatherResponse(BaseModel):
    status: str
    location: str
    temperature_c: float | None
    condition: str
    updated: str | None


class CalendarStatusResponse(BaseModel):
    configured: bool
    authenticated: bool
    login_url: str | None
    calendar_id: str
    scopes: list[str]
    message: str


class CalendarEventResponse(BaseModel):
    id: str
    title: str
    start: str
    end: str | None
    is_all_day: bool
    location: str | None
    calendar: str | None
    html_link: str | None


class CalendarScheduleResponse(BaseModel):
    status: str
    authenticated: bool
    date: str
    time_zone: str
    events: list[CalendarEventResponse]
    updated: str | None
    message: str


class SpotifyStatusResponse(BaseModel):
    configured: bool
    authenticated: bool
    login_url: str | None
    scopes: list[str]
    message: str


class SpotifyPlaybackResponse(BaseModel):
    status: str
    authenticated: bool
    is_playing: bool
    title: str | None
    artist: str | None
    album: str | None
    artwork_url: str | None
    progress_ms: int | None
    duration_ms: int | None
    device_name: str | None
    device_type: str | None
    spotify_url: str | None
    updated: str | None
    message: str


class SpotifyActionResponse(BaseModel):
    status: str
    message: str
