"""Provider-independent smart home model helpers and safety rules."""

from __future__ import annotations

import re
from typing import Any

from backend.app.schemas import SmartHomeEntityResponse

PROVIDER_NAME = "home_assistant"
SUPPORTED_DOMAINS = ("light", "switch", "scene", "sensor", "binary_sensor")
EXPOSED_SUPPORTED_DOMAINS = ("light", "switch", "scene", "sensor")
CONTROL_DOMAINS = ("light", "switch")
SCENE_DOMAIN = "scene"
SENSOR_DOMAINS = ("sensor", "binary_sensor")
BLOCKED_HIGH_RISK_DOMAINS = (
    "alarm_control_panel",
    "camera",
    "cover",
    "garage_door",
    "lock",
    "vacuum",
)
FUTURE_DOMAINS = (
    "climate",
    "media_player",
)
ENTITY_ID_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*\.[a-z0-9_]+$")


class SmartHomeError(RuntimeError):
    """Base error for smart home operations."""


class SmartHomeConfigurationError(SmartHomeError):
    """Raised when smart home control is disabled or unconfigured."""


class SmartHomeProviderError(SmartHomeError):
    """Raised when the smart home provider cannot complete an operation."""


class SmartHomeSafetyError(SmartHomeError):
    """Raised when an action is outside the current safety boundary."""


def validate_entity_id(entity_id: str) -> str:
    """Validate entity IDs before they reach any provider API path."""

    cleaned = entity_id.strip().lower()
    if not ENTITY_ID_PATTERN.fullmatch(cleaned):
        raise SmartHomeSafetyError("Invalid smart home entity ID.")
    return cleaned


def entity_domain(entity_id: str) -> str:
    return validate_entity_id(entity_id).split(".", 1)[0]


def exposed_device_type(domain: str) -> str:
    if domain == "binary_sensor":
        return "sensor"
    return domain


def risk_classification(domain: str) -> str:
    if domain in SENSOR_DOMAINS:
        return "read_only"
    if domain in {*CONTROL_DOMAINS, SCENE_DOMAIN}:
        return "low"
    if domain in BLOCKED_HIGH_RISK_DOMAINS:
        return "high"
    return "future_or_unsupported"


def supported_actions_for_domain(domain: str) -> list[str]:
    if domain in CONTROL_DOMAINS:
        return ["turn_on", "turn_off"]
    if domain == SCENE_DOMAIN:
        return ["activate"]
    return []


def is_supported_domain(domain: str) -> bool:
    return domain in SUPPORTED_DOMAINS


def is_sensor_domain(domain: str) -> bool:
    return domain in SENSOR_DOMAINS


def ensure_supported_domain(domain: str) -> None:
    if domain in BLOCKED_HIGH_RISK_DOMAINS:
        raise SmartHomeSafetyError(
            f"{domain} is a high-risk smart home domain and is blocked."
        )
    if domain in FUTURE_DOMAINS:
        raise SmartHomeSafetyError(
            f"{domain} is planned for future support but is blocked in this phase."
        )
    if not is_supported_domain(domain):
        raise SmartHomeSafetyError(f"{domain} is not supported in this phase.")


def ensure_control_allowed(entity_id: str, action: str) -> str:
    domain = entity_domain(entity_id)
    ensure_supported_domain(domain)

    if domain in SENSOR_DOMAINS:
        raise SmartHomeSafetyError("Sensors are read-only in this phase.")

    if action in {"turn_on", "turn_off"} and domain not in CONTROL_DOMAINS:
        raise SmartHomeSafetyError(f"{action} is only allowed for lights and switches.")

    if action == "activate" and domain != SCENE_DOMAIN:
        raise SmartHomeSafetyError("Scene activation is only allowed for scenes.")

    if action not in supported_actions_for_domain(domain):
        raise SmartHomeSafetyError(f"{action} is not supported for {domain}.")

    return domain


def normalize_entity(payload: dict[str, Any]) -> SmartHomeEntityResponse | None:
    """Normalize a Home Assistant state object into Mirrage's safe shape."""

    raw_entity_id = str(payload.get("entity_id") or "").strip().lower()
    if not raw_entity_id:
        return None

    try:
        domain = entity_domain(raw_entity_id)
    except SmartHomeSafetyError:
        return None

    if not is_supported_domain(domain):
        return None

    attributes = payload.get("attributes")
    if not isinstance(attributes, dict):
        attributes = {}

    friendly_name = _optional_str(attributes.get("friendly_name"))
    name = friendly_name or _name_from_entity_id(raw_entity_id)
    state = str(payload.get("state") or "unknown")

    return SmartHomeEntityResponse(
        entity_id=raw_entity_id,
        name=name,
        domain=domain,
        device_type=exposed_device_type(domain),
        state=state,
        available=state not in {"unavailable", "unknown"},
        room=_optional_str(
            attributes.get("area")
            or attributes.get("area_id")
            or attributes.get("room")
        ),
        friendly_name=friendly_name,
        supported_actions=supported_actions_for_domain(domain),
        last_updated=_optional_str(payload.get("last_updated")),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _name_from_entity_id(entity_id: str) -> str:
    return entity_id.split(".", 1)[1].replace("_", " ").title()
