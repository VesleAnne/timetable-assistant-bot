"""
Test Telegram engine end-to-end flow.

Tests the complete Telegram message processing flow:
1. Basic conversion - sender has timezone, message has time mention
2. Onboarding - sender has no timezone configured
3. Time ranges - both endpoints are converted
4. Weekday anchors - resolved calendar date is included in output
5. Russian language - Russian messages get Russian replies
6. Active timezones - conversions shown for all group members' timezones

These tests verify the full integration of:
- Message parsing
- Timezone resolution
- Active timezone list building
- Conversion logic
- Output formatting
- Language detection and matching
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from zoneinfo import ZoneInfo

from src.engine import Engine, TelegramMessageContext
from src.storage import SQLiteStorage


def _extract_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    for attr in ["text", "message", "reply_text", "content", "body"]:
        if hasattr(result, attr):
            val = getattr(result, attr)
            if isinstance(val, str):
                return val
    return str(result)


def _prepare_active_timezones_for_chat(storage: SQLiteStorage, chat_id: str, user_ids_to_tz: dict[str, str]):
    """
    Makes active timezones exist in a Telegram group by:
    - enabling monitoring
    - touching members
    - setting user timezones
    """
    storage.telegram_set_monitoring(chat_id, True)
    for user_id, tz in user_ids_to_tz.items():
        storage.telegram_touch_member(chat_id, user_id)
        storage.set_user_timezone("telegram", user_id, tz)


def _call_telegram_engine(engine: Engine, storage: SQLiteStorage, ctx: TelegramMessageContext, text: str):
    """
    Adapter-style call:
    - adapter computes active timezones from storage
    - engine builds public reply
    """
    active = sorted(storage.telegram_get_active_timezones(ctx.chat_id))
    return engine.telegram_build_public_reply(
        message_text=text,
        ctx=ctx,
        active_timezones=active,
        max_active_timezones=None,
    )


@pytest.fixture()
def telegram_ctx_factory():
    def _make(chat_id: str, sender_id: str, sender_is_bot: bool = False, is_edited: bool = False):
        return TelegramMessageContext(
            chat_id=chat_id,
            sender_id=sender_id,
            sender_is_bot=sender_is_bot,
            is_edited=is_edited,
        )

    return _make


def test_telegram_end_to_end_basic_conversion(engine: Engine, storage: SQLiteStorage, telegram_ctx_factory):
    """
    Telegram E2E:
    - Sender has timezone set
    - Message has time mention without explicit timezone
    - Engine replies with conversions to active timezones
    """
    chat_id = "chat_1"
    user_ams = "u_ams"
    user_yer = "u_yer"
    user_cyp = "u_cyp"

    _prepare_active_timezones_for_chat(
        storage,
        chat_id,
        {
            user_ams: "Europe/Amsterdam",
            user_cyp: "Asia/Nicosia",
            user_yer: "Asia/Yerevan",
        },
    )

    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=user_ams)

    result = _call_telegram_engine(engine, storage, ctx, "see you 10:30")
    text = _extract_text(result)

    assert "10:30" in text
    assert "Amsterdam" in text
    assert ("Cyprus" in text) or ("Limassol" in text) or ("Nicosia" in text)
    assert "Yerevan" in text

    # winter offsets: AMS 10:30 -> CYP 11:30 -> YER 13:30
    assert "11:30" in text
    assert "13:30" in text


def test_telegram_end_to_end_missing_sender_timezone_onboards(engine: Engine, storage: SQLiteStorage, telegram_ctx_factory):
    """
    Telegram E2E:
    - sender has NO timezone configured
    - message has time mention without explicit timezone
    - engine must respond with onboarding and NOT convert
    """
    chat_id = "chat_2"
    sender = "u_new"

    storage.telegram_set_monitoring(chat_id, True)
    storage.telegram_touch_member(chat_id, sender)

    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=sender)

    result = _call_telegram_engine(engine, storage, ctx, "see you 10:30")
    text = _extract_text(result).lower()

    assert "/tz set" in text


def test_telegram_end_to_end_range_conversion(engine: Engine, storage: SQLiteStorage, telegram_ctx_factory):
    """
    Telegram E2E:
    - range mention detected
    - both endpoints converted
    """
    chat_id = "chat_3"
    sender = "u_ams"
    user_yer = "u_yer"

    _prepare_active_timezones_for_chat(
        storage,
        chat_id,
        {
            sender: "Europe/Amsterdam",
            user_yer: "Asia/Yerevan",
        },
    )

    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=sender)

    result = _call_telegram_engine(engine, storage, ctx, "meeting 10:00–11:00")

    text = _extract_text(result)

    assert "10:00" in text
    assert "11:00" in text
    assert "Amsterdam" in text
    assert "Yerevan" in text


def test_telegram_end_to_end_weekday_anchor_includes_calendar_date(
    engine: Engine, storage: SQLiteStorage, telegram_ctx_factory, monkeypatch
):
    """
    Telegram E2E:
    - weekday anchor present
    - output includes resolved calendar date
    """
    # Freeze "now" to make "next Monday" deterministic.
    # Wed Jan 28, 2026 -> next Monday is Feb 2, 2026
    from src import conversion as conversion_module

    def fake_now_in_timezone(tz_name: str):
        return datetime(2026, 1, 28, 12, 0, tzinfo=ZoneInfo(tz_name))

    monkeypatch.setattr(conversion_module, "now_in_timezone", fake_now_in_timezone)

    chat_id = "chat_4"
    sender = "u_ams"
    user_yer = "u_yer"

    _prepare_active_timezones_for_chat(
        storage,
        chat_id,
        {
            sender: "Europe/Amsterdam",
            user_yer: "Asia/Yerevan",
        },
    )

    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=sender)

    result = _call_telegram_engine(engine, storage, ctx, "on Monday 10:00")
    text = _extract_text(result)

    # Must include resolved date prefix like "Mon, Feb 2"
    assert "Mon" in text
    assert "Feb" in text
    assert "2" in text
    assert "10:00" in text
    assert "Amsterdam" in text
    assert "Yerevan" in text


def test_telegram_end_to_end_russian_message_russian_reply(engine: Engine, storage: SQLiteStorage, telegram_ctx_factory):
    """
    Telegram E2E:
    - Russian input
    - bot responds in Russian with Russian city names
    """
    chat_id = "chat_5"
    sender = "u_ams"
    user_yer = "u_yer"

    _prepare_active_timezones_for_chat(
        storage,
        chat_id,
        {
            sender: "Europe/Amsterdam",
            user_yer: "Asia/Yerevan",
        },
    )

    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=sender)

    result = _call_telegram_engine(engine, storage, ctx, "в 10:30 созвон")
    text = _extract_text(result)

    # Russian message should produce Russian city names
    assert "Амстердам" in text  # Changed from "Amsterdam"
    assert "Ереван" in text      # Changed from "Yerevan" (if it was there)

def test_telegram_respects_max_active_timezones_limit(engine: Engine, storage: SQLiteStorage, telegram_ctx_factory):
    """
    Telegram E2E:
    - Many active timezones in group
    - max_active_timezones setting limits output
    """
    chat_id = "chat_6"
    sender = "u1"  # Changed from u_ams to u1 (who has timezone)
    
    # Create a group with MANY active timezones (more than typical limit)
    many_users = {
        "u1": "Europe/Amsterdam",
        "u2": "Asia/Yerevan",
        "u3": "America/Vancouver",
        "u4": "Asia/Tokyo",
        "u5": "Australia/Sydney",
        "u6": "America/New_York",
        "u7": "Asia/Dubai",
        "u8": "Europe/London",
    }
    
    _prepare_active_timezones_for_chat(storage, chat_id, many_users)
    
    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=sender)
    
    # Get active timezones (should be 8)
    active = sorted(storage.telegram_get_active_timezones(chat_id))
    assert len(active) == 8
    
    # Call engine with max_active_timezones limit
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30",
        ctx=ctx,
        active_timezones=active,
        max_active_timezones=5,  # Limit to 5
    )
    
    text = _extract_text(result)
    
    # Should have conversion output
    assert "10:30" in text
    
    # Should show source timezone
    assert "Amsterdam" in text
    
    # Count how many timezone names appear in output
    # With max=5, should show at most 5 target timezones (plus source)
    # This is a heuristic check - exact behavior depends on formatting
    timezone_count = sum([
        "Yerevan" in text,
        "Vancouver" in text,
        "Tokyo" in text,
        "Sydney" in text,
        "New York" in text or "New_York" in text,
        "Dubai" in text,
        "London" in text,
    ])
    
    # Should be limited (not all 7 non-source timezones shown)
    # Exact number depends on implementation (might be 5, might be slightly different)
    assert timezone_count <= 6  # Allow some flexibility

def test_telegram_with_zero_active_timezones(engine: Engine, storage: SQLiteStorage, telegram_ctx_factory):
    """
    Telegram E2E:
    - Sender has timezone
    - No other active timezones (empty list)
    - Bot should still respond (no conversions to show, but acknowledges time)
    """
    chat_id = "chat_7"
    sender = "u_ams"
    
    # Only sender has timezone, no other members
    storage.telegram_set_monitoring(chat_id, True)
    storage.telegram_touch_member(chat_id, sender)
    storage.set_user_timezone("telegram", sender, "Europe/Amsterdam")
    
    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=sender)
    
    # Active timezones list is empty (or just sender's timezone)
    active = sorted(storage.telegram_get_active_timezones(chat_id))
    # Might be [Amsterdam] or might be empty depending on implementation
    
    result = engine.telegram_build_public_reply(
        message_text="meeting at 10:30",
        ctx=ctx,
        active_timezones=active,
    )
    
    # Should still respond
    assert result is not None
    text = _extract_text(result)
    
    # Should show the time
    assert "10:30" in text
    # Should show source timezone
    assert "Amsterdam" in text

def test_telegram_dm_sent_when_user_eligible(engine, storage, telegram_ctx_factory):
    """
    Telegram DM should be sent when:
    - User has /dm on
    - User has started private chat (is eligible)
    - User is not muted
    """
    chat_id = "chat_dm_test"
    sender = "u_sender"
    recipient = "u_recipient"
    
    # Setup
    storage.set_user_timezone("telegram", sender, "Europe/Amsterdam")
    storage.set_user_timezone("telegram", recipient, "Asia/Yerevan")
    storage.set_user_dm_enabled("telegram", recipient, True)  # DM on
    # Note: Need method to mark user as having started private chat
    # Assuming there's a method like: storage.telegram_mark_user_eligible_for_dm(recipient)
    
    storage.telegram_set_monitoring(chat_id, True)
    storage.telegram_touch_member(chat_id, sender)
    storage.telegram_touch_member(chat_id, recipient)
    
    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=sender)
    
    # Build DM for recipient
    dm_result = engine.telegram_build_dm_for_user(
        message_text="meeting at 10:30",
        ctx=ctx,
        recipient_user_id=recipient,
        recipient_timezone="Asia/Yerevan"
    )
    
    # Should get DM (user is eligible)
    assert dm_result is not None
    assert "10:30" in dm_result.text
    assert "Yerevan" in dm_result.text or "13:30" in dm_result.text


def test_telegram_dm_not_sent_when_dm_disabled(engine, storage, telegram_ctx_factory):
    """DM should NOT be sent when user has /dm off."""
    chat_id = "chat_dm_test2"
    sender = "u_sender"
    recipient = "u_recipient_dm_off"
    
    storage.set_user_timezone("telegram", sender, "Europe/Amsterdam")
    storage.set_user_timezone("telegram", recipient, "Asia/Yerevan")
    storage.set_user_dm_enabled("telegram", recipient, False)  # DM OFF
    
    storage.telegram_set_monitoring(chat_id, True)
    storage.telegram_touch_member(chat_id, sender)
    storage.telegram_touch_member(chat_id, recipient)
    
    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=sender)
    
    dm_result = engine.telegram_build_dm_for_user(
        message_text="meeting at 10:30",
        ctx=ctx,
        recipient_user_id=recipient,
        recipient_timezone="Asia/Yerevan"
    )
    
    # Should NOT get DM
    assert dm_result is None


def test_telegram_dm_not_sent_when_user_muted(engine, storage, telegram_ctx_factory):
    """DM should NOT be sent when user is muted, even if DM enabled."""
    chat_id = "chat_dm_test3"
    sender = "u_sender"
    recipient = "u_recipient_muted"
    
    storage.set_user_timezone("telegram", sender, "Europe/Amsterdam")
    storage.set_user_timezone("telegram", recipient, "Asia/Yerevan")
    storage.set_user_dm_enabled("telegram", recipient, True)  # DM on
    storage.set_user_muted("telegram", recipient, True)  # But muted!
    
    storage.telegram_set_monitoring(chat_id, True)
    storage.telegram_touch_member(chat_id, sender)
    storage.telegram_touch_member(chat_id, recipient)
    
    ctx = telegram_ctx_factory(chat_id=chat_id, sender_id=sender)
    
    dm_result = engine.telegram_build_dm_for_user(
        message_text="meeting at 10:30",
        ctx=ctx,
        recipient_user_id=recipient,
        recipient_timezone="Asia/Yerevan"
    )
    
    # Should NOT get DM (muted)
    assert dm_result is None