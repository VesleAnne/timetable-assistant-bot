# Developer Onboarding & Handover

Welcome! This guide is for developers joining the **Timetable Assistant Bot** codebase.

It focuses on:
- running the project locally (Discord + Telegram)
- running tests and making changes safely
- where core logic vs platform code lives
- what to check first when something doesn’t work

For product requirements and expected behavior, also read:
- **Specification:** `docs/spec.md`
- **Architecture:** `docs/architecture.md`
- **Acceptance scenarios:** `docs/acceptance_tests.md`
- **Implementation journal:** `journal/PROGRESS.md` (+ `journal/` entries)

---

## Repository tour

High-level structure (current repo):

- `src/` — application code
  - `engine.py` — platform-agnostic orchestration (parse → resolve tz → convert → format)
  - `parser.py` — time mention detection (English + Russian) + ignore rules
  - `conversion.py` — timezone conversions (IANA/zoneinfo-based)
  - `formatting.py` — output formatting + EN/RU templates
  - `storage.py` — SQLite persistence and simple schema bootstrap
  - `discord_bot.py` — Discord adapter (slash commands, channel monitoring, “Convert for me”button)
  - `telegram_bot.py` — Telegram adapter (commands, public replies, optional DM delivery)
  - `config.py` — settings model + YAML + `.env` loading
  - `timezones.py` — the curated list of cities 
  - `main.py` — CLI entrypoint (`python -m src.main {discord|telegram}`)
- `tests/` — pytest suite (core units + adapter flows)
- `docs/` — documentation (`INSTALL.md`, `spec.md`, `architecture.md`, this file)
- `configuration.yaml` — non-secret runtime configuration
- `.env.example` — example secrets/overrides for local dev
- `Dockerfile`, `docker-compose.yml` — containerized deployment
- `run.sh` — convenience wrapper for common commands

---

## Local development setup

### 1) System prerequisites

From the existing docs and repo config:
- Python **3.9+** (the Docker image uses Python 3.11)
- `pip`
- Git

See: `docs/INSTALL.md`

### 2) Clone and install dependencies

```bash
git clone <REPO_URL>
cd timetable-assistant-bot

# Runtime dependencies
pip install -r requirements.txt

# Dev dependencies (recommended)
pip install -r requirements-dev.txt
Alternative editable installs (supported by pyproject.toml):
pip install -e .
pip install -e ".[dev]"
```

### 3) Configure secrets (.env)

Copy the example file and insert your tokens:

cp .env.example .env
.env.example currently includes:
DISCORD_BOT_TOKEN=...
TELEGRAM_BOT_TOKEN=...
SQLITE_PATH=... (optional override)
Tokens must not be committed. Keep them in .env locally, or supply them via environment variables in production.

### 4) Configure non-secrets (configuration.yaml)
The repo ships with a default configuration.yaml.
This file includes platform enablement, parsing/formatting behavior, and storage location.
Relevant sections (current file):

platforms.discord.enabled
platforms.telegram.enabled
storage.sqlite_path
telegram.dm_delivery.enabled
metrics.enabled
formatting.*
Running the bot locally
Option A: Directly (CLI)
The documented entrypoint is:
python -m src.main telegram
# or
python -m src.main discord
CLI flags documented in docs/INSTALL.md and implemented in src/main.py:
--config <path> (default: configuration.yaml)
--log-level <level> (default: INFO)
Example:
python -m src.main telegram --log-level DEBUG
Option B: Convenience script (run.sh)
run.sh wraps common operations:
./run.sh telegram
./run.sh discord --debug
./run.sh test
./run.sh format
./run.sh lint
./run.sh typecheck
Note: run.sh delegates to python -m src.main ....
Option C: Docker / docker-compose
docker-compose up -d telegram
docker-compose up -d discord
See: Dockerfile, docker-compose.yml, and docs/INSTALL.md.
Database / persistence
Storage is SQLite (MVP) and is initialized automatically on first run.
Default DB path (unless overridden):

./data/bot.db (storage.sqlite_path in configuration.yaml)
or via env var SQLITE_PATH (as shown in README / .env.example)
Schema bootstrap happens in SQLiteStorage._init_schema() in src/storage.py.
Tables created by src/storage.py:

user_profiles
discord_monitored_channels
telegram_group_config
telegram_group_members
telegram_timezone_overrides
events
feedback
Running the test suite
Install test dependencies (included in requirements-dev.txt), then:
pytest -v
# or
pytest tests/ -v
Coverage (supported by dev deps):
pytest tests/ --cov=src --cov-report=html
Related configs:
pytest.ini
tests/conftest.py
Code quality checks
Commands are documented in README.md and supported by requirements-dev.txt:
# Format
black src/ tests/
isort src/ tests/

