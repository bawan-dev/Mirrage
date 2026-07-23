"""Backend-owned plan and execution policy for bounded agents."""

from __future__ import annotations

from pydantic import ValidationError

from backend.app.services.agents.models import (
    AgentPlanStepProposal,
    AgentType,
    ValidatedAgentStep,
)
from backend.app.services.agents.registry import (
    UnknownAgentToolError,
    agent_tool_registry,
)
from backend.app.services.agents.store import AgentValidationError
from backend.app.services.authorization import authorization_service
from backend.app.services.identity_models import (
    AuthenticatedPrincipal,
    AuthorizationRequest,
)
from backend.app.services.permissions import Permission
from backend.app.settings import settings


class AgentPolicy:
    def validate_plan(
        self,
        principal: AuthenticatedPrincipal,
        agent_type: AgentType,
        proposals: list[AgentPlanStepProposal],
        *,
        max_steps: int,
    ) -> list[ValidatedAgentStep]:
        if not settings.agents_enabled:
            raise AgentValidationError("Agent execution is disabled.")
        if len(proposals) > min(max_steps, settings.agent_max_steps):
            raise AgentValidationError("The plan exceeds the configured step limit.")

        validated: list[ValidatedAgentStep] = []
        for proposal in proposals:
            try:
                tool = agent_tool_registry.get(proposal.tool_name)
                arguments = agent_tool_registry.validate_arguments(
                    proposal.tool_name, proposal.arguments
                )
            except (UnknownAgentToolError, ValidationError) as exc:
                raise AgentValidationError(
                    f"Step {proposal.tool_name!r} failed tool validation."
                ) from exc
            if agent_type not in tool.allowed_agent_types:
                raise AgentValidationError(
                    f"Tool {tool.name!r} is not allowed for this agent type."
                )
            self.authorize_tool(principal, tool.name, audit=True)
            validated.append(
                ValidatedAgentStep(
                    proposal=proposal.model_copy(
                        update={
                            "description": tool.description,
                            "arguments": arguments.model_dump(mode="json"),
                        }
                    ),
                    risk_level=tool.risk_level,
                    approval_required=bool(tool.side_effect or tool.approval_required),
                )
            )
        return validated

    def authorize_tool(
        self,
        principal: AuthenticatedPrincipal,
        tool_name: str,
        *,
        audit: bool,
    ) -> None:
        tool = agent_tool_registry.get(tool_name)
        execution_permission = (
            Permission.AGENTS_EXECUTE_LOW_RISK.value
            if tool.side_effect
            else Permission.AGENTS_EXECUTE_READ_ONLY.value
        )
        for permission in (execution_permission, tool.required_permission):
            decision = authorization_service.decide(
                principal,
                AuthorizationRequest(
                    permission=permission,
                    resource_type="agent_tool",
                    resource_id=tool.name,
                    risk_level=tool.risk_level,
                ),
                audit=audit,
            )
            if decision.decision != "allowed":
                raise AgentValidationError(
                    f"Permission denied for registered tool {tool.name!r}."
                )


agent_policy = AgentPolicy()
