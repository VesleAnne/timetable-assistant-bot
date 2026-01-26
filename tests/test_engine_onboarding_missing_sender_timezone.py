"""
Test onboarding flow when sender timezone is missing.

Tests that the engine correctly handles the case where:
1. A time mention is detected in the message
2. No explicit timezone is present in the message
3. The sender has NOT configured their timezone

Expected behavior (per spec Section 6):
- Engine must return an OnboardingResponse
- Response must ask the sender to set their timezone
- Response must include the command to set timezone (/tz set)
- NO conversion should be attempted

This ensures users are guided to configure their timezone
before the bot can perform conversions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.engine import TelegramMessageContext
from src.models import OnboardingResponse, Language


@dataclass(frozen=True)
class FakeParsedMessage:
    language: Language
    times: list[str]
    explicit_timezone: Optional[object] = None
    date_anchor: object | None = None


def test_telegram_onboarding_when_sender_has_no_timezone(engine, storage, monkeypatch):
    """
    If message contains a time but no explicit timezone and sender has no configured timezone,
    bot must onboard the sender.
    """

    def fake_parse_message(_text: str) -> FakeParsedMessage:
        return FakeParsedMessage(language=Language.EN, times=["10:00"], explicit_timezone=None)
    monkeypatch.setattr("src.engine.parse_message", fake_parse_message)


    ctx = TelegramMessageContext(chat_id="c1", sender_id="u1", sender_is_bot=False, is_edited=False)

    # Ensure no sender timezone in storage
    assert storage.get_user_timezone("telegram", "u1") is None

    result = engine.telegram_build_public_reply(
        message_text="see you at 10:00",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )

    assert isinstance(result, OnboardingResponse)
    assert "/tz set" in result.text
