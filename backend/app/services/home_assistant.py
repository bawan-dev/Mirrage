"""Home Assistant provider boundary for smart home control."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.app.services.smart_home_models import (
    SmartHomeProviderError,
    validate_entity_id,
)
from backend.app.settings import settings

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Small Home Assistant REST client.

    The token is only used in Authorization headers and must never be logged.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.home_assistant_base_url).rstrip("/")
        self.token = token or settings.home_assistant_token
        self.timeout = timeout or settings.smart_home_timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def states(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/states")
        if not isinstance(payload, list):
            raise SmartHomeProviderError("Home Assistant returned invalid state data.")
        return [item for item in payload if isinstance(item, dict)]

    def state(self, entity_id: str) -> dict[str, Any]:
        safe_entity_id = validate_entity_id(entity_id)
        payload = self._request("GET", f"/api/states/{safe_entity_id}")
        if not isinstance(payload, dict):
            raise SmartHomeProviderError("Home Assistant returned invalid entity data.")
        return payload

    def call_service(
        self,
        *,
        domain: str,
        service: str,
        entity_id: str,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        safe_entity_id = validate_entity_id(entity_id)
        return self._request(
            "POST",
            f"/api/services/{domain}/{service}",
            json={"entity_id": safe_entity_id},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, object] | None = None,
    ) -> Any:
        if not self.configured:
            raise SmartHomeProviderError("Home Assistant is not configured.")

        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.token}"},
                json=json,
                timeout=self.timeout,
            )
            response.raise_for_status()
            if response.content:
                return response.json()
            return {}
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "Home Assistant request failed.",
                extra={
                    "event": "smart_home_provider_error",
                    "subsystem": "smart_home",
                    "provider": "home_assistant",
                },
            )
            raise SmartHomeProviderError(
                "Home Assistant is unavailable right now."
            ) from exc
