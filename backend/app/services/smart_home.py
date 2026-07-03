"""Provider-independent smart home service layer."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from backend.app.schemas import (
    AssistantMessageResponse,
    SmartHomeActionResponse,
    SmartHomeEntitiesResponse,
    SmartHomeEntityResponse,
    SmartHomeStatusResponse,
)
from backend.app.services.home_assistant import HomeAssistantClient
from backend.app.services.smart_home_models import (
    CONTROL_DOMAINS,
    EXPOSED_SUPPORTED_DOMAINS,
    PROVIDER_NAME,
    SCENE_DOMAIN,
    SmartHomeConfigurationError,
    SmartHomeProviderError,
    SmartHomeSafetyError,
    ensure_control_allowed,
    entity_domain,
    normalize_entity,
    validate_entity_id,
)
from backend.app.settings import settings

logger = logging.getLogger(__name__)


class SmartHomeService:
    """Owns discovery, normalization, safety, and provider calls."""

    def __init__(self, provider: HomeAssistantClient | None = None) -> None:
        self.provider = provider or HomeAssistantClient()
        self._last_entities: list[SmartHomeEntityResponse] = []
        self._last_successful_sync: str | None = None
        self._last_error: str | None = None

    def status(self) -> SmartHomeStatusResponse:
        if not settings.smart_home_enabled:
            return self._status(
                enabled=False,
                configured=False,
                connection_status="disabled",
                entity_count=0,
                message="Smart home control is disabled.",
            )

        if not settings.home_assistant_enabled:
            return self._status(
                enabled=True,
                configured=False,
                connection_status="provider_disabled",
                entity_count=0,
                message="Home Assistant provider is disabled.",
            )

        if not self.provider.configured:
            return self._status(
                enabled=True,
                configured=False,
                connection_status="unconfigured",
                entity_count=0,
                message="Home Assistant base URL or token is not configured.",
            )

        try:
            entities = self.discover_entities(refresh=True)
        except SmartHomeProviderError:
            return self._status(
                enabled=True,
                configured=True,
                connection_status="unavailable",
                entity_count=len(self._last_entities),
                message=self._last_error or "Home Assistant is unavailable.",
            )

        return self._status(
            enabled=True,
            configured=True,
            connection_status="connected",
            entity_count=len(entities),
            message="Home Assistant is connected.",
        )

    def entities_response(self) -> SmartHomeEntitiesResponse:
        try:
            entities = self.discover_entities(refresh=True)
        except SmartHomeConfigurationError as exc:
            return SmartHomeEntitiesResponse(
                status="disabled",
                provider=PROVIDER_NAME,
                items=[],
                count=0,
                message=str(exc),
            )
        except SmartHomeProviderError as exc:
            return SmartHomeEntitiesResponse(
                status="unavailable",
                provider=PROVIDER_NAME,
                items=[],
                count=0,
                message=str(exc),
            )

        return SmartHomeEntitiesResponse(
            status="ready",
            provider=PROVIDER_NAME,
            items=entities,
            count=len(entities),
            message=f"{len(entities)} smart home entities loaded.",
        )

    def sensors_response(self) -> SmartHomeEntitiesResponse:
        response = self.entities_response()
        sensors = [
            entity for entity in response.items if entity.device_type == "sensor"
        ]

        return SmartHomeEntitiesResponse(
            status=response.status,
            provider=response.provider,
            items=sensors,
            count=len(sensors),
            message=(
                f"{len(sensors)} smart home sensors loaded."
                if response.status == "ready"
                else response.message
            ),
        )

    def get_entity(self, entity_id: str) -> SmartHomeEntityResponse:
        self._ensure_configured()
        safe_entity_id = validate_entity_id(entity_id)
        domain = entity_domain(safe_entity_id)
        if domain not in (*CONTROL_DOMAINS, SCENE_DOMAIN, "sensor", "binary_sensor"):
            raise SmartHomeSafetyError(f"{domain} is not supported in this phase.")

        normalized = normalize_entity(self.provider.state(safe_entity_id))
        if normalized is None:
            raise SmartHomeProviderError("Smart home entity was not found.")
        return normalized

    def turn_on(self, entity_id: str) -> SmartHomeActionResponse:
        return self._run_control(entity_id, "turn_on")

    def turn_off(self, entity_id: str) -> SmartHomeActionResponse:
        return self._run_control(entity_id, "turn_off")

    def activate_scene(self, entity_id: str) -> SmartHomeActionResponse:
        return self._run_control(entity_id, "activate")

    def discover_entities(
        self, *, refresh: bool = False
    ) -> list[SmartHomeEntityResponse]:
        self._ensure_configured()

        if self._last_entities and not refresh:
            return list(self._last_entities)

        try:
            payload = self.provider.states()
        except SmartHomeProviderError as exc:
            self._last_error = str(exc)
            logger.warning(
                "Smart home discovery failed.",
                extra={
                    "event": "smart_home_discovery_failed",
                    "subsystem": "smart_home",
                    "provider": PROVIDER_NAME,
                },
            )
            raise

        entities = [
            normalized
            for item in payload
            if (normalized := normalize_entity(item)) is not None
        ]
        self._last_entities = entities
        self._last_successful_sync = datetime.now(UTC).isoformat()
        self._last_error = None
        logger.info(
            "Smart home discovery completed.",
            extra={
                "event": "smart_home_discovery_completed",
                "subsystem": "smart_home",
                "provider": PROVIDER_NAME,
            },
        )
        return list(entities)

    def _run_control(self, entity_id: str, action: str) -> SmartHomeActionResponse:
        self._ensure_configured()
        safe_entity_id = validate_entity_id(entity_id)

        try:
            domain = ensure_control_allowed(safe_entity_id, action)
        except SmartHomeSafetyError:
            logger.warning(
                "Blocked unsafe smart home action.",
                extra={
                    "event": "smart_home_action_blocked",
                    "subsystem": "smart_home",
                    "provider": PROVIDER_NAME,
                },
            )
            raise

        service_name = "turn_on" if action == "activate" else action
        service_domain = SCENE_DOMAIN if action == "activate" else domain

        self.provider.call_service(
            domain=service_domain,
            service=service_name,
            entity_id=safe_entity_id,
        )
        logger.info(
            "Smart home action sent.",
            extra={
                "event": "smart_home_action_sent",
                "subsystem": "smart_home",
                "provider": PROVIDER_NAME,
            },
        )

        entity = self.get_entity(safe_entity_id)
        label = "activated" if action == "activate" else action.replace("_", " ")
        return SmartHomeActionResponse(
            status="ok",
            message=f"{entity.name} {label}.",
            entity=entity,
        )

    def _ensure_configured(self) -> None:
        if not settings.smart_home_enabled:
            raise SmartHomeConfigurationError("Smart home control is disabled.")
        if not settings.home_assistant_enabled:
            raise SmartHomeConfigurationError("Home Assistant provider is disabled.")
        if not self.provider.configured:
            raise SmartHomeConfigurationError(
                "Home Assistant base URL or token is not configured."
            )

    def _status(
        self,
        *,
        enabled: bool,
        configured: bool,
        connection_status: str,
        entity_count: int,
        message: str,
    ) -> SmartHomeStatusResponse:
        return SmartHomeStatusResponse(
            enabled=enabled,
            configured=configured,
            provider=PROVIDER_NAME,
            connection_status=connection_status,
            entity_count=entity_count,
            supported_domains=list(EXPOSED_SUPPORTED_DOMAINS),
            last_successful_sync=self._last_successful_sync,
            message=message,
        )


smart_home_service = SmartHomeService()


def handle_smart_home_message(message: str) -> AssistantMessageResponse | None:
    """Handle safe smart-home awareness prompts without model control."""

    normalized = message.casefold()
    if "smart home" not in normalized and "sensor" not in normalized:
        return None

    if (
        "show" not in normalized
        and "list" not in normalized
        and "devices" not in normalized
    ):
        return None

    response = (
        smart_home_service.sensors_response()
        if "sensor" in normalized
        else smart_home_service.entities_response()
    )

    if response.count == 0:
        reply = response.message
    else:
        names = ", ".join(entity.name for entity in response.items[:5])
        extra = response.count - 5
        reply = f"{response.count} smart home item(s): {names}"
        if extra > 0:
            reply += f", plus {extra} more."
        else:
            reply += "."

    return AssistantMessageResponse(
        reply=reply,
        provider="smart_home",
        model=None,
        context_action="smart_home",
    )
