"""Privacy-aware personalization and deterministic greeting policy."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.app.services.identity_models import AuthenticatedPrincipal
from backend.app.services.identity_store import IdentityNotFoundError, identity_store
from backend.app.services.relationship_models import (
    GreetingResponse,
    PersonalizationProfileResponse,
    SafePersonalizationContext,
    VisibleProfileResponse,
)
from backend.app.services.relationship_store import relationship_store


def visible_profile(viewer_id: str, target_id: str) -> VisibleProfileResponse:
    """Filter a profile by field visibility; owner role is not a bypass."""

    viewer = identity_store.get_user(viewer_id)
    target = identity_store.get_user(target_id)
    profile = relationship_store.get_profile(target_id)
    relationship = relationship_store.active_relationship(viewer_id, target_id)
    same_household = viewer.household_member and target.household_member
    fields: dict[str, str | bool | None] = {}

    for field, visibility in profile.visibility.items():
        if _field_visible(
            owner=viewer_id == target_id,
            relationship=relationship,
            household=same_household,
            visibility=visibility,
        ):
            fields[field] = getattr(profile, field)

    return VisibleProfileResponse(
        user_id=target_id,
        fields=fields,
        visible_fields=sorted(fields),
    )


def profile_directory(viewer_id: str) -> list[VisibleProfileResponse]:
    return [
        visible_profile(viewer_id, user.public_id)
        for user in identity_store.list_users()
        if user.status == "active"
    ]


def greeting_for(principal: AuthenticatedPrincipal) -> GreetingResponse:
    """Return a deterministic, non-inferential greeting."""

    if not principal.authenticated or not principal.user_id:
        return _generic_greeting(principal)
    if principal.device_type == "mirror" and not principal.human_session_active:
        return _generic_greeting(principal)

    try:
        profile = relationship_store.get_profile(principal.user_id)
    except IdentityNotFoundError:
        return _generic_greeting(principal)
    quiet = is_quiet_hours(profile)
    personalized = bool(
        profile.personalized_greeting and profile.greeting_style != "none"
    )
    if profile.greeting_style == "none" or profile.proactivity == "silent":
        text = ""
    elif personalized:
        text = _named_greeting(profile)
    else:
        text = "Welcome back." if profile.greeting_style == "warm" else "Hello."

    return GreetingResponse(
        text=text,
        personalized=personalized and bool(text),
        quiet_hours=quiet,
        spoken_allowed=bool(profile.spoken_announcements and not quiet),
        human_session_active=principal.human_session_active,
    )


def build_safe_personalization_context(
    principal: AuthenticatedPrincipal | None,
) -> SafePersonalizationContext:
    """Build local and cloud-safe profile context for an authenticated person."""

    if (
        principal is None
        or not principal.authenticated
        or not principal.user_id
        or (principal.device_type == "mirror" and not principal.human_session_active)
    ):
        return SafePersonalizationContext()

    try:
        profile = relationship_store.get_profile(principal.user_id)
    except IdentityNotFoundError:
        return SafePersonalizationContext()
    quiet = is_quiet_hours(profile)
    local_lines = [
        f"Preferred name: {profile.preferred_display_name}.",
        f"Preferred language: {profile.preferred_language}.",
        f"Response tone: {profile.response_tone}.",
        f"Response length: {profile.response_length}.",
        f"Greeting style: {profile.greeting_style}.",
        f"Humour: {profile.humour}.",
    ]
    accessible = relationship_store.list_shared_context(principal.user_id)
    for item in accessible[:8]:
        local_lines.append(
            f"Explicit shared {item.context_type}: {item.title}: {item.value}"
        )

    cloud_lines: list[str] = []
    if profile.cloud_personalization_opt_in:
        cloud_lines = [
            f"Preferred language: {profile.preferred_language}.",
            f"Response tone: {profile.response_tone}.",
            f"Response length: {profile.response_length}.",
            f"Greeting style: {profile.greeting_style}.",
        ]
        if profile.visibility.get("preferred_display_name") == "public":
            cloud_lines.insert(0, f"Preferred name: {profile.preferred_display_name}.")

    return SafePersonalizationContext(
        local_lines=local_lines,
        cloud_lines=cloud_lines,
        sources=["profile", *(("shared_context",) if accessible else ())],
        quiet_hours=quiet,
        spoken_allowed=bool(profile.spoken_announcements and not quiet),
        proactivity=profile.proactivity,
    )


def is_quiet_hours(
    profile: PersonalizationProfileResponse, now: datetime | None = None
) -> bool:
    if not profile.quiet_hours_start or not profile.quiet_hours_end:
        return False
    try:
        zone = ZoneInfo(profile.time_zone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    current = (now or datetime.now(zone)).astimezone(zone).time().replace(tzinfo=None)
    start = time.fromisoformat(profile.quiet_hours_start)
    end = time.fromisoformat(profile.quiet_hours_end)
    if start == end:
        return True
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _field_visible(
    *, owner: bool, relationship: bool, household: bool, visibility: str
) -> bool:
    if owner:
        return True
    if visibility == "public":
        return True
    if visibility == "household":
        return household
    if visibility == "relationship":
        return relationship
    return False


def _generic_greeting(principal: AuthenticatedPrincipal) -> GreetingResponse:
    return GreetingResponse(
        text="Hello.",
        personalized=False,
        quiet_hours=False,
        spoken_allowed=False,
        human_session_active=principal.human_session_active,
    )


def _named_greeting(profile: PersonalizationProfileResponse) -> str:
    try:
        zone = ZoneInfo(profile.time_zone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    hour = datetime.now(zone).hour
    period = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    if profile.greeting_style == "minimal":
        return f"Hello, {profile.preferred_display_name}."
    return f"Good {period}, {profile.preferred_display_name}."
