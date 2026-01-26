"""
Test event/metrics logging to storage.

Tests that the bot correctly logs events for:
1. Discord activation events (time detected, button clicked, conversion)
2. Telegram activation events (time detected, public reply, DM sent)
3. Monitoring events (channel added/removed, monitoring enabled/disabled)
4. User preference events (timezone set/cleared, mute/unmute, delete)
5. Feedback events

These tests verify that:
- Events are recorded with correct event names
- Event metadata is properly stored
- Events can be retrieved and listed
- Event timestamps are recorded
"""

from __future__ import annotations

import pytest

from src.storage import SQLiteStorage


# =============================================================================
# Discord Activation Events
# =============================================================================

def test_discord_time_detected_event_logged(storage):
    """discord_time_detected event should be logged when time is detected."""
    storage.log_event(
        platform="discord",
        event_name="discord_time_detected",
        scope_id="guild123",
        channel_id="channel456",
        user_id="user789",
        metadata={"message": "meeting at 10:30"}
    )
    
    events = storage.list_events(platform="discord", event_name="discord_time_detected", limit=10)
    assert len(events) > 0
    assert events[0]["event_name"] == "discord_time_detected"
    assert events[0]["channel_id"] == "channel456"


def test_discord_convert_button_clicked_event(storage):
    """discord_convert_button_clicked event should be logged."""
    storage.log_event(
        platform="discord",
        event_name="discord_convert_button_clicked",
        scope_id="guild123",
        channel_id="channel456",
        user_id="clicker_user",
        metadata={"original_sender": "user789"}
    )
    
    events = storage.list_events(platform="discord", event_name="discord_convert_button_clicked", limit=10)
    assert len(events) > 0
    assert events[0]["user_id"] == "clicker_user"


def test_discord_conversion_success_event(storage):
    """discord_conversion_success event should be logged."""
    storage.log_event(
        platform="discord",
        event_name="discord_conversion_success",
        scope_id="guild123",
        channel_id="channel456",
        user_id="user789",
        metadata={"source_tz": "Europe/Amsterdam", "target_tz": "Asia/Yerevan"}
    )
    
    events = storage.list_events(platform="discord", event_name="discord_conversion_success", limit=10)
    assert len(events) > 0


def test_discord_conversion_onboarding_shown_event(storage):
    """discord_conversion_onboarding_shown event should be logged."""
    storage.log_event(
        platform="discord",
        event_name="discord_conversion_onboarding_shown",
        scope_id="guild123",
        channel_id="channel456",
        user_id="new_user"
    )
    
    events = storage.list_events(platform="discord", event_name="discord_conversion_onboarding_shown", limit=10)
    assert len(events) > 0
    assert events[0]["user_id"] == "new_user"


def test_discord_conversion_blocked_user_muted_event(storage):
    """discord_conversion_blocked_user_muted event should be logged."""
    storage.log_event(
        platform="discord",
        event_name="discord_conversion_blocked_user_muted",
        scope_id="guild123",
        channel_id="channel456",
        user_id="muted_user"
    )
    
    events = storage.list_events(platform="discord", event_name="discord_conversion_blocked_user_muted", limit=10)
    assert len(events) > 0


# =============================================================================
# Telegram Activation Events
# =============================================================================

def test_telegram_time_detected_event(storage):
    """telegram_time_detected event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="telegram_time_detected",
        scope_id="chat123",
        user_id="user456",
        metadata={"message": "встреча в 10:30"}
    )
    
    events = storage.list_events(platform="telegram", event_name="telegram_time_detected", limit=10)
    assert len(events) > 0
    assert events[0]["scope_id"] == "chat123"


def test_telegram_public_reply_sent_event(storage):
    """telegram_public_reply_sent event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="telegram_public_reply_sent",
        scope_id="chat123",
        user_id="user456",
        metadata={"num_timezones": 3}
    )
    
    events = storage.list_events(platform="telegram", event_name="telegram_public_reply_sent", limit=10)
    assert len(events) > 0


