"""API request and response schemas."""

from pydantic import BaseModel, Field


class AssistantMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class AssistantMessageResponse(BaseModel):
    reply: str
    provider: str
    model: str | None


class WeatherResponse(BaseModel):
    status: str
    location: str
    temperature_c: float | None
    condition: str
    updated: str | None
