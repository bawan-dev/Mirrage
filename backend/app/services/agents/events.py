"""Persistent, privacy-safe event stream for agent run progress."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator

from backend.app.services.agents.models import AgentEventResponse
from backend.app.services.agents.store import agent_store


class AgentEventService:
    def emit(
        self,
        run_id: str,
        event_type: str,
        message: str,
        *,
        step_id: str | None = None,
    ) -> AgentEventResponse:
        return agent_store.append_event(
            run_id,
            event_type,
            message,
            step_id=step_id,
        )

    def stream(
        self,
        run_id: str,
        owner_user_id: str,
        *,
        after_sequence: int = 0,
        follow: bool = False,
    ) -> Iterator[str]:
        """Yield persisted events; optional follow is bounded to 30 seconds."""

        cursor = max(0, after_sequence)
        deadline = time.monotonic() + 30
        while True:
            events = agent_store.list_events(
                run_id, owner_user_id, after_sequence=cursor
            )
            for event in events:
                cursor = event.sequence
                payload = event.model_dump(mode="json")
                yield (
                    f"id: {event.sequence}\n"
                    f"event: {event.event_type}\n"
                    f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
                )
            if not follow or time.monotonic() >= deadline:
                break
            yield ": keep-alive\n\n"
            time.sleep(1)


agent_events = AgentEventService()
