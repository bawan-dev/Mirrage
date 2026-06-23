"""API request and response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MemoryKind = Literal["preference", "fact", "goal", "routine"]
MemoryStatus = Literal["active", "archived", "done"]


class AssistantMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class AssistantMessageResponse(BaseModel):
    reply: str
    provider: str
    model: str | None
    memory_action: str | None = None
    context_action: str | None = None


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
