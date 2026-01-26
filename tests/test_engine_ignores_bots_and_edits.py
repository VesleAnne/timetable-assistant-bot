"""
Test engine ignore rules for bots and edited messages.

Tests that the engine correctly ignores:
1. Messages sent by bot accounts (sender_is_bot=True)
2. Edited messages (is_edited=True)

These tests ensure the bot doesn't:
- Respond to itself
- Respond to other bots
- Respond to message edits (MVP limitation per spec)

Even if a time mention is detected in the message, the engine
must return None when these conditions are met.
"""


from __future__ import annotations

from dataclasses import dataclass

from src.engine import TelegramMessageContext
from src.models import Language


@dataclass(frozen=True)
class FakeParsedMessage:
    language: Language
    times: list[str]


def test_engine_ignores_bot_messages(engine, monkeypatch):
    def fake_parse_message(_text: str) -> FakeParsedMessage:
        return FakeParsedMessage(language=Language.EN, times=["10:00"])

    monkeypatch.setattr("src.engine.parse_message", fake_parse_message)


    ctx = TelegramMessageContext(chat_id="c1", sender_id="u1", sender_is_bot=True, is_edited=False)

    result = engine.telegram_build_public_reply(
        message_text="10:00",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )
    assert result is None


def test_engine_ignores_edited_messages(engine, monkeypatch):
    def fake_parse_message(_text: str) -> FakeParsedMessage:
        return FakeParsedMessage(language=Language.EN, times=["10:00"])

    monkeypatch.setattr("src.engine.parse_message", fake_parse_message)

    ctx = TelegramMessageContext(chat_id="c1", sender_id="u1", sender_is_bot=False, is_edited=True)

    result = engine.telegram_build_public_reply(
        message_text="10:00",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )
    assert result is None
