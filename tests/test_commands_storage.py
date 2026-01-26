"""
Test user and admin commands with storage persistence.

Tests command execution and storage operations:
1. User timezone commands: /tz set, /tz show, /tz clear
2. Telegram DM commands: /dm on, /dm off, /dm status
3. Mute commands: /mute, /unmute
4. Data deletion: /delete_me
5. Feedback: /feedback
6. Discord monitoring: /monitor add, /monitor remove, /monitor list
7. Telegram monitoring: /monitor_on, /monitor_off, /monitor_status
8. Admin timezone overrides (Telegram)

These tests verify that:
- Commands properly update storage
- Storage changes persist
- Invalid inputs are handled gracefully
- Cross-platform isolation works (Discord vs Telegram)
"""

from __future__ import annotations

import pytest

from src.storage import SQLiteStorage


# =============================================================================
# User Timezone Commands (/tz set, /tz show, /tz clear)
# =============================================================================

def test_tz_set_stores_timezone(storage):
    """Setting timezone should persist in storage."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    
    retrieved = storage.get_user_timezone("telegram", "user123")
    assert retrieved == "Europe/Amsterdam"


def test_tz_set_updates_existing_timezone(storage):
    """Setting timezone again should update existing value."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    storage.set_user_timezone("telegram", "user123", "Asia/Yerevan")
    
    retrieved = storage.get_user_timezone("telegram", "user123")
    assert retrieved == "Asia/Yerevan"


def test_tz_clear_removes_timezone(storage):
    """Clearing timezone should remove it from storage."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    storage.clear_user_timezone("telegram", "user123")
    
    retrieved = storage.get_user_timezone("telegram", "user123")
    assert retrieved is None


def test_tz_show_returns_none_when_not_set(storage):
    """Showing timezone when not set should return None."""
    retrieved = storage.get_user_timezone("telegram", "user456")
    assert retrieved is None


def test_tz_platform_isolation(storage):
    """Timezones are isolated per platform."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    storage.set_user_timezone("discord", "user123", "Asia/Yerevan")
    
    telegram_tz = storage.get_user_timezone("telegram", "user123")
    discord_tz = storage.get_user_timezone("discord", "user123")
    
    assert telegram_tz == "Europe/Amsterdam"
    assert discord_tz == "Asia/Yerevan"


# =============================================================================
# Telegram DM Commands (/dm on, /dm off, /dm status)
# =============================================================================

def test_dm_on_enables_dm_delivery(storage):
    """Enabling DM should set dm_enabled to True."""
    storage.set_user_dm_enabled("telegram", "user123", True)
    
    enabled = storage.get_user_dm_enabled("telegram", "user123")
    assert enabled is True


def test_dm_off_disables_dm_delivery(storage):
    """Disabling DM should set dm_enabled to False."""
    storage.set_user_dm_enabled("telegram", "user123", True)
    storage.set_user_dm_enabled("telegram", "user123", False)
    
    enabled = storage.get_user_dm_enabled("telegram", "user123")
    assert enabled is False


def test_dm_status_default_is_false(storage):
    """DM delivery should be disabled by default."""
    enabled = storage.get_user_dm_enabled("telegram", "user456")
    assert enabled is False


def test_dm_setting_persists(storage):
    """DM setting should persist across queries."""
    storage.set_user_dm_enabled("telegram", "user123", True)
    
    # Query multiple times
    assert storage.get_user_dm_enabled("telegram", "user123") is True
    assert storage.get_user_dm_enabled("telegram", "user123") is True


def test_dm_only_applies_to_telegram(storage):
    """DM settings only exist for Telegram platform."""
    storage.set_user_dm_enabled("telegram", "user123", True)
    
    # Discord doesn't have DM settings (should use default False)
    discord_dm = storage.get_user_dm_enabled("discord", "user123")
    assert discord_dm is False


# =============================================================================
# Mute Commands (/mute, /unmute)
# =============================================================================

def test_mute_sets_user_muted(storage):
    """Muting user should set muted flag to True."""
    storage.set_user_muted("telegram", "user123", True)
    
    is_muted = storage.get_user_muted("telegram", "user123")
    assert is_muted is True


def test_unmute_clears_user_muted(storage):
    """Unmuting user should set muted flag to False."""
    storage.set_user_muted("telegram", "user123", True)
    storage.set_user_muted("telegram", "user123", False)
    
    is_muted = storage.get_user_muted("telegram", "user123")
    assert is_muted is False


