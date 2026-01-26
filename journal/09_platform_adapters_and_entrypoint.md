# 09 — Platform Adapters + Single Entrypoint (Discord + Telegram)

## Goal
After implementing the core logic (parser → conversion → formatting → engine), the next priority was to make the project runnable end-to-end:

- Telegram: group monitoring + public replies + optional DMs
- Discord: monitored channels + “Convert for me” button + per-user ephemeral conversion
- A single entrypoint (`src/main.py`) to run either platform cleanly

This directly supports the evaluation criteria:
- **Does the project run?**
- **How easy is it to test and hand over?**

---

## What Was Implemented

### 1) Telegram Adapter (`src/telegram_bot.py`)
Implemented a minimal MVP Telegram bot using `python-telegram-bot` (async):

**Admin-only commands**
- `/monitor_on` — enable monitoring in current group
- `/monitor_off` — disable monitoring
- `/monitor_status` — show state

**User commands**
- `/tz set <timezone>`
- `/tz show`
- `/tz clear`
- `/dm on | off | status`
- `/feedback <text>`
- `/delete_me`

**Message behavior**
- Only reacts in monitored group chats
- Ignores bot accounts
- Only processes newly sent messages (edited messages are ignored in MVP)
- Converts detected times into the group’s **active timezones**
- Optionally sends DMs to eligible users who enabled `/dm on`
  - DM sending is best-effort (Telegram limitation: user must start private chat with bot)

**Active timezone logic**
- Uses `storage.telegram_get_active_timezones(chat_id)`
- Tracks group members via `telegram_touch_member(chat_id, user_id)`
- Removes members when Telegram reports a leave event

---

### 2) Discord Adapter (`src/discord_bot.py`)
Implemented a minimal MVP Discord bot using `discord.py` 2.x:

**Admin-only commands**
- `/monitor add` — channel selector UI to add monitored channels
- `/monitor remove` — selector UI to remove monitored channels
- `/monitor list` — list monitored channel IDs

**User commands**
- `/tz set <timezone>`
- `/tz show`
- `/tz clear`
- `/feedback <text>`
- `/delete_me`

**Message behavior**
- Only reacts in monitored channels
- Ignores bot messages
- Detects time mentions → posts a public message with a button: **Convert for me**
- On button click → sends an ephemeral per-user conversion (only visible to the clicker)

**Important Discord note**
The bot requires **Message Content Intent** enabled to read message text.
This must be enabled in the Discord Developer Portal.

---

### 3) Single Entrypoint (`src/main.py`)
Implemented `main.py` to run either platform with the same command:

```bash
python -m src.main telegram
python -m src.main discord


