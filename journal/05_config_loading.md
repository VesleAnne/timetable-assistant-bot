# 05 — Config Loading (configuration.yaml + env overrides)

## Problem
We need a configuration system that:
- is easy for new developers to understand and modify
- supports local development via `.env`
- supports production deployments where secrets and overrides come from environment variables
- keeps sensitive data out of git

## MVP Decision
We split configuration into:

### 1) `configuration.yaml` (committed, non-secret)
Contains project-level settings such as:
- enabled platforms (discord/telegram)
- per-platform safety limits
- bot behavior toggles (ignore bots, edited messages off)
- i18n settings (EN/RU)
- formatting rules
- storage backend/path (SQLite in MVP)
- metrics enabled flag

### 2) `.env` / environment variables (not committed, secret + deployment overrides)
Contains:
- platform tokens:
  - `DISCORD_BOT_TOKEN`
  - `TELEGRAM_BOT_TOKEN`
- optional runtime overrides such as log level or disabling a platform

## Override Rule
**Environment variables override configuration.yaml**.

Rationale:
- This is standard for deployments (containerized apps, cloud platforms, CI).
- Allows overriding behavior without editing files in production.
- Keeps secrets separate from repo configuration.

## Per-Platform Limits
Configuration supports platform-specific limits to avoid spam/edge cases.

Example limits:
- Discord:
  - max_time_mentions_per_message
- Telegram:
  - max_time_mentions_per_message
  - max_active_timezones_in_public_reply

Rationale:
- Telegram public replies can become noisy when too many timezones are active.
- Discord conversions are per-user via button click and do not require an active timezone list.

## Validation Rules (Fail Fast)
At startup:
- If Discord is enabled but `DISCORD_BOT_TOKEN` is missing → startup fails
- If Telegram is enabled but `TELEGRAM_BOT_TOKEN` is missing → startup fails
- Storage backend must be `sqlite` in MVP (others are out of scope)

This avoids partial startup states where one adapter silently fails later.

## Implementation Notes
- Config loading is implemented in `src/config.py`.
- YAML loading is used as the lowest priority source.
- env and `.env` override YAML.
- init kwargs override all sources (useful for tests).

## Out of Scope (MVP)
- runtime config hot reload
- remote configuration service
- multiple storage backends (Postgres, Redis)