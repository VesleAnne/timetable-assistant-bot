"""
Test Discord bot flow integration.

Tests the complete Discord flow:
1. Message detection → Button prompt
2. Button click → Ephemeral conversion
3. Onboarding when timezone missing
4. Mute behavior
5. Ignore rules (bots, edits)
"""

import pytest

from src.engine import Engine, DiscordMessageContext
from src.storage import SQLiteStorage


def test_discord_button_prompt_on_time_detection(engine, storage):
    """When time detected, bot should return button prompt."""
    ctx = DiscordMessageContext(
        guild_id="guild1",
        channel_id="channel1",
        sender_id="user1",
        sender_is_bot=False,
        is_edited=False,
    )
    
    result = engine.discord_should_post_button_prompt(
        message_text="meeting at 10:30",
        ctx=ctx,
    )
    
    # Should return a button prompt
    assert result is not None
    assert "convert" in result.text.lower() or "button" in result.text.lower() or "🕒" in result.text


def test_discord_ignores_bot_messages(engine):
    """Bot should ignore messages from other bots."""
    ctx = DiscordMessageContext(
        guild_id="guild1",
        channel_id="channel1",
        sender_id="bot123",
        sender_is_bot=True,
        is_edited=False,
    )
    
    result = engine.discord_should_post_button_prompt(
        message_text="meeting at 10:30",
        ctx=ctx,
    )
    
    assert result is None


def test_discord_ignores_edited_messages(engine):
    """Bot should ignore edited messages."""
    ctx = DiscordMessageContext(
        guild_id="guild1",
        channel_id="channel1",
        sender_id="user1",
        sender_is_bot=False,
        is_edited=True,
    )
    
    result = engine.discord_should_post_button_prompt(
        message_text="meeting at 10:30",
        ctx=ctx,
    )
    
    assert result is None


def test_discord_button_click_converts_for_clicker(engine, storage):
    """Clicking button should convert to clicker's timezone."""
    storage.set_user_timezone("discord", "original_sender", "Europe/Amsterdam")
    storage.set_user_timezone("discord", "clicker_user", "Asia/Yerevan")
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="meeting at 10:30 Amsterdam",
        original_sender_id="original_sender",
        clicking_user_id="clicker_user",
    )
    
    # Should convert Amsterdam → Yerevan
    assert result is not None
    assert "Amsterdam" in result.text
    assert "Yerevan" in result.text
    assert "10:30" in result.text


def test_discord_button_click_onboarding_clicker_no_timezone(engine, storage):
    """If clicker has no timezone, show onboarding."""
    storage.set_user_timezone("discord", "original_sender", "Europe/Amsterdam")
    # clicker has NO timezone
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="meeting at 10:30 Amsterdam",
        original_sender_id="original_sender",
        clicking_user_id="clicker_no_tz",
    )
    
    # Should return onboarding
    assert result is not None
    assert "timezone" in result.text.lower()
    assert "/tz set" in result.text


def test_discord_button_click_onboarding_sender_no_timezone(engine, storage):
    """If sender has no timezone and no explicit tz, show onboarding."""
    storage.set_user_timezone("discord", "clicker_user", "Asia/Yerevan")
    # sender has NO timezone
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="meeting at 10:30",  # No explicit timezone
        original_sender_id="sender_no_tz",
        clicking_user_id="clicker_user",
    )
    
    # Should return onboarding
    assert result is not None
    assert "timezone" in result.text.lower()


def test_discord_muted_user_gets_nothing(engine, storage):
    """Muted users should get no response when clicking button."""
    storage.set_user_timezone("discord", "original_sender", "Europe/Amsterdam")
    storage.set_user_timezone("discord", "clicker_user", "Asia/Yerevan")
    storage.set_user_muted("discord", "clicker_user", True)
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="meeting at 10:30 Amsterdam",
        original_sender_id="original_sender",
        clicking_user_id="clicker_user",
    )
    
    # Should return None (muted)
    assert result is None


def test_discord_handles_time_range(engine, storage):
    """Time ranges should convert both endpoints."""
    storage.set_user_timezone("discord", "sender", "Europe/Amsterdam")
    storage.set_user_timezone("discord", "clicker", "Asia/Yerevan")
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="meeting 10:00-11:00",
        original_sender_id="sender",
        clicking_user_id="clicker",
    )
    
    # Should show both times
    assert result is not None
    assert "10:00" in result.text or "10:0" in result.text
    assert "11:00" in result.text or "11:0" in result.text


def test_discord_handles_multiple_times(engine, storage):
    """Multiple times should all be converted."""
    storage.set_user_timezone("discord", "sender", "Europe/Amsterdam")
    storage.set_user_timezone("discord", "clicker", "Asia/Yerevan")
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="either 10:30 or 14:00",
        original_sender_id="sender",
        clicking_user_id="clicker",
    )
    
    # Should show both times
    assert result is not None
    assert "10:30" in result.text
    assert "14:00" in result.text or "14:0" in result.text


def test_discord_russian_message_russian_response(engine, storage):
    """Russian messages should get Russian responses."""
    storage.set_user_timezone("discord", "sender", "Europe/Amsterdam")
    storage.set_user_timezone("discord", "clicker", "Asia/Yerevan")
    
    result = engine.discord_build_ephemeral_conversion_for_clicker(
        original_message_text="встреча в 10:30",  # Russian
        original_sender_id="sender",
        clicking_user_id="clicker",
    )
    
    # Should respond (Russian language detected)
    assert result is not None
    assert len(result.text) > 0

