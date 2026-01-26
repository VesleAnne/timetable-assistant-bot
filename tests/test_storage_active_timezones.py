"""
Test Telegram active timezone list management.

Tests the storage layer's handling of "active timezones" (spec Section 7):
1. Active timezones are built from group member timezones
2. Only users with configured timezones contribute to the list
3. Admin overrides allow manual addition of timezones
4. Admin overrides allow manual removal of timezones
5. Removal overrides take precedence over addition
6. When a member leaves/removes their timezone, active list updates

Active timezones determine which conversions appear in Telegram public replies.

The list is computed dynamically from:
- Group members who have configured timezones
- Plus any admin-added timezone overrides
- Minus any admin-removed timezone overrides

This ensures the public reply shows conversions relevant to current participants.
"""

from __future__ import annotations


def test_active_timezones_from_members(storage):
    chat_id = "chat1"

    # users appear in membership table
    storage.telegram_touch_member(chat_id, "u1")
    storage.telegram_touch_member(chat_id, "u2")
    storage.telegram_touch_member(chat_id, "u3")

    # only two of them have timezones configured
    storage.set_user_timezone("telegram", "u1", "Europe/Amsterdam")
    storage.set_user_timezone("telegram", "u2", "Asia/Yerevan")
    # u3 has no timezone -> should not contribute

    tzs = storage.telegram_get_active_timezones(chat_id)

    assert tzs == {"Europe/Amsterdam", "Asia/Yerevan"}


def test_active_timezones_with_overrides_add(storage):
    chat_id = "chat1"

    storage.telegram_touch_member(chat_id, "u1")
    storage.set_user_timezone("telegram", "u1", "Europe/Amsterdam")

    storage.telegram_set_timezone_override(chat_id, "Asia/Tbilisi", mode="add")

    tzs = storage.telegram_get_active_timezones(chat_id)
    assert tzs == {"Europe/Amsterdam", "Asia/Tbilisi"}


def test_active_timezones_with_overrides_remove(storage):
    chat_id = "chat1"

    storage.telegram_touch_member(chat_id, "u1")
    storage.telegram_touch_member(chat_id, "u2")
    storage.set_user_timezone("telegram", "u1", "Europe/Amsterdam")
    storage.set_user_timezone("telegram", "u2", "Asia/Yerevan")

    # Remove Yerevan via admin override
    storage.telegram_set_timezone_override(chat_id, "Asia/Yerevan", mode="remove")

    tzs = storage.telegram_get_active_timezones(chat_id)
    assert tzs == {"Europe/Amsterdam"}


def test_active_timezones_override_remove_wins_over_add(storage):
    chat_id = "chat1"

    storage.telegram_touch_member(chat_id, "u1")
    storage.set_user_timezone("telegram", "u1", "Europe/Amsterdam")

    # Add then remove same tz -> should be removed
    storage.telegram_set_timezone_override(chat_id, "Asia/Tbilisi", mode="add")
    storage.telegram_set_timezone_override(chat_id, "Asia/Tbilisi", mode="remove")

    tzs = storage.telegram_get_active_timezones(chat_id)
    assert tzs == {"Europe/Amsterdam"}


def test_member_removal_affects_active_timezones(storage):
    chat_id = "chat1"

    storage.telegram_touch_member(chat_id, "u1")
    storage.set_user_timezone("telegram", "u1", "Europe/Amsterdam")

    assert storage.telegram_get_active_timezones(chat_id) == {"Europe/Amsterdam"}

    # user leaves
    storage.telegram_remove_member(chat_id, "u1")

    # no members with tz -> becomes empty
    assert storage.telegram_get_active_timezones(chat_id) == set()