def test_muted_default_is_false(storage):
    """Users should not be muted by default."""
    is_muted = storage.get_user_muted("telegram", "user456")
    assert is_muted is False


def test_mute_platform_isolation(storage):
    """Mute status is isolated per platform."""
    storage.set_user_muted("telegram", "user123", True)
    storage.set_user_muted("discord", "user123", False)
    
    telegram_muted = storage.get_user_muted("telegram", "user123")
    discord_muted = storage.get_user_muted("discord", "user123")
    
    assert telegram_muted is True
    assert discord_muted is False


# =============================================================================
# Data Deletion (/delete_me)
# =============================================================================

def test_delete_me_removes_timezone(storage):
    """Deleting user data should remove timezone."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    storage.delete_user_data("telegram", "user123")
    
    retrieved = storage.get_user_timezone("telegram", "user123")
    assert retrieved is None


def test_delete_me_removes_dm_setting(storage):
    """Deleting user data should remove DM setting."""
    storage.set_user_dm_enabled("telegram", "user123", True)
    storage.delete_user_data("telegram", "user123")
    
    dm_enabled = storage.get_user_dm_enabled("telegram", "user123")
    assert dm_enabled is False  # Reverts to default


def test_delete_me_removes_mute_status(storage):
    """Deleting user data should remove mute status."""
    storage.set_user_muted("telegram", "user123", True)
    storage.delete_user_data("telegram", "user123")
    
    is_muted = storage.get_user_muted("telegram", "user123")
    assert is_muted is False  # Reverts to default


def test_delete_me_removes_all_user_data(storage):
    """Deleting user data should remove all settings at once."""
    # Set multiple preferences
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    storage.set_user_dm_enabled("telegram", "user123", True)
    storage.set_user_muted("telegram", "user123", True)
    
    # Delete all
    storage.delete_user_data("telegram", "user123")
    
    # Verify all removed
    assert storage.get_user_timezone("telegram", "user123") is None
    assert storage.get_user_dm_enabled("telegram", "user123") is False
    assert storage.get_user_muted("telegram", "user123") is False


def test_delete_me_platform_isolation(storage):
    """Deleting user data only affects specified platform."""
    storage.set_user_timezone("telegram", "user123", "Europe/Amsterdam")
    storage.set_user_timezone("discord", "user123", "Asia/Yerevan")
    
    # Delete only Telegram data
    storage.delete_user_data("telegram", "user123")
    
    # Telegram data deleted
    assert storage.get_user_timezone("telegram", "user123") is None
    # Discord data remains
    assert storage.get_user_timezone("discord", "user123") == "Asia/Yerevan"


# =============================================================================
# Feedback (/feedback)
# =============================================================================

def test_feedback_stores_submission(storage):
    """Submitting feedback should store it in database."""
    storage.save_feedback("telegram", "user123", "Great bot!")
    
    # Feedback should be retrievable
    feedback_list = storage.list_feedback(platform="telegram")
    assert len(feedback_list) > 0
    # Check that the feedback text appears in the list
    assert any("Great bot!" in str(fb) for fb in feedback_list)


def test_feedback_stores_multiple_submissions(storage):
    """Multiple feedback submissions should all be stored."""
    storage.save_feedback("telegram", "user123", "First feedback")
    storage.save_feedback("telegram", "user123", "Second feedback")
    storage.save_feedback("telegram", "user456", "Different user")
    
    # All should be stored
    feedback_list = storage.list_feedback(platform="telegram")
    assert len(feedback_list) >= 3


# =============================================================================
# Discord Monitoring Commands (/monitor add, /monitor remove, /monitor list)
# =============================================================================

def test_discord_monitor_add_channel(storage):
    """Adding monitored channel should store it."""
    storage.discord_add_monitored_channel("guild1", "channel1")
    
    channels = storage.discord_list_monitored_channels("guild1")
    assert "channel1" in channels


def test_discord_monitor_add_multiple_channels(storage):
    """Adding multiple channels should store all."""
    storage.discord_add_monitored_channel("guild1", "channel1")
    storage.discord_add_monitored_channel("guild1", "channel2")
    storage.discord_add_monitored_channel("guild1", "channel3")
    
    channels = storage.discord_list_monitored_channels("guild1")
    assert len(channels) == 3
    assert "channel1" in channels
    assert "channel2" in channels
    assert "channel3" in channels


def test_discord_monitor_remove_channel(storage):
    """Removing monitored channel should delete it."""
    storage.discord_add_monitored_channel("guild1", "channel1")
    storage.discord_add_monitored_channel("guild1", "channel2")
    
    storage.discord_remove_monitored_channel("guild1", "channel1")
    
    channels = storage.discord_list_monitored_channels("guild1")
    assert "channel1" not in channels
    assert "channel2" in channels


def test_discord_monitor_list_empty_when_none_added(storage):
    """Listing channels when none added should return empty list."""
    channels = storage.discord_list_monitored_channels("guild1")
    assert len(channels) == 0


def test_discord_monitor_guild_isolation(storage):
    """Monitored channels are isolated per guild."""
    storage.discord_add_monitored_channel("guild1", "channel1")
    storage.discord_add_monitored_channel("guild2", "channel2")
    
    guild1_channels = storage.discord_list_monitored_channels("guild1")
    guild2_channels = storage.discord_list_monitored_channels("guild2")
    
    assert "channel1" in guild1_channels
    assert "channel1" not in guild2_channels
    assert "channel2" in guild2_channels
    assert "channel2" not in guild1_channels


def test_discord_monitor_add_duplicate_is_idempotent(storage):
    """Adding same channel twice should not duplicate."""
    storage.discord_add_monitored_channel("guild1", "channel1")
    storage.discord_add_monitored_channel("guild1", "channel1")
    
    channels = storage.discord_list_monitored_channels("guild1")
    # Should appear only once
    assert channels.count("channel1") == 1


def test_discord_is_monitored_channel_check(storage):
    """Should be able to check if channel is monitored."""
    storage.discord_add_monitored_channel("guild1", "channel1")
    
    assert storage.discord_is_monitored_channel("guild1", "channel1") is True
    assert storage.discord_is_monitored_channel("guild1", "channel2") is False
    assert storage.discord_is_monitored_channel("guild2", "channel1") is False


# =============================================================================
# Telegram Monitoring Commands (/monitor_on, /monitor_off, /monitor_status)
# =============================================================================

def test_telegram_monitor_on_enables_monitoring(storage):
    """Enabling monitoring should set flag to True."""
    storage.telegram_set_monitoring("chat1", True)
    
    is_enabled = storage.telegram_get_monitoring("chat1")
    assert is_enabled is True


def test_telegram_monitor_off_disables_monitoring(storage):
    """Disabling monitoring should set flag to False."""
    storage.telegram_set_monitoring("chat1", True)
    storage.telegram_set_monitoring("chat1", False)
    
    is_enabled = storage.telegram_get_monitoring("chat1")
    assert is_enabled is False


def test_telegram_monitor_status_default_is_false(storage):
    """Monitoring should be disabled by default."""
    is_enabled = storage.telegram_get_monitoring("chat_new")
    assert is_enabled is False


def test_telegram_monitor_chat_isolation(storage):
    """Monitoring status is isolated per chat."""
    storage.telegram_set_monitoring("chat1", True)
    storage.telegram_set_monitoring("chat2", False)
    
    chat1_enabled = storage.telegram_get_monitoring("chat1")
    chat2_enabled = storage.telegram_get_monitoring("chat2")
    
    assert chat1_enabled is True
    assert chat2_enabled is False


# =============================================================================
# Telegram Admin Timezone Overrides
# =============================================================================

def test_telegram_admin_can_add_timezone_override(storage):
    """Admin can manually add timezone to active list."""
    storage.telegram_set_monitoring("chat1", True)
    
    # Add admin override for a timezone
    storage.telegram_set_timezone_override("chat1", "Asia/Tokyo", "add")
    
    active = storage.telegram_get_active_timezones("chat1")
    assert "Asia/Tokyo" in active


def test_telegram_admin_can_remove_timezone_override(storage):
    """Admin can manually remove timezone from active list."""
    storage.telegram_set_monitoring("chat1", True)
    
    # User has timezone
    storage.set_user_timezone("telegram", "user1", "Europe/Amsterdam")
    storage.telegram_touch_member("chat1", "user1")
    
    # Admin removes it
    storage.telegram_set_timezone_override("chat1", "Europe/Amsterdam", "remove")
    
    active = storage.telegram_get_active_timezones("chat1")
    # Should not appear even though user has it
    assert "Europe/Amsterdam" not in active


def test_telegram_admin_add_override_persists_after_user_leaves(storage):
    """Admin-added timezone should persist even if no users have it."""
    storage.telegram_set_monitoring("chat1", True)
    
    # Admin adds timezone manually
    storage.telegram_set_timezone_override("chat1", "Asia/Tokyo", "add")
    
    # No users have this timezone
    active = storage.telegram_get_active_timezones("chat1")
    assert "Asia/Tokyo" in active


def test_telegram_remove_override_takes_precedence(storage):
    """Admin removal override should hide timezone even if users have it."""
    storage.telegram_set_monitoring("chat1", True)
    
    # Multiple users have Amsterdam
    storage.set_user_timezone("telegram", "user1", "Europe/Amsterdam")
    storage.set_user_timezone("telegram", "user2", "Europe/Amsterdam")
    storage.telegram_touch_member("chat1", "user1")
    storage.telegram_touch_member("chat1", "user2")
    
    # Admin removes it
    storage.telegram_set_timezone_override("chat1", "Europe/Amsterdam", "remove")
    
    active = storage.telegram_get_active_timezones("chat1")
    # Should not appear despite 2 users having it
    assert "Europe/Amsterdam" not in active


def test_telegram_clear_timezone_override(storage):
    """Clearing override should restore normal behavior."""
    storage.telegram_set_monitoring("chat1", True)
    
    # Add override
    storage.telegram_set_timezone_override("chat1", "Asia/Tokyo", "add")
    assert "Asia/Tokyo" in storage.telegram_get_active_timezones("chat1")
    
    # Clear override
    storage.telegram_clear_timezone_override("chat1", "Asia/Tokyo")
    
    # Should no longer appear (no users have it)
    assert "Asia/Tokyo" not in storage.telegram_get_active_timezones("chat1")


def test_telegram_list_timezone_overrides(storage):
    """Should be able to list all overrides for a chat."""
    storage.telegram_set_monitoring("chat1", True)
    
    storage.telegram_set_timezone_override("chat1", "Asia/Tokyo", "add")
    storage.telegram_set_timezone_override("chat1", "Europe/London", "remove")
    
    overrides = storage.telegram_list_timezone_overrides("chat1")
    
    assert "Asia/Tokyo" in overrides
    assert overrides["Asia/Tokyo"] == "add"
    assert "Europe/London" in overrides
    assert overrides["Europe/London"] == "remove"


# =============================================================================
# Edge Cases & Error Handling
# =============================================================================

def test_set_invalid_timezone_format(storage):
    """Setting invalid timezone should either raise error or be stored as-is."""
    # Depending on implementation, this might:
    # 1. Raise an error (strict validation)
    # 2. Store the value anyway (validation happens at use time)
    
    # For now, test that it doesn't crash
    storage.set_user_timezone("telegram", "user123", "InvalidTimezone")
    
    # Retrieve it
    retrieved = storage.get_user_timezone("telegram", "user123")
    # Should either be None (rejected) or "InvalidTimezone" (stored)
    assert retrieved in [None, "InvalidTimezone"]


def test_multiple_operations_on_same_user(storage):
    """Multiple operations on same user should work correctly."""
    user_id = "user_complex"
    
    # Set timezone
    storage.set_user_timezone("telegram", user_id, "Europe/Amsterdam")
    assert storage.get_user_timezone("telegram", user_id) == "Europe/Amsterdam"
    
    # Enable DM
    storage.set_user_dm_enabled("telegram", user_id, True)
    assert storage.get_user_dm_enabled("telegram", user_id) is True
    
    # Mute user
    storage.set_user_muted("telegram", user_id, True)
    assert storage.get_user_muted("telegram", user_id) is True
    
    # All should coexist
    assert storage.get_user_timezone("telegram", user_id) == "Europe/Amsterdam"
    assert storage.get_user_dm_enabled("telegram", user_id) is True
    assert storage.get_user_muted("telegram", user_id) is True
    
    # Delete all
    storage.delete_user_data("telegram", user_id)
    
    # All should be cleared
    assert storage.get_user_timezone("telegram", user_id) is None
    assert storage.get_user_dm_enabled("telegram", user_id) is False
    assert storage.get_user_muted("telegram", user_id) is False