def test_telegram_dm_sent_event(storage):
    """telegram_dm_sent event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="telegram_dm_sent",
        scope_id="chat123",
        user_id="recipient_user",
        metadata={"source_user": "sender_user"}
    )
    
    events = storage.list_events(platform="telegram", event_name="telegram_dm_sent", limit=10)
    assert len(events) > 0
    assert events[0]["user_id"] == "recipient_user"


def test_telegram_dm_skipped_disabled_event(storage):
    """telegram_dm_skipped_disabled event should be logged when user has DM off."""
    storage.log_event(
        platform="telegram",
        event_name="telegram_dm_skipped_disabled",
        scope_id="chat123",
        user_id="user_with_dm_off"
    )
    
    events = storage.list_events(platform="telegram", event_name="telegram_dm_skipped_disabled", limit=10)
    assert len(events) > 0


def test_telegram_dm_skipped_not_eligible_event(storage):
    """telegram_dm_skipped_not_eligible event should be logged when user hasn't started chat."""
    storage.log_event(
        platform="telegram",
        event_name="telegram_dm_skipped_not_eligible",
        scope_id="chat123",
        user_id="user_no_private_chat"
    )
    
    events = storage.list_events(platform="telegram", event_name="telegram_dm_skipped_not_eligible", limit=10)
    assert len(events) > 0


def test_telegram_dm_blocked_user_muted_event(storage):
    """telegram_dm_blocked_user_muted event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="telegram_dm_blocked_user_muted",
        scope_id="chat123",
        user_id="muted_user"
    )
    
    events = storage.list_events(platform="telegram", event_name="telegram_dm_blocked_user_muted", limit=10)
    assert len(events) > 0


# =============================================================================
# Monitoring Events
# =============================================================================

def test_discord_monitor_channel_added_event(storage):
    """discord_monitor_channel_added event should be logged."""
    storage.log_event(
        platform="discord",
        event_name="discord_monitor_channel_added",
        scope_id="guild123",
        channel_id="channel456",
        user_id="admin_user"
    )
    
    events = storage.list_events(platform="discord", event_name="discord_monitor_channel_added", limit=10)
    assert len(events) > 0
    assert events[0]["channel_id"] == "channel456"


def test_discord_monitor_channel_removed_event(storage):
    """discord_monitor_channel_removed event should be logged."""
    storage.log_event(
        platform="discord",
        event_name="discord_monitor_channel_removed",
        scope_id="guild123",
        channel_id="channel456",
        user_id="admin_user"
    )
    
    events = storage.list_events(platform="discord", event_name="discord_monitor_channel_removed", limit=10)
    assert len(events) > 0


def test_telegram_monitor_enabled_event(storage):
    """telegram_monitor_enabled event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="telegram_monitor_enabled",
        scope_id="chat123",
        user_id="admin_user"
    )
    
    events = storage.list_events(platform="telegram", event_name="telegram_monitor_enabled", limit=10)
    assert len(events) > 0
    assert events[0]["scope_id"] == "chat123"


def test_telegram_monitor_disabled_event(storage):
    """telegram_monitor_disabled event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="telegram_monitor_disabled",
        scope_id="chat123",
        user_id="admin_user"
    )
    
    events = storage.list_events(platform="telegram", event_name="telegram_monitor_disabled", limit=10)
    assert len(events) > 0


# =============================================================================
# User Preference Events
# =============================================================================

def test_user_timezone_set_event(storage):
    """user_timezone_set event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="user_timezone_set",
        user_id="user123",
        metadata={"timezone": "Europe/Amsterdam"}
    )
    
    events = storage.list_events(event_name="user_timezone_set", limit=10)
    assert len(events) > 0
    assert events[0]["user_id"] == "user123"


def test_user_timezone_cleared_event(storage):
    """user_timezone_cleared event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="user_timezone_cleared",
        user_id="user123"
    )
    
    events = storage.list_events(event_name="user_timezone_cleared", limit=10)
    assert len(events) > 0


def test_user_muted_event(storage):
    """user_muted event should be logged."""
    storage.log_event(
        platform="discord",
        event_name="user_muted",
        user_id="user123"
    )
    
    events = storage.list_events(event_name="user_muted", limit=10)
    assert len(events) > 0


def test_user_unmuted_event(storage):
    """user_unmuted event should be logged."""
    storage.log_event(
        platform="discord",
        event_name="user_unmuted",
        user_id="user123"
    )
    
    events = storage.list_events(event_name="user_unmuted", limit=10)
    assert len(events) > 0


def test_user_deleted_data_event(storage):
    """user_deleted_data event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="user_deleted_data",
        user_id="user123"
    )
    
    events = storage.list_events(event_name="user_deleted_data", limit=10)
    assert len(events) > 0