# Lint
ruff check src/ tests/
flake8 src/ tests/  # optional, also listed in requirements-dev.txt

# Type check
mypy src/
run.sh also exposes: format, lint, typecheck.
How the bot works (mental model)
A good starting point for understanding runtime behavior:
Adapter receives a message
Discord: src/discord_bot.py
Telegram: src/telegram_bot.py
Message is parsed
src/parser.py extracts:
time mentions (single times, multiple times, ranges)
optional timezone in text
optional date anchor (today/tomorrow/weekday)
language (EN/RU)
Engine resolves & converts
src/engine.py decides:
source timezone (explicit or inferred)
target timezone(s) (depends on platform)
conversion logic in src/conversion.py
Formatted output is generated
src/formatting.py chooses templates (EN/RU) and output layout
Adapter sends response back
Discord: public “Convert for me” button → ephemeral conversion on click
Telegram: one public reply for the group + optional per-user DMs
The architecture doc has end-to-end flow diagrams:
docs/architecture.md
Common development tasks
Add or adjust parsing rules
Main parsing logic: src/parser.py
Parser behavior is heavily covered by:
tests/test_parser_en.py
tests/test_parser_ru.py
tests/test_weekday_resolution.py
tests/test_timezone_resolution.py
Suggested workflow:
Add/modify a test that demonstrates the desired new behavior
Update parser implementation
Run full suite: pytest -v
Adjust conversion behavior
Conversion code: src/conversion.py
Unit tests: tests/test_conversion.py
Adjust output formatting
Formatting templates and rules: src/formatting.py
Tests: tests/test_formatting_date_on_both_sides.py
Update storage behavior
Persistence layer: src/storage.py
Tests:
tests/test_commands_storage.py
tests/test_storage_active_timezones.py
tests/test_metrics_events.py
Platform adapters and commands
Discord
Primary module: src/discord_bot.py
Discord behaviors implemented in code:

channel monitoring via /monitor ...
message listener posts a “Convert for me” button when a time is detected
conversion response is ephemeral (visible only to the clicker)
Flow tests:
tests/test_discord_flow.py
tests/test_engine_ignores_bots_and_edits.py
Telegram
Primary module: src/telegram_bot.py
Telegram behaviors implemented in code:

group monitoring toggles: /monitor_on, /monitor_off, /monitor_status
user settings:
/tz ...
/dm on|off|status
public reply converts to “active timezones”
optional per-user DM conversions when enabled in user profile
Flow tests:
tests/test_telegram_flow.py
Configuration system (YAML + env)
Configuration sources are implemented in src/config.py:
configuration.yaml (lowest priority)
environment variables (override YAML)
.env (loaded automatically for local dev; overrides YAML)
init kwargs (highest priority, mostly for tests)
Environment variables observed in the codebase:
DISCORD_BOT_TOKEN
TELEGRAM_BOT_TOKEN
SQLITE_PATH (used in README / .env.example)
ENV
LOG_LEVEL
CONFIG_PATH
Known runtime mismatches (current repo state)
These are observable inconsistencies between modules that affect “run the bot” paths:
src/main.py calls load_settings(args.config), but
src/config.py:load_settings() currently takes no arguments.
src/main.py expects settings.telegram.token and settings.discord.token, but
src/config.py defines telegram_bot_token / discord_bot_token instead.
src/main.py reads Telegram settings like
settings.telegram.max_active_timezones_public_reply and settings.telegram.enable_dm_delivery, but
src/config.py’s TelegramConfig currently only defines dm_delivery.enabled.
If you are onboarding and need to run the bot locally, the quickest path is to:
align the Settings model in src/config.py with what src/main.py reads, or
update src/main.py to use the fields that currently exist in src/config.py.
Tests currently do not execute the CLI entrypoint (python -m src.main ...), so these mismatches can exist while pytest still passes.
Where to start as a new developer
If you want the fastest “get productive” route:
Run the test suite and ensure it passes:
pytest -v
Read the spec + architecture:
docs/spec.md
docs/architecture.md
Pick a small change and follow the test-first loop:
add/adjust a parsing test (tests/test_parser_en.py)
implement the parser change (src/parser.py)
run pytest -v
(Optional) Fix the runtime mismatches listed above so python -m src.main ... runs end-to-end.
Useful references
Installation & deployment: docs/INSTALL.md
Architecture & data flows: docs/architecture.md
Product specification: docs/spec.md
Acceptance scenarios: docs/acceptance_tests.md
Implementation journal: journal/PROGRESS.md
