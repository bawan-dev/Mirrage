"""Unit tests for the AI service layer and provider selection."""

import pytest

from ai.service import AssistantAIService


def test_stub_provider_replies() -> None:
    service = AssistantAIService("stub")
    result = service.reply("hello")

    assert result.provider == "stub"
    assert result.model is None
    assert isinstance(result.reply, str)
    assert result.reply


def test_provider_name_is_case_insensitive() -> None:
    service = AssistantAIService("STUB")

    assert service.reply("hi").provider == "stub"


def test_unsupported_provider_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported AI provider"):
        AssistantAIService("does-not-exist")
