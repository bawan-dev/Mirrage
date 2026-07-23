"""Typed models for persistent agent planning and execution."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AgentType = Literal["planning", "memory", "calendar", "smart_home", "research"]
AgentRunStatus = Literal[
    "draft",
    "planning",
    "awaiting_approval",
    "awaiting_user_input",
    "ready",
    "running",
    "paused",
    "completed",
    "failed",
    "cancelled",
    "expired",
]
AgentStepStatus = Literal[
    "proposed",
    "validated",
    "awaiting_approval",
    "ready",
    "running",
    "completed",
    "failed",
    "skipped",
    "cancelled",
]
AgentRiskLevel = Literal["read_only", "low", "medium", "high", "critical"]


class AgentRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_type: AgentType
    goal: str = Field(..., min_length=3, max_length=2000)
    max_steps: int | None = Field(default=None, ge=1, le=50)


class AgentPlanStepProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(..., min_length=3, max_length=300)
    tool_name: str = Field(..., min_length=3, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps: list[AgentPlanStepProposal] | None = Field(default=None, max_length=50)


class AgentRunResponse(BaseModel):
    public_id: str
    owner_user_id: str
    created_by_device_id: str | None
    agent_type: AgentType
    goal: str
    status: AgentRunStatus
    risk_level: AgentRiskLevel
    current_step: int
    total_steps: int
    max_steps: int
    provider: str | None
    model: str | None
    assumptions: list[str]
    expected_outcome: str | None
    stop_conditions: list[str]
    clarification_prompt: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None
    paused_at: str | None
    cancelled_at: str | None
    expires_at: str
    final_result: str | None
    error_summary: str | None
    correlation_id: str


class AgentStepResponse(BaseModel):
    public_id: str
    run_id: str
    step_number: int
    description: str
    tool_name: str
    arguments: dict[str, Any]
    status: AgentStepStatus
    risk_level: AgentRiskLevel
    approval_required: bool
    approval_id: str | None
    approval_status: str | None
    started_at: str | None
    completed_at: str | None
    retry_count: int
    output_summary: str | None
    error_summary: str | None


class AgentRunDetailResponse(BaseModel):
    run: AgentRunResponse
    steps: list[AgentStepResponse]


class AgentRunListResponse(BaseModel):
    items: list[AgentRunResponse]
    count: int


class AgentStepListResponse(BaseModel):
    items: list[AgentStepResponse]
    count: int


class AgentTypeResponse(BaseModel):
    name: AgentType
    description: str
    side_effects_allowed: bool
    live_web_access: bool = False


class AgentTypeListResponse(BaseModel):
    items: list[AgentTypeResponse]


class AgentToolResponse(BaseModel):
    name: str
    description: str
    required_permission: str
    risk_level: AgentRiskLevel
    side_effect: bool
    approval_required: bool
    timeout_seconds: float
    max_retries: int
    idempotent: bool
    allowed_agent_types: list[AgentType]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class AgentToolListResponse(BaseModel):
    items: list[AgentToolResponse]


class AgentEventResponse(BaseModel):
    public_id: str
    run_id: str
    step_id: str | None
    sequence: int
    event_type: str
    message: str
    created_at: str


class AgentEventListResponse(BaseModel):
    items: list[AgentEventResponse]
    count: int


class AgentStatusResponse(BaseModel):
    enabled: bool
    database_status: str
    active_run_count: int
    awaiting_approval_count: int
    failed_run_count: int
    queue_status: str
    concurrency_limit: int
    max_steps: int
    max_runtime_seconds: int
    message: str


class AgentApprovalQueueItem(BaseModel):
    approval_id: str
    run_id: str
    step_id: str
    requesting_user_id: str
    agent_type: AgentType
    tool_name: str
    description: str
    risk_level: AgentRiskLevel
    expires_at: str


class AgentApprovalQueueResponse(BaseModel):
    items: list[AgentApprovalQueueItem]
    count: int


class AgentApprovalDecisionRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class AgentApprovalDecisionResponse(BaseModel):
    approval_id: str
    run_id: str
    step_id: str
    status: Literal["approved", "denied"]


class AgentToolExecutionOutput(BaseModel):
    status: str = "ok"
    safe_summary: str = Field(..., min_length=1, max_length=500)
    result_text: str = Field(..., min_length=1, max_length=4000)


class AgentToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyToolInput(AgentToolInput):
    pass


class CalendarUpcomingInput(AgentToolInput):
    days: int = Field(default=7, ge=1, le=30)


class MemorySearchInput(AgentToolInput):
    query: str | None = Field(default=None, max_length=120)
    kind: Literal["preference", "fact", "goal", "routine"] | None = None


class MemoryCreateInput(AgentToolInput):
    kind: Literal["preference", "fact", "goal", "routine"]
    key: str = Field(..., min_length=1, max_length=120)
    value: str = Field(..., min_length=1, max_length=500)

    @field_validator("key", "value")
    @classmethod
    def reject_secret_material(cls, value: str) -> str:
        lowered = value.casefold()
        blocked = ("password", "api key", "secret key", "access token", "pin code")
        if any(term in lowered for term in blocked):
            raise ValueError("Agent memory tools do not accept secret material.")
        return value.strip()


class SharedContextCreateInput(AgentToolInput):
    context_type: Literal["plan", "reminder", "fact", "project", "preference"]
    title: str = Field(..., min_length=1, max_length=160)
    value: str = Field(..., min_length=1, max_length=500)


class SmartHomeEntityInput(AgentToolInput):
    entity_id: str = Field(..., pattern=r"^(light|switch)\.[a-z0-9_]+$")


class SmartHomeSceneInput(AgentToolInput):
    entity_id: str = Field(..., pattern=r"^scene\.[a-z0-9_]+$")


class OrganizeInput(AgentToolInput):
    source: Literal["run_goal"] = "run_goal"


class PlannerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assumptions: list[str] = Field(default_factory=list, max_length=10)
    steps: list[AgentPlanStepProposal] = Field(default_factory=list, max_length=50)
    expected_outcome: str = Field(..., min_length=3, max_length=500)
    stop_conditions: list[str] = Field(default_factory=list, max_length=10)
    clarification_prompt: str | None = Field(default=None, max_length=500)
    provider: str | None = None
    model: str | None = None


class ValidatedAgentStep(BaseModel):
    proposal: AgentPlanStepProposal
    risk_level: AgentRiskLevel
    approval_required: bool
