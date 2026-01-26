# 03 — Storage Schema (SQLite)

## Goals
- Persist minimal required state for MVP behavior.
- Keep storage simple and testable.
- Support metrics/event logging and feedback collection.

## Stored Data (MVP)

### User profile (per platform)
- user_id
- timezone (IANA string)
- dm_enabled (Telegram only)
- muted (per user)

### Discord
- monitored channel IDs per guild

### Telegram
- monitoring enabled flag per group
- group membership (best-effort, updated on messages)
- admin timezone overrides (force add / force remove)
- active timezones derived from:
  (member-configured timezones) +/- (admin overrides)

### Metrics/Events
- event_name, timestamp, platform
- optional scope_id (guild/chat), channel_id, user_id
- optional metadata_json

### Feedback
- user_id, message text, timestamp, platform

## Notes
- Membership tracking is best-effort:
  - users are touched when they send a message or command
  - users may be removed when Telegram provides a "left chat" event
