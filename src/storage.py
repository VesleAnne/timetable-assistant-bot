from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple



@dataclass(frozen=True)
class UserProfile:
    platform: str  # "discord" | "telegram"
    user_id: str
    timezone: Optional[str]
    dm_enabled: bool
    muted: bool


class SQLiteStorage:
    """
    SQLite-backed storage for MVP.

    Tables:
      - user_profiles
      - discord_monitored_channels
      - telegram_group_config
      - telegram_group_members
      - telegram_timezone_overrides
      - events
      - feedback

    Notes:
    - This storage is thread-safe via a lock (important for bot event handlers).
    - Uses CREATE TABLE IF NOT EXISTS (simple schema bootstrap).
    - Designed to be used by both Discord and Telegram adapters.
    """

    def __init__(self, sqlite_path: str) -> None:
        self.sqlite_path = sqlite_path
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(sqlite_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            cur = self._conn.cursor()

            # User profiles (per platform)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    platform TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timezone TEXT NULL,
                    dm_enabled INTEGER NOT NULL DEFAULT 0,
                    muted INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (platform, user_id)
                )
                """
            )

            # Discord: monitored channels
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS discord_monitored_channels (
                    guild_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, channel_id)
                )
                """
            )

            # Telegram: monitoring enabled flag per group
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_group_config (
                    chat_id TEXT NOT NULL PRIMARY KEY,
                    monitoring_enabled INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL
                )
                """
            )

            # Telegram: group membership tracking (best-effort)
            # We add rows as we observe messages / commands.
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_group_members (
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    last_seen_at INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, user_id)
                )
                """
            )

            # Telegram: timezone overrides (admin edits)
            # mode:
            #   - "add": force include timezone even if nobody has it
            #   - "remove": force exclude timezone even if users have it
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_timezone_overrides (
                    chat_id TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    mode TEXT NOT NULL CHECK(mode IN ('add', 'remove')),
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, timezone)
                )
                """
            )

            # Events table for metrics/analytics
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    scope_id TEXT NULL,
                    channel_id TEXT NULL,
                    user_id TEXT NULL,
                    metadata_json TEXT NULL
                )
                """
            )

            # Feedback table 
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    scope_id TEXT NULL,
                    user_id TEXT NOT NULL,
                    text TEXT NOT NULL
                )
                """
            )

            self._conn.commit()

 
    @staticmethod
    def _now_ts() -> int:
        return int(time.time())

    @staticmethod
    def _bool_to_int(v: bool) -> int:
        return 1 if v else 0

    @staticmethod
    def _int_to_bool(v: Any) -> bool:
        return bool(int(v))

    def close(self) -> None:
        with self._lock:
            self._conn.close()


    def upsert_user_profile(
        self,
        platform: str,
        user_id: str,
        timezone: Optional[str] = None,
        dm_enabled: Optional[bool] = None,
        muted: Optional[bool] = None,
    ) -> None:
        """
        Create/update a user profile.
        Any field left as None is NOT modified (except timezone, which can be explicitly set to None via clear methods).
        """
        with self._lock:
            cur = self._conn.cursor()
            existing = cur.execute(
                "SELECT * FROM user_profiles WHERE platform=? AND user_id=?",
                (platform, user_id),
            ).fetchone()

            now = self._now_ts()

            if existing is None:
                # Insert new profile with defaults
                cur.execute(
                    """
                    INSERT INTO user_profiles (platform, user_id, timezone, dm_enabled, muted, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        platform,
                        user_id,
                        timezone,
                        self._bool_to_int(dm_enabled or False),
                        self._bool_to_int(muted or False),
                        now,
                    ),
                )
            else:
                # Update only provided fields
                new_timezone = timezone if timezone is not None else existing["timezone"]
                new_dm = (
                    self._bool_to_int(dm_enabled)
                    if dm_enabled is not None
                    else int(existing["dm_enabled"])
                )
                new_muted = (
                    self._bool_to_int(muted) if muted is not None else int(existing["muted"])
                )

                cur.execute(
                    """
                    UPDATE user_profiles
                    SET timezone=?, dm_enabled=?, muted=?, updated_at=?
                    WHERE platform=? AND user_id=?
                    """,
                    (new_timezone, new_dm, new_muted, now, platform, user_id),
                )

            self._conn.commit()

    def set_user_timezone(self, platform: str, user_id: str, timezone: str) -> None:
        with self._lock:
            self.upsert_user_profile(platform=platform, user_id=user_id, timezone=timezone)
            self.log_event(
                platform=platform,
                event_name="user_timezone_set",
                user_id=user_id,
                metadata={"timezone": timezone},
            )

    def get_user_timezone(self, platform: str, user_id: str) -> Optional[str]:
        with self._lock:
            cur = self._conn.cursor()
            row = cur.execute(
                "SELECT timezone FROM user_profiles WHERE platform=? AND user_id=?",
                (platform, user_id),
            ).fetchone()
            return row["timezone"] if row else None

    def clear_user_timezone(self, platform: str, user_id: str) -> None:
        with self._lock:
            cur = self._conn.cursor()
            now = self._now_ts()
            cur.execute(
                """
                INSERT INTO user_profiles (platform, user_id, timezone, dm_enabled, muted, updated_at)
                VALUES (?, ?, NULL, 0, 0, ?)
                ON CONFLICT(platform, user_id)
                DO UPDATE SET timezone=NULL, updated_at=excluded.updated_at
                """,
                (platform, user_id, now),
            )
            self._conn.commit()

            self.log_event(platform=platform, event_name="user_timezone_cleared", user_id=user_id)

    def set_user_dm_enabled(self, platform: str, user_id: str, enabled: bool) -> None:
        """
        Telegram only in MVP, but stored per-platform to keep API consistent.
        """
        with self._lock:
            self.upsert_user_profile(platform=platform, user_id=user_id, dm_enabled=enabled)
            self.log_event(
                platform=platform,
                event_name="user_dm_setting_changed",
                user_id=user_id,
                metadata={"dm_enabled": enabled},
            )

    def get_user_dm_enabled(self, platform: str, user_id: str) -> bool:
        with self._lock:
            cur = self._conn.cursor()
            row = cur.execute(
                "SELECT dm_enabled FROM user_profiles WHERE platform=? AND user_id=?",
                (platform, user_id),
            ).fetchone()
            return self._int_to_bool(row["dm_enabled"]) if row else False

    def set_user_muted(self, platform: str, user_id: str, muted: bool) -> None:
        with self._lock:
            self.upsert_user_profile(platform=platform, user_id=user_id, muted=muted)
            self.log_event(
                platform=platform,
                event_name="user_muted" if muted else "user_unmuted",
                user_id=user_id,
            )

    def get_user_muted(self, platform: str, user_id: str) -> bool:
        with self._lock:
            cur = self._conn.cursor()
            row = cur.execute(
                "SELECT muted FROM user_profiles WHERE platform=? AND user_id=?",
                (platform, user_id),
            ).fetchone()
            return self._int_to_bool(row["muted"]) if row else False

    def delete_user_data(self, platform: str, user_id: str) -> None:
        """
        Implements /delete_me behavior.
        Removes stored timezone + dm preference + muted state for the user.
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "DELETE FROM user_profiles WHERE platform=? AND user_id=?",
                (platform, user_id),
            )
            self._conn.commit()

            self.log_event(platform=platform, event_name="user_deleted_data", user_id=user_id)

    def get_user_profile(self, platform: str, user_id: str) -> UserProfile:
        """
        Returns a profile with defaults if it does not exist.
        """
        with self._lock:
            cur = self._conn.cursor()
            row = cur.execute(
                "SELECT * FROM user_profiles WHERE platform=? AND user_id=?",
                (platform, user_id),
            ).fetchone()

            if not row:
                return UserProfile(
                    platform=platform,
                    user_id=user_id,
                    timezone=None,
                    dm_enabled=False,
                    muted=False,
                )

            return UserProfile(
                platform=platform,
                user_id=user_id,
                timezone=row["timezone"],
                dm_enabled=self._int_to_bool(row["dm_enabled"]),
                muted=self._int_to_bool(row["muted"]),
            )


    def discord_add_monitored_channel(self, guild_id: str, channel_id: str) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO discord_monitored_channels (guild_id, channel_id, created_at)
                VALUES (?, ?, ?)
                """,
                (guild_id, channel_id, self._now_ts()),
            )
            self._conn.commit()
            self.log_event(
                platform="discord",
                event_name="discord_monitor_channel_added",
                scope_id=guild_id,
                channel_id=channel_id,
            )

    def discord_remove_monitored_channel(self, guild_id: str, channel_id: str) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "DELETE FROM discord_monitored_channels WHERE guild_id=? AND channel_id=?",
                (guild_id, channel_id),
            )
            self._conn.commit()
            self.log_event(
                platform="discord",
                event_name="discord_monitor_channel_removed",
                scope_id=guild_id,
                channel_id=channel_id,
            )

    def discord_list_monitored_channels(self, guild_id: str) -> List[str]:
        with self._lock:
            cur = self._conn.cursor()
            rows = cur.execute(
                "SELECT channel_id FROM discord_monitored_channels WHERE guild_id=?",
                (guild_id,),
            ).fetchall()
            return [r["channel_id"] for r in rows]

    def discord_is_monitored_channel(self, guild_id: str, channel_id: str) -> bool:
        with self._lock:
            cur = self._conn.cursor()
            row = cur.execute(
                """
                SELECT 1 FROM discord_monitored_channels
                WHERE guild_id=? AND channel_id=?
                """,
                (guild_id, channel_id),
            ).fetchone()
            return row is not None

    def telegram_set_monitoring(self, chat_id: str, enabled: bool) -> None:
        with self._lock:
            cur = self._conn.cursor()
            now = self._now_ts()
            cur.execute(
                """
                INSERT INTO telegram_group_config (chat_id, monitoring_enabled, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id)
                DO UPDATE SET monitoring_enabled=excluded.monitoring_enabled, updated_at=excluded.updated_at
                """,
                (chat_id, self._bool_to_int(enabled), now),
            )
            self._conn.commit()

            self.log_event(
                platform="telegram",
                event_name="telegram_monitor_enabled" if enabled else "telegram_monitor_disabled",
                scope_id=chat_id,
            )

    def telegram_get_monitoring(self, chat_id: str) -> bool:
        with self._lock:
            cur = self._conn.cursor()
            row = cur.execute(
                "SELECT monitoring_enabled FROM telegram_group_config WHERE chat_id=?",
                (chat_id,),
            ).fetchone()
            return self._int_to_bool(row["monitoring_enabled"]) if row else False

    def telegram_touch_member(self, chat_id: str, user_id: str) -> None:
        """
        Register/update a user as a member of this chat (best-effort).
        Called whenever we observe a message/command from this user in this chat.
        """
        with self._lock:
            cur = self._conn.cursor()
            now = self._now_ts()
            cur.execute(
                """
                INSERT INTO telegram_group_members (chat_id, user_id, last_seen_at)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, user_id)
                DO UPDATE SET last_seen_at=excluded.last_seen_at
                """,
                (chat_id, user_id, now),
            )
            self._conn.commit()

    def telegram_remove_member(self, chat_id: str, user_id: str) -> None:
        """
        Remove a user from membership table.
        Intended to be called when Telegram reports "user left" event.
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "DELETE FROM telegram_group_members WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
            self._conn.commit()

    def telegram_list_members(self, chat_id: str) -> List[str]:
        with self._lock:
            cur = self._conn.cursor()
            rows = cur.execute(
                "SELECT user_id FROM telegram_group_members WHERE chat_id=?",
                (chat_id,),
            ).fetchall()
            return [r["user_id"] for r in rows]


    def telegram_set_timezone_override(self, chat_id: str, timezone: str, mode: str) -> None:
        """
        mode = "add" | "remove"
        """
        if mode not in {"add", "remove"}:
            raise ValueError("mode must be 'add' or 'remove'")

        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO telegram_timezone_overrides (chat_id, timezone, mode, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, timezone)
                DO UPDATE SET mode=excluded.mode, updated_at=excluded.updated_at
                """,
                (chat_id, timezone, mode, self._now_ts()),
            )
            self._conn.commit()

            self.log_event(
                platform="telegram",
                event_name="telegram_timezone_override_set",
                scope_id=chat_id,
                metadata={"timezone": timezone, "mode": mode},
            )

    def telegram_clear_timezone_override(self, chat_id: str, timezone: str) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "DELETE FROM telegram_timezone_overrides WHERE chat_id=? AND timezone=?",
                (chat_id, timezone),
            )
            self._conn.commit()

            self.log_event(
                platform="telegram",
                event_name="telegram_timezone_override_cleared",
                scope_id=chat_id,
                metadata={"timezone": timezone},
            )

    def telegram_list_timezone_overrides(self, chat_id: str) -> Dict[str, str]:
        """
        Returns {timezone: mode} mapping.
        """
        with self._lock:
            cur = self._conn.cursor()
            rows = cur.execute(
                "SELECT timezone, mode FROM telegram_timezone_overrides WHERE chat_id=?",
                (chat_id,),
            ).fetchall()
            return {r["timezone"]: r["mode"] for r in rows}


    def telegram_get_active_timezones(self, chat_id: str) -> Set[str]:
        """
        Computes Telegram active timezones as:

            base = distinct timezones of current members in chat (if user_profile timezone exists)
            active = (base ∪ forced_additions) - forced_removals

        This matches the spec:
        - active timezones come from participants who configured a timezone
        - admin can add/remove timezones manually

        Returns a set of IANA timezone strings.
        """
        with self._lock:
            cur = self._conn.cursor()

            # Base from group members
            member_rows = cur.execute(
                """
                SELECT DISTINCT up.timezone AS tz
                FROM telegram_group_members gm
                JOIN user_profiles up
                  ON up.platform='telegram' AND up.user_id=gm.user_id
                WHERE gm.chat_id=? AND up.timezone IS NOT NULL
                """,
                (chat_id,),
            ).fetchall()

            base: Set[str] = {r["tz"] for r in member_rows if r["tz"]}

            overrides = self.telegram_list_timezone_overrides(chat_id)
            additions = {tz for tz, mode in overrides.items() if mode == "add"}
            removals = {tz for tz, mode in overrides.items() if mode == "remove"}

            return (base | additions) - removals


    def log_event(
        self,
        platform: str,
        event_name: str,
        scope_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store a metrics/event row.
        metadata is stored as JSON.
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO events (ts, platform, event_name, scope_id, channel_id, user_id, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._now_ts(),
                    platform,
                    event_name,
                    scope_id,
                    channel_id,
                    user_id,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            self._conn.commit()

    def list_events(
        self,
        event_name: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Debug helper: fetch recent events.
        """
        with self._lock:
            cur = self._conn.cursor()
            query = "SELECT * FROM events WHERE 1=1"
            params: List[Any] = []

            if event_name:
                query += " AND event_name=?"
                params.append(event_name)
            if platform:
                query += " AND platform=?"
                params.append(platform)

            query += " ORDER BY ts DESC LIMIT ?"
            params.append(limit)

            rows = cur.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]


    def save_feedback(
        self,
        platform: str,
        user_id: str,
        text: str,
        scope_id: Optional[str] = None,
    ) -> None:
        """
        Stores feedback in the feedback table and also logs an event.
        """
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                INSERT INTO feedback (ts, platform, scope_id, user_id, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (self._now_ts(), platform, scope_id, user_id, text),
            )
            self._conn.commit()

            self.log_event(
                platform=platform,
                event_name="feedback_submitted",
                scope_id=scope_id,
                user_id=user_id,
                metadata={"text": text},
            )

    def list_feedback(self, platform: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Debug helper: fetch recent feedback.
        """
        with self._lock:
            cur = self._conn.cursor()
            if platform:
                rows = cur.execute(
                    "SELECT * FROM feedback WHERE platform=? ORDER BY ts DESC LIMIT ?",
                    (platform, limit),
                ).fetchall()
            else:
                rows = cur.execute(
                    "SELECT * FROM feedback ORDER BY ts DESC LIMIT ?",
                    (limit,),
                ).fetchall()

            return [dict(r) for r in rows]
