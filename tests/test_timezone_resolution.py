"""
Test timezone resolution priority logic.

Tests that the engine correctly resolves source timezone according to spec:
1. Explicit timezone in message (highest priority)
2. Sender's configured timezone
3. Onboarding required (no timezone available)
"""

import pytest

from src.engine import Engine, TelegramMessageContext, DiscordMessageContext
from src.models import Platform, Language
from src.storage import SQLiteStorage


def test_explicit_timezone_overrides_sender_profile_telegram(engine, storage):
    """Explicit timezone in message should override sender's configured timezone."""
    # Setup: user has Amsterdam configured
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    
    # Message with explicit timezone "Yerevan"
    ctx = TelegramMessageContext(
        chat_id="chat1",
        sender_id="user123",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30 Yerevan",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam", "Asia/Yerevan"],
    )
    
    # Should use Yerevan as source (explicit), not Amsterdam (profile)
    assert result is not None
    # Should not ask for onboarding
    assert "/tz set" not in result.text.lower()
    # Yerevan should be mentioned as source
    assert "Yerevan" in result.text


def test_sender_profile_used_when_no_explicit_timezone_telegram(engine, storage):
    """Sender's configured timezone should be used when no explicit timezone in message."""
    # Setup: user has Amsterdam configured
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    
    ctx = TelegramMessageContext(
        chat_id="chat1",
        sender_id="user123",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30",  # No explicit timezone
        ctx=ctx,
        active_timezones=["Europe/Amsterdam", "Asia/Yerevan"],
    )
    
    # Should use Amsterdam from sender profile
    assert result is not None
    assert "Amsterdam" in result.text


def test_onboarding_when_no_timezone_available_telegram(engine, storage):
    """Should request onboarding when no explicit timezone and no sender profile."""
    # User has NO timezone configured
    
    ctx = TelegramMessageContext(
        chat_id="chat1",
        sender_id="user_without_tz",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30",  # No explicit timezone
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )
    
    # Should return onboarding message
    assert result is not None
    assert "timezone" in result.text.lower()
    assert "/tz set" in result.text


def test_parser_does_not_detect_random_words_as_timezones(engine, storage):
    """
    Parser only recognizes known timezone formats.
    Random words are not parsed as timezones.
    """
    # Setup: user has Amsterdam configured
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    
    ctx = TelegramMessageContext(
        chat_id="chat1",
        sender_id="user123",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30 RandomWord",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam", "Asia/Yerevan"],
    )
    
    # "RandomWord" is not recognized as a timezone by the parser
    # So the bot uses the sender's configured timezone (Amsterdam)
    assert result is not None
    assert "Amsterdam" in result.text
    assert "10:30" in result.text
    # Should convert to active timezones
    assert "Yerevan" in result.text

    
def test_iana_timezone_string_recognized(engine, storage):
    """Valid IANA timezone string should be accepted as explicit timezone."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    
    ctx = TelegramMessageContext(
        chat_id="chat1",
        sender_id="user123",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30 Europe/Berlin",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )
    
    # Should use Europe/Berlin (explicit)
    assert result is not None
    assert "Berlin" in result.text


def test_explicit_timezone_overrides_sender_profile_discord(engine, storage):
    """Discord: Explicit timezone should override sender profile."""
    storage.set_user_timezone("discord", "sender1", "Europe/Amsterdam")
    storage.set_user_timezone("discord", "clicker1", "Asia/Yerevan")
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="meeting at 10:30 Europe/Berlin",  # Explicit
        original_sender_id="sender1",
        clicking_user_id="clicker1",
    )
    
    # Should use Berlin (explicit), not Amsterdam (profile)
    assert result is not None
    assert "Berlin" in result.text
    # Should NOT ask for onboarding
    assert "/tz set" not in result.text


def test_sender_profile_used_discord(engine, storage):
    """Discord: Sender profile used when no explicit timezone."""
    storage.set_user_timezone("discord", "sender1", "Europe/Amsterdam")
    storage.set_user_timezone("discord", "clicker1", "Asia/Yerevan")
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="meeting at 10:30",  # No explicit
        original_sender_id="sender1",
        clicking_user_id="clicker1",
    )
    
    # Should use Amsterdam from sender profile
    assert result is not None
    assert "Amsterdam" in result.text


def test_onboarding_when_sender_has_no_timezone_discord(engine, storage):
    """Discord: Onboarding when sender has no timezone."""
    # Only clicker has timezone
    storage.set_user_timezone("discord", "clicker1", "Asia/Yerevan")
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="meeting at 10:30",
        original_sender_id="sender_no_tz",
        clicking_user_id="clicker1",
    )
    
    # Should return onboarding
    assert result is not None
    assert "timezone" in result.text.lower()

def test_utc_offset_plus_recognized_as_explicit_telegram(engine, storage):
    """UTC offset like UTC+4 should be recognized as explicit timezone."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    
    ctx = TelegramMessageContext(
        chat_id="chat1",
        sender_id="user123",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30 UTC+4",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )
    
    # Should accept UTC+4 as explicit timezone
    assert result is not None
    # Should not ask for onboarding
    assert "/tz set" not in result.text.lower()


def test_utc_offset_colon_format_recognized(engine, storage):
    """UTC offset with colon (+04:00) should be recognized."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    
    ctx = TelegramMessageContext(
        chat_id="chat1",
        sender_id="user123",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30 +04:00",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )
    
    # Should accept +04:00 as explicit timezone
    assert result is not None
    # Should not be an error message about unrecognized timezone
    assert "recognize" not in result.text.lower()


def test_timezone_abbreviation_cet_recognized(engine, storage):
    """CET abbreviation should be recognized as explicit timezone."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    
    ctx = TelegramMessageContext(
        chat_id="chat1",
        sender_id="user123",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30 CET",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam", "Asia/Yerevan"],
    )
    
    # Should recognize CET
    assert result is not None
    # Should not be an error or onboarding message
    assert "/tz set" not in result.text.lower()
    assert "recognize" not in result.text.lower()


def test_timezone_abbreviation_pst_recognized(engine, storage):
    """PST abbreviation should be recognized as explicit timezone."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    
    ctx = TelegramMessageContext(
        chat_id="chat1",
        sender_id="user123",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30 PST",
        ctx=ctx,
        active_timezones=["Europe/Amsterdam"],
    )
    
    # Should recognize PST
    assert result is not None
    assert "/tz set" not in result.text.lower()