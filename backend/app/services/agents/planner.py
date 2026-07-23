"""Structured agent planning with deterministic safe fallbacks."""

from __future__ import annotations

import json
import re
from typing import Any

from ai.runtime import assistant_runtime
from backend.app.services.agents.models import (
    AgentPlanStepProposal,
    AgentType,
    PlannerResult,
)
from backend.app.services.agents.registry import agent_tool_registry
from backend.app.services.identity_models import AuthenticatedPrincipal

_ENTITY_PATTERN = re.compile(r"\b(?:light|switch)\.[a-z0-9_]+\b")
_SCENE_PATTERN = re.compile(r"\bscene\.[a-z0-9_]+\b")


class AgentPlanner:
    def propose(
        self,
        *,
        goal: str,
        agent_type: AgentType,
        principal: AuthenticatedPrincipal,
        explicit_steps: list[AgentPlanStepProposal] | None = None,
    ) -> PlannerResult:
        if explicit_steps is not None:
            return PlannerResult(
                assumptions=["The user supplied the proposed steps directly."],
                steps=explicit_steps,
                expected_outcome="Complete the validated user-supplied plan.",
                stop_conditions=[
                    "Stop on denial, cancellation, timeout, or tool failure."
                ],
                provider="user",
                model=None,
            )

        prompt = self._prompt(goal, agent_type)
        runtime = assistant_runtime.run_assistant_request(
            prompt,
            task_type="agent_planning",
            principal=principal,
        )
        parsed = self._parse_runtime_plan(runtime.reply)
        if parsed is not None:
            return parsed.model_copy(
                update={"provider": runtime.provider, "model": runtime.model}
            )
        fallback = self._deterministic_plan(goal, agent_type)
        return fallback.model_copy(
            update={"provider": runtime.provider, "model": runtime.model}
        )

    @staticmethod
    def _prompt(goal: str, agent_type: AgentType) -> str:
        tools = [
            descriptor.model_dump(
                include={"name", "description", "input_schema"},
                mode="json",
            )
            for descriptor in agent_tool_registry.descriptors()
            if agent_type in descriptor.allowed_agent_types
        ]
        shape = {
            "assumptions": ["short assumption"],
            "steps": [
                {
                    "description": "short step",
                    "tool_name": "registered.tool",
                    "arguments": {},
                }
            ],
            "expected_outcome": "short outcome",
            "stop_conditions": ["short condition"],
            "clarification_prompt": None,
        }
        return (
            "Return JSON only. Propose a bounded Mirrage agent plan. "
            "Use only listed tools and never invent arguments. Backend policy "
            "will independently validate every step. Do not include hidden "
            "reasoning or request unrelated personal data.\n"
            f"Agent type: {agent_type}\n"
            f"Goal: {goal}\n"
            f"Allowed tools: {json.dumps(tools, separators=(',', ':'))}\n"
            f"Required JSON shape: {json.dumps(shape, separators=(',', ':'))}"
        )

    @staticmethod
    def _parse_runtime_plan(reply: str) -> PlannerResult | None:
        text = reply.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
        try:
            payload: Any = json.loads(text)
            return PlannerResult.model_validate(payload)
        except (json.JSONDecodeError, ValueError):
            return None

    def _deterministic_plan(self, goal: str, agent_type: AgentType) -> PlannerResult:
        normalized = " ".join(goal.casefold().split())
        steps: list[AgentPlanStepProposal] = []
        clarification: str | None = None

        if agent_type == "calendar":
            steps.append(_step("Read today's schedule.", "calendar.read_today"))
            if any(word in normalized for word in ("week", "upcoming", "next")):
                steps.append(
                    _step(
                        "Read the next seven days.",
                        "calendar.read_upcoming",
                        {"days": 7},
                    )
                )
        elif agent_type == "memory":
            memory_match = re.search(
                r"(?:store|remember)\s+memory\s*:\s*"
                r"(preference|fact|goal|routine)\s*\|\s*"
                r"([^|]+)\|\s*(.+)$",
                goal,
                flags=re.IGNORECASE,
            )
            if memory_match:
                kind, key, value = (part.strip() for part in memory_match.groups())
                steps.append(
                    _step(
                        "Store the approved memory entry.",
                        "memory.create_own",
                        {"kind": kind.casefold(), "key": key, "value": value},
                    )
                )
            elif any(word in normalized for word in ("write", "store", "remember")):
                clarification = (
                    "Use `Store memory: kind | key | value` so Mirrage does not "
                    "guess what permanent information to save."
                )
            else:
                steps.extend(
                    [
                        _step(
                            "Search relevant private memory.",
                            "memory.search_own",
                            {"query": goal[:120]},
                        ),
                        _step("Summarize private memory.", "memory.summary_own"),
                    ]
                )
        elif agent_type == "smart_home":
            entity = _ENTITY_PATTERN.search(normalized)
            scene = _SCENE_PATTERN.search(normalized)
            if scene and any(word in normalized for word in ("activate", "start")):
                steps.append(
                    _step(
                        "Activate the approved scene.",
                        "smart_home.activate_approved_scene",
                        {"entity_id": scene.group(0)},
                    )
                )
            elif entity and "turn on" in normalized:
                steps.append(
                    _step(
                        "Turn on the approved light or switch.",
                        "smart_home.turn_on_approved_light",
                        {"entity_id": entity.group(0)},
                    )
                )
            elif entity and "turn off" in normalized:
                steps.append(
                    _step(
                        "Turn off the approved light or switch.",
                        "smart_home.turn_off_approved_light",
                        {"entity_id": entity.group(0)},
                    )
                )
            elif any(word in normalized for word in ("turn", "activate", "switch")):
                clarification = (
                    "Specify an approved entity ID such as `light.office` or "
                    "`scene.evening`; Mirrage will not guess a household device."
                )
            else:
                steps.extend(
                    [
                        _step(
                            "Read supported smart-home entities.",
                            "smart_home.read_entities",
                        ),
                        _step(
                            "Read supported smart-home sensors.",
                            "smart_home.read_sensors",
                        ),
                    ]
                )
        elif agent_type == "research":
            steps.append(
                _step(
                    "Organize the supplied material without external research.",
                    "research.organize_input",
                )
            )
        else:
            if "weather" in normalized:
                steps.append(_step("Read current weather.", "weather.read"))
            if any(word in normalized for word in ("calendar", "schedule", "day")):
                steps.append(_step("Read today's schedule.", "calendar.read_today"))
            if any(word in normalized for word in ("goal", "memory", "routine")):
                steps.append(_step("Summarize private memory.", "memory.summary_own"))
            if not steps:
                steps.extend(
                    [
                        _step("Read the current profile.", "profile.read_self"),
                        _step("Read safe system status.", "system.read_safe_status"),
                    ]
                )

        return PlannerResult(
            assumptions=[
                "Only registered local or configured internal tools may run.",
                "No live web research or arbitrary computer access is available.",
            ],
            steps=steps,
            expected_outcome=(
                "Return a concise result from the validated steps."
                if not clarification
                else "Resume planning after the user supplies the missing detail."
            ),
            stop_conditions=[
                "Stop on permission denial, rejected approval, cancellation, timeout, "
                "or tool failure."
            ],
            clarification_prompt=clarification,
        )


def _step(
    description: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> AgentPlanStepProposal:
    return AgentPlanStepProposal(
        description=description,
        tool_name=tool_name,
        arguments=arguments or {},
    )


agent_planner = AgentPlanner()
