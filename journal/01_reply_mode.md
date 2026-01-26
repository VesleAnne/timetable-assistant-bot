# 01 — Reply Mode Decisions (Discord vs Telegram)

## Problem
We want the bot to help distributed teams interpret time mentions reliably without noise.

## MVP Decision
### Discord
- The bot posts a public message containing a "Convert for me" button whenever it detects a valid time mention.
- Only users who click the button get a conversion.
- The conversion is sent as an ephemeral message visible only to the clicking user.

Rationale:
- Avoids spamming channels with timezone lists.
- Supports a "self-serve" workflow.

### Telegram
- The bot replies publicly in the group with conversions for all active timezones.
- Optional DM delivery exists for users who opt in and are eligible to receive DMs.

Rationale:
- Telegram groups often benefit from a single shared conversion message.
- DM delivery provides a personalized view when needed.

## Out of Scope (MVP)
- Discord public message listing all timezone conversions
- Automatic per-user replies to every participant in Discord
- Edited message handling (responding when a message is edited)
