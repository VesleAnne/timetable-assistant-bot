# Timetable Assistant Bot — Architecture (v0.1)

This document describes the MVP architecture for the Timetable Assistant Bot supporting **Discord** and **Telegram**.
The primary goal is to keep the codebase simple while ensuring:
- shared core logic across platforms
- clear separation between platform adapters and conversion logic
- strong testability
- easy extensibility (e.g. WhatsApp in the future)

---

## 1. Architecture Overview

The bot is composed of four main parts:

1) **Platform Adapters**
- `discord_bot.py`: Discord message listener, slash commands, and "Convert for me" button interactions
- `telegram_bot.py`: Telegram message listener, commands, public replies, and optional DM delivery

2) **Core Engine (shared)**
- `engine.py`: the orchestration layer that:
  - parses a message
  - resolves source timezone
  - resolves target timezone(s)
  - converts times
  - formats output (English/Russian)

3) **Parsing + Detection**
- `parser.py`: time mention detection (English + Russian) and ignore rules

4) **Storage**
- `storage.py`: persistent state storage (SQLite in MVP)

Supporting modules:
- `conversion.py`: timezone conversion logic (DST-safe, IANA-based)
- `formatting.py`: output formatting rules + language templates (EN/RU)
- `models.py`: shared data structures and types
- `config.py`: environment configuration
- `main.py`: application entrypoint to start Discord and/or Telegram adapters

---

## 2. Data Flow

### 2.1 Discord Flow (Message → Button → Ephemeral Conversion)

**Given** a monitored Discord channel and a newly sent message:

1. Discord receives `MESSAGE_CREATE`
2. `discord_bot.py` checks:
   - channel is monitored
   - message is not edited
   - sender is not a bot
3. `parser.py` extracts time mentions + optional timezone + language
4. If at least one valid time mention is found:
   - bot posts a public message containing a **"Convert for me"** button
   - the public message stores the minimal metadata required to compute conversions on click:
     - detected times (including multiple times/ranges)
     - resolved source timezone (explicit or inferred)
     - detected language
5. When a user clicks the button:
   - `discord_bot.py` loads clicker timezone from `storage.py`
   - If missing → send ephemeral onboarding message
   - Else → call `engine.py` to convert detected time(s) to clicker timezone
   - Respond with an **ephemeral** message visible only to the clicker

### 2.2 Telegram Flow (Public Reply + Optional DM)

**Given** a monitored Telegram group and a newly sent message:

1. Telegram receives a message update
2. `telegram_bot.py` checks:
   - monitoring is enabled for this group
   - message is not edited
3. `parser.py` extracts time mentions + optional timezone + language
4. If at least one valid time mention is found:
   - `engine.py` resolves source timezone
   - bot posts a **single combined** public reply converting to all group **active timezones**
5. Optional DM flow:
   - for each user with `/dm on` and eligible for DMs, bot may send a private message containing the conversion in the user’s timezone

---

## 3. Core Engine Responsibilities (`engine.py`)

The core engine is platform-agnostic and contains no Discord/Telegram code.

### 3.1 Inputs
- message text (plain string)
- sender timezone (optional, from storage)
- target timezone(s) (either one timezone or a set)
- language (English/Russian)

### 3.2 Outputs
- formatted string output for the platform adapter to send
- onboarding instructions when timezone resolution is impossible

### 3.3 Responsibilities
- call `parser.py` to detect time mentions and extract optional timezone/date anchors
- apply **source timezone resolution** rules from the spec
- apply **target timezone selection** rules based on platform:
  - Discord: clicking user timezone
  - Telegram public: active timezone list
  - Telegram DM: receiving user timezone
- perform conversions via `conversion.py`
- generate user-facing output via `formatting.py`

---

## 4. Parsing & Detection (`parser.py`)

The parser implements:
- supported time formats (English + Russian)
- supported timezone expressions
- date anchors and weekday references
- ignore rules (versions, numeric dates, code blocks, floats, etc.)

Parser output is a structured representation containing:
- detected time mentions (including multiple times and ranges)
- explicit timezone mention (if present)
- date anchor info (today/tomorrow/weekday modifiers)
- detected language

---

## 5. Conversion (`conversion.py`)

Timezone conversion must:
- use **IANA timezone rules**
- correctly handle **DST transitions**
- support conversion for:
  - single times
  - multiple times in one message
  - time ranges (convert both endpoints)

---

## 6. Formatting & i18n (`formatting.py`)

Formatting rules:
- mirror sender time style (12h vs 24h)
- timezone labels appear as city names (e.g. `Amsterdam`, `Yerevan`)
- include day markers when conversion crosses midnight
- Telegram public replies are sorted by UTC offset
- output language matches triggering message (English/Russian)

A small internal dictionary-based i18n mechanism is sufficient for MVP:
- fixed response strings translated in EN/RU
- onboarding messages translated in EN/RU

---

## 7. Storage (`storage.py`)

Storage is implemented as SQLite for MVP.

### 7.1 Stored Data
Per user (per platform):
- `user_id`
- `timezone` (IANA)
- `dm_enabled` (Telegram only)

Per Discord server:
- monitored channel IDs

Per Telegram group:
- monitoring enabled flag
- optional active timezone overrides (admin edited list)

### 7.2 Storage API (minimum operations)
- set/get/clear timezone for user
- set/get Telegram DM preference
- delete user data (`/delete_me`)
- add/remove/list monitored Discord channels
- enable/disable Telegram monitoring per group
- read Telegram monitoring status
- edit Telegram active timezone overrides

---

## 8. Testing Strategy

### 8.1 Unit Tests (Core)
- English time parsing
- Russian time parsing
- ignore rules
- timezone resolution
- conversion correctness
- formatting rules (mirror time style, day markers, sorting, language)

### 8.2 Flow Tests (Adapters)
- Discord: message → button message created
- Discord: button click → ephemeral output
- Telegram: message → single combined reply
- Telegram: DM on/off behavior

Acceptance tests are documented in `docs/acceptance_tests.md` and should map to these test suites.

---

## 9. Repo Structure (MVP)

```txt
timetable-assistant-bot/
├─ README.md
├─ .env.example
├─ pyproject.toml
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ requirements-dev.txt
├─ run.sh
├─ configuration.yaml
├─ pytest.ini
│
├─ docs/
│  ├─ spec.md
│  ├─ acceptance_tests.md
│  ├─ architecture.md
│  └─ onboarding.md
│
├─ src/
│  ├─ main.py
│  ├─ config.py
│  ├─ storage.py
│  ├─ models.py
│  ├─ engine.py
│  ├─ parser.py
│  ├─ conversion.py
│  ├─ formatting.py
│  ├─ timezones.py
│  ├─ discord_bot.py
│  └─ telegram_bot.py
│
├─ tests/
│  ├─ conftest.py
│  ├─ test_commands_storage.py
│  ├─ test_discord_flow.py
│  ├─ test_engine_ignores_bots_and_edits.py
│  ├─ test_engine_onboarding_missing_sender_timezone.py
│  ├─ test_engine_unknown_timezone.py
│  ├─ test_formatting_date_on_both_sides.py
│  ├─ test_metrics_events.py
│  ├─ test_parser_en.py
│  ├─ test_parser_ru.py
│  ├─ test_storage_active_timezones.py
│  ├─ test_telegram_flow.py
│  ├─ test_timezone_resolution.py
│  └─ test_weekday_resolution.py
│
└─ .gitignore
```
