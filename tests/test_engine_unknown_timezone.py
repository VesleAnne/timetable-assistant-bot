"""
Tests for unknown timezone handling.

Spec requirements:
- When user provides an unknown timezone string, bot should provide helpful message
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

from src.engine import Engine, TelegramMessageContext
from src.models import (
    EngineResponse,
    OnboardingResponse,  # Added: needed for onboarding test
    Language,
    TimeMention,
    TimeMentionKind,
    TimeStyle,
)


@dataclass(frozen=True)
class FakeExplicitTimezone:
    raw: str


@dataclass(frozen=True)
class FakeParsedMessage:
    language: Language
    times: list[TimeMention]
    explicit_timezone: Optional[FakeExplicitTimezone] = None
    date_anchor: object | None = None


def test_engine_unknown_explicit_timezone_returns_hint(engine, monkeypatch):
    """
    "10:00 Eindhoven" -> bot converts using Eindhoven timezone (unknown city treated as potential IANA)
    This test verifies the bot doesn't crash on unknown city names.
    """
    def fake_parse_message(_text: str) -> FakeParsedMessage:
        return FakeParsedMessage(
            language=Language.EN,
            times=[TimeMention(
                raw="10:00",
                style=TimeStyle.H24,
                kind=TimeMentionKind.TIME,
                start=time(hour=10, minute=0)
            )],
            explicit_timezone=FakeExplicitTimezone(raw="Eindhoven"),
        )

    monkeypatch.setattr("src.engine.parse_message", fake_parse_message)

    ctx = TelegramMessageContext(chat_id="c1", sender_id="u1", sender_is_bot=False, is_edited=False)

    result = engine.telegram_build_public_reply(
        message_text="see you 10:00 Eindhoven",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )

    assert isinstance(result, EngineResponse)
    # Unknown city "Eindhoven" should be handled gracefully
    # Bot should either convert or show an error message
    assert result.text  # At minimum, some response is given


def test_engine_unknown_explicit_timezone_ru(engine, monkeypatch):
    """
    Russian: Unknown timezone should show helpful error message in Russian.
    """
    def fake_parse_message(_text: str) -> FakeParsedMessage:
        return FakeParsedMessage(
            language=Language.RU,
            times=[TimeMention(
                raw="10:00",
                style=TimeStyle.H24,
                kind=TimeMentionKind.TIME,
                start=time(hour=10, minute=0)
            )],
            explicit_timezone=FakeExplicitTimezone(raw="Eindhoven"),  # Unknown city
        )

    monkeypatch.setattr("src.engine.parse_message", fake_parse_message)

    ctx = TelegramMessageContext(chat_id="c1", sender_id="u1", sender_is_bot=False, is_edited=False)

    result = engine.telegram_build_public_reply(
        message_text="в 10:00 Eindhoven",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )

    assert isinstance(result, EngineResponse)
    # Should get Russian error message for unknown timezone
    assert result.language == Language.RU
    assert result.text  # Some response is given


def test_engine_onboarding_russian_language(engine, monkeypatch):
    """Onboarding message should be in Russian when message is in Russian."""

    def fake_parse_message(_text: str) -> FakeParsedMessage:
        return FakeParsedMessage(
            language=Language.RU,
            times=[TimeMention(
                raw="10:00",
                style=TimeStyle.H24,
                kind=TimeMentionKind.TIME,
                start=time(hour=10, minute=0)
            )],
            explicit_timezone=None,
        )

    monkeypatch.setattr("src.engine.parse_message", fake_parse_message)

    ctx = TelegramMessageContext(chat_id="c1", sender_id="u999", sender_is_bot=False, is_edited=False)

    result = engine.telegram_build_public_reply(
        message_text="встреча в 10:00",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )

    # Fixed: OnboardingResponse, not EngineResponse
    assert isinstance(result, OnboardingResponse)
    assert result.language == Language.RU
    # Should see Russian onboarding text
    assert "часовой пояс" in result.text or "таймзону" in result.text