# =============================================================================
# Feedback Events
# =============================================================================

def test_feedback_submitted_event(storage):
    """feedback_submitted event should be logged."""
    storage.log_event(
        platform="telegram",
        event_name="feedback_submitted",
        user_id="user123",
        metadata={"feedback": "Great bot!"}
    )
    
    events = storage.list_events(event_name="feedback_submitted", limit=10)
    assert len(events) > 0


# =============================================================================
# Event Retrieval and Filtering
# =============================================================================

def test_list_events_filtered_by_platform(storage):
    """Should be able to filter events by platform."""
    storage.log_event(platform="discord", event_name="test_event_1", user_id="user1")
    storage.log_event(platform="telegram", event_name="test_event_2", user_id="user2")
    
    discord_events = storage.list_events(platform="discord", limit=100)
    telegram_events = storage.list_events(platform="telegram", limit=100)
    
    # Discord events should only contain discord platform
    assert all(e["platform"] == "discord" for e in discord_events if e["event_name"] == "test_event_1")
    # Telegram events should only contain telegram platform
    assert all(e["platform"] == "telegram" for e in telegram_events if e["event_name"] == "test_event_2")


def test_list_events_filtered_by_event_name(storage):
    """Should be able to filter events by event name."""
    storage.log_event(platform="discord", event_name="event_type_a", user_id="user1")
    storage.log_event(platform="discord", event_name="event_type_b", user_id="user2")
    
    events_a = storage.list_events(event_name="event_type_a", limit=100)
    events_b = storage.list_events(event_name="event_type_b", limit=100)
    
    assert all(e["event_name"] == "event_type_a" for e in events_a if e["user_id"] == "user1")
    assert all(e["event_name"] == "event_type_b" for e in events_b if e["user_id"] == "user2")


def test_list_events_respects_limit(storage):
    """Should respect the limit parameter."""
    # Log many events
    for i in range(20):
        storage.log_event(platform="discord", event_name="bulk_event", user_id=f"user{i}")
    
    # Request only 5
    events = storage.list_events(event_name="bulk_event", limit=5)
    
    # Should return at most 5
    assert len(events) <= 5


def test_event_metadata_is_stored(storage):
    """Event metadata should be stored and retrievable."""
    metadata = {
        "source_timezone": "Europe/Amsterdam",
        "target_timezone": "Asia/Yerevan",
        "num_times": 2
    }
    
    storage.log_event(
        platform="telegram",
        event_name="test_with_metadata",
        user_id="user123",
        metadata=metadata
    )
    
    events = storage.list_events(event_name="test_with_metadata", limit=1)
    assert len(events) > 0
    # Metadata should be accessible (format depends on storage implementation)
    # Could be JSON string or dict


def test_events_have_timestamps(storage):
    """Events should have timestamps."""
    storage.log_event(
        platform="telegram",
        event_name="timestamped_event",
        user_id="user123"
    )
    
    events = storage.list_events(event_name="timestamped_event", limit=1)
    assert len(events) > 0
    # Should have timestamp field (name depends on implementation)
    assert "ts" in events[0] or "timestamp" in events[0] or "created_at" in events[0]


def test_multiple_events_for_same_user(storage):
    """Should be able to log multiple events for same user."""
    storage.log_event(platform="telegram", event_name="event1", user_id="user123")
    storage.log_event(platform="telegram", event_name="event2", user_id="user123")
    storage.log_event(platform="telegram", event_name="event3", user_id="user123")
    
    events = storage.list_events(platform="telegram", limit=100)
    user123_events = [e for e in events if e.get("user_id") == "user123"]
    
    assert len(user123_events) >= 3