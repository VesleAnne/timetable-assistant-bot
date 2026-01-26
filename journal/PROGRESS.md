# Implementation Progress Journal

This file tracks implementation progress, scope boundaries, and decisions made while building the MVP.

## MVP Scope (in progress)
✅ Discord + Telegram support  
✅ English + Russian detection + responses  
✅ Source timezone resolution rules  
✅ Telegram active timezone list  
✅ Discord "Convert for me" button + per-user ephemeral conversion  
✅ Telegram public conversion reply + optional DM delivery  
✅ Ignore rules (versions, numeric dates, code blocks, floats, etc.)  
✅ /feedback, /mute, /unmute  
✅ Event/metrics recording (SQLite)

## Out of scope (explicit)
- WhatsApp integration (future)
- Responding to edited messages (future)
- Natural-language fuzzy time parsing beyond defined formats (future)
- Automatic inference of user timezone without explicit input (future)

## Current Work Items
- [x] spec.md finalized
- [x] acceptance_tests.md created
- [x] architecture.md drafted (simplified repo structure)
- [x] configuration.yaml schema defined
- [x] src/config.py implemented (env overrides YAML)
- [x] src/storage.py implemented (SQLite)
- [ ] src/models.py
- [ ] src/parser.py
- [ ] src/engine.py
- [ ] src/conversion.py
- [ ] src/formatting.py
- [ ] src/discord_bot.py
- [ ] src/telegram_bot.py
- [ ] tests implementation
- [ ] run.sh implementation
- [ ] docs/onboarding.md implementation

## Notes / Principles
- MVP prioritizes correctness and explicit behavior over guessing user intent.
- All platform adapters remain thin; shared logic lives in core modules.
- Feature flags exist to safely extend behavior beyond MVP without breaking it.


## 2026-01-22 — Core runnable MVP: Telegram + Discord adapters + entrypoint
- Implemented Telegram bot adapter (`src/telegram_bot.py`)
  - Admin-only monitoring commands: `/monitor_on`, `/monitor_off`, `/monitor_status`
  - User timezone commands: `/tz set|show|clear`
  - DM opt-in/out commands: `/dm on|off|status`
  - Feedback + data deletion: `/feedback`, `/delete_me`
  - Public group replies using active timezones + optional per-user DMs (best-effort)

- Implemented Discord bot adapter (`src/discord_bot.py`)
  - Admin-only channel monitoring: `/monitor add|remove|list`
  - User timezone commands: `/tz set|show|clear`
  - Public “Convert for me” button on detection + per-user ephemeral conversion on click
  - Feedback + data deletion: `/feedback`, `/delete_me`

- Added single entrypoint (`src/main.py`)
  - Run either platform bot via CLI:
    - `python -m src.main telegram`
    - `python -m src.main discord`

- Documented decisions and rationale in `journal/09_platform_adapters_and_entrypoint.md`
