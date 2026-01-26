# Timetable Assistant Bot — Specification (v0.1)

## 1. Purpose
The bot detects time mentions in chat messages and replies with the equivalent times in the timezones of other participants.  
It is intended for internal team use to reduce timezone confusion when coordinating meetings, releases, and events across distributed locations.


## 2. Platforms & Environments
### 2.1 Supported Platforms
- Discord
- Telegram

WhatsApp integration is out of scope for the MVP.
Reason: WhatsApp’s bot policy and platform constraints add significant complexity (approval flow, messaging rules, hosting/verification requirements) that are not aligned with MVP goals.


### 2.2 Monitoring Scope
The bot monitors only explicitly configured locations:
- Discord: selected text channels inside a server
- Telegram: selected group chats

Only admins are allowed to configure which channels/groups are monitored.

### 2.3 Reply Mode (MVP)

Discord: When a time mention is detected in a monitored channel, the bot posts a public message containing a "Convert for me" button.

When a user clicks the button, the bot responds with an ephemeral message containing the converted time in that user's configured timezone.

Telegram: 

When a time mention is detected in a monitored group chat, the bot replies in the same group with timezone conversions.

Optionally, the bot may send direct messages to participants containing the converted time in their configured timezone.
A user is eligible to receive direct messages only if:
- they have explicitly opted in to DM delivery, and
- they have started a private chat with the bot at least once (Telegram platform limitation).

### 2.4 Language Support (MVP)
The bot MUST support messages written in:
- English
- Russian

Time detection MUST work for both languages.
The bot MUST respond in the same language as the triggering message:
- English messages → English bot responses
- Russian messages → Russian bot responses

## 3. Glossary
- Active Timezones: Set of timezones used for public conversion output in a Telegram group.
- Source Timezone: Timezone assumed for interpreting the detected time mention before conversion.
- Target Timezones: Timezones that the bot converts the detected time into (Telegram: active timezones; Discord: the clicking user’s timezone).
- Time Mention: A detected time expression in a message (e.g. `10:30`, `10am`, `22h30`, `10:00–11:00`).
- Participant Timezone: The timezone configured by a specific user.
- Group Default Timezone: Not used in MVP.

## 4. High-Level Behavior

### 4.1 When the Bot Responds
The bot MUST respond when all of the following are true:
- The message is posted in a monitored location:
  - Discord: a monitored text channel
  - Telegram: a monitored group chat
- The message is newly sent (not an edited message).
- The message is not sent by a bot account (including itself).
- The bot detects at least one valid time mention according to Section 5.

If a time mention is detected but the source timezone cannot be resolved (no explicit timezone in the message and the sender has no configured timezone), the bot MUST respond with an onboarding message asking the sender to set their timezone (e.g. `/tz set Europe/Amsterdam`) and MUST NOT attempt conversion.

### 4.2 What the Bot Responds With

#### Discord
When a time mention is detected in a monitored channel, the bot MUST post a public message containing a **"Convert for me"** button.

When a user clicks the button:
- If the clicking user has a configured timezone, the bot MUST reply with an **ephemeral** message containing the time converted into that user’s timezone.
- If the clicking user does not have a configured timezone, the bot MUST reply with an ephemeral onboarding message asking the user to set their timezone.

#### Telegram
When a time mention is detected in a monitored group chat, the bot MUST reply in the group with timezone conversions for all **active timezones** of that group.

If multiple times are detected within a single message, the bot MUST respond with a **single combined reply** that includes conversions for all detected times.

If DM delivery is enabled for a user (`/dm on`) and the user is eligible to receive DMs (has started a private chat with the bot at least once), the bot MAY additionally send that user a DM containing the converted time in that user’s configured timezone.

### 5.1 Supported Time Formats (MVP)

The bot MUST detect the following time formats:
- `HH:MM` (e.g. `10:30`, `17:45`)
- `H[am/pm]` (e.g. `10am`, `10pm`)
- `H am/pm` and `H a.m./p.m.` (e.g. `10 am`, `10 a.m.`)
- `HHhMM` (e.g. `22h30`)
- `noon`, `midnight`, `half past`, `quarter past`, `quarter to`
- time ranges using en dash or hyphen (e.g. `10:00–11:00`, `10:00-11:00`)
- multiple times in one message (e.g. `10:30 or 14:00`)

- Russian time phrasing:
  - `в HH:MM` (e.g. `в 10:30`, `в 22:30`)
  - `в H утра/вечера/дня/ночи` (e.g. `в 10 утра`, `в 7 вечера`)

The bot MUST NOT detect:
- `10.30`
- `10` (a standalone number without minutes or am/pm)
- `в 10` (standalone hour without minutes or time-of-day qualifier)

### 5.2 Supported Timezone Expressions (MVP)

The bot MUST support explicit timezones specified in messages, including:
- city names from the curated list (e.g. `Amsterdam`, `Yerevan`)
- IANA timezone strings (e.g. `Europe/Amsterdam`)
- timezone abbreviations (e.g. `CET`, `EET`, `PST`)
- UTC offsets (e.g. `UTC+4`, `+04:00`)

### City Name Support (MVP Limitation)
City-name timezone detection is supported only for a **curated list** of cities relevant to the team and examples (e.g. `Amsterdam`, `Yerevan`).

If a user mentions a city name that is not recognized (e.g. `Berlin`), the bot MUST respond with an error message suggesting an IANA timezone format, for example:
- `Europe/Berlin`

Timezone abbreviations (e.g. `CET`, `PST`) are supported only for a **curated list** in MVP due to ambiguity.


### 5.3 Date Handling (MVP)

#### Date handling

The bot MUST support date anchor words to interpret a full datetime when present.

Supported date anchors (English and Russian):
- `today`, `сегодня`
- `tomorrow`, `завтра`
- weekday references:
  - English: `Mon`, `Monday`, `Tue`, `Tuesday`, etc.
  - Russian: `пн`, `понедельник`, `вт`, `вторник`, `ср`, `среда`, `чт`, `четверг`, `пт`, `пятница`, `сб`, `суббота`, `вс`, `воскресенье`
- optional phrasing such as:
  - English: `on Monday`, `this Monday`, `next Monday`
  - Russian: `в понедельник`, `в этот понедельник`, `в следующий понедельник`

#### Interpretation Rules
- If a detected time mention includes `today`, the date MUST be interpreted as the current date in the **source timezone**.
- If a detected time mention includes `tomorrow`, the date MUST be interpreted as the next date (+1 day) in the **source timezone**.
- If a detected time mention includes a weekday, the bot MUST resolve it to a concrete calendar date in the **source timezone** and display it in output (e.g. `Mon, Feb 2`).

If no date anchor is present, the bot treats the detected time mention as a time-of-day without a calendar date.
In this case, conversions may still display day rollover markers such as `(next day)` when timezone conversion crosses midnight.

Examples:
User in Amsterdam says: see you 23:30 (no date)
Bot interprets this as today at 23:30 Amsterdam, then converts.
In Yerevan it may become tomorrow 02:30.

### 5.4 Messages That Must Be Ignored

To avoid false positives, the bot MUST NOT detect time mentions in the following cases:

- Software version numbers (e.g. `v10.3.0`, `version 2.14.7`)
- Date-like numeric formats (e.g. `10/11`, `01/02/2026`)
- Rating-like formats (e.g. `10/10`)
- Numeric values with units or currency (e.g. `10km`, `10$`, `€10`)
- Float/decimal numbers that are not valid time mentions (e.g. `5.836`)
- Any content inside code blocks (inline or multiline), e.g.:
  - Inline code: `` `see you at 10:30` ``
  - Multiline code fences:
    ```txt
    see you at 10:30
    ```

## 6. Source Timezone Resolution

The “source timezone” is the timezone assumed for the detected time mention before converting it into other timezones.

Priority order:
1. If the message includes an explicit timezone (e.g. "10:00 Amsterdam", "10:00 UTC+4"), the bot MUST use that timezone.
2. Otherwise, the bot MUST use the sender’s configured timezone.
3. If the sender has no configured timezone, the bot MUST ask the sender to clarify or set their timezone before conversion is performed.


## 7. Target Timezones (“Active Timezones”)

### 7.1 Definition
“Active timezones” are the set of timezones used for public timezone conversion output in Telegram group chats.

Discord does not use the active timezone list for conversions in MVP (conversion is per-user via button click).

### 7.2 How Active Timezones Are Built (Telegram)
A timezone becomes active in a Telegram group when at least one participant in that group has configured that timezone.

### 7.3 Expiration / Cleanup (Telegram)
A timezone is automatically removed from the active timezone list when there are no remaining users in the group with that timezone.

### 7.4 Admin Overrides (Telegram)
Admins can manually edit the active timezone list for a Telegram group, including:
- removing specific timezones
- adding specific timezones


## 8. Timezone Management (User & Group)

### 8.1 Discord Commands

#### Admin Commands (Discord)
Admins MUST be able to configure which channels the bot monitors.

- `/monitor add`
  - Opens a channel selector UI to choose one or more text channels to monitor.
  - The bot MUST store selected channel IDs.
  - The bot MUST only process messages from monitored channels.

- `/monitor remove`
  - Opens a channel selector UI listing currently monitored channels.
  - Removes selected channels from the monitored set.

- `/monitor list`
  - Displays the list of monitored channels.

#### User Commands (Discord)
Users MUST be able to configure their timezone.

- `/tz set <timezone>`
  - Sets the user's timezone for that platform.
  - `<timezone>` MUST be an IANA timezone string (e.g. `Europe/Amsterdam`, `Asia/Yerevan`).

- `/tz show`
  - Shows the user's currently configured timezone.

- `/tz clear`
  - Removes the user's configured timezone.

### 8.2 Telegram Commands

#### Admin Commands (Telegram)
Admins MUST be able to enable or disable monitoring per group chat.

- `/monitor_on`
  - Enables monitoring for the current group chat.
  - When monitoring is enabled, the bot MUST parse messages and respond to time mentions.

- `/monitor_off`
  - Disables monitoring for the current group chat.

- `/monitor_status`
  - Displays whether monitoring is enabled for the current group chat.

Admins MUST be able to edit the active timezone list for a Telegram group:
- removing specific timezones
- adding specific timezones

#### User Commands (Telegram)
Users MUST be able to configure their timezone.

- `/tz set <timezone>`
  - Sets the user's timezone for that platform.
  - `<timezone>` MUST be an IANA timezone string (e.g. `Europe/Amsterdam`, `Asia/Yerevan`).

- `/tz show`
  - Shows the user's currently configured timezone.

- `/tz clear`
  - Removes the user's configured timezone.

#### DM Delivery Settings (Telegram)
Users MAY opt in to receiving per-user conversions via Direct Messages (DM).

- `/dm on`
  - Enables DM delivery for the user.

- `/dm off`
  - Disables DM delivery for the user.

- `/dm status`
  - Shows whether DM delivery is enabled.

Note: Telegram platform limitation:
A Telegram user can only receive DMs from the bot if they have started a private chat with the bot at least once.

### 8.3 UX for Users Without a Timezone Set
If a time mention is detected but the sender has no configured timezone and the message does not include an explicit timezone, the bot must respond with an onboarding message requesting the user to set a timezone.

### 8.4 Feedback and User Mute Controls (MVP)

#### Feedback (Discord + Telegram)
Users MUST be able to submit feedback using:
- `/feedback <text>`

The bot MUST store the feedback as an internal event for later review.

#### Mute Controls (Discord + Telegram)
Users MUST be able to mute/unmute the bot for themselves:
- `/mute`
- `/unmute`

When a user is muted:
- Discord: the bot MUST NOT show the user conversion output (ephemeral conversion) when they click the button.
- Telegram: the bot MUST NOT send the user DM conversions, even if `/dm on` is enabled.

Muted users MUST be able to re-enable the bot using `/unmute`.


## 9. Output Formatting Rules

### 9.1 Time Display Format
The bot MUST mirror the sender’s time format when possible:
- If the detected time was written in 24-hour format (e.g. `17:45`), output MUST use 24-hour format.
- If the detected time was written in 12-hour format (e.g. `10am`), output MUST use 12-hour format.

### 9.2 Timezone Labels
Timezone labels in output MUST be displayed as city names (e.g. `Amsterdam`, `Yerevan`) rather than IANA strings.

### 9.3 Date Boundary Handling

If a weekday/date anchor was present in the message (e.g. `on Monday 10am`), the bot MUST include the resolved calendar date in output for BOTH the source and target timezones:
- `Mon, Feb 2 — 10:00 Amsterdam` → `Mon, Feb 2 — 14:00 Yerevan`

If timezone conversion changes the calendar date, the target output MUST reflect that:
- `Mon, Feb 2 — 23:30 Amsterdam` → `Tue, Feb 3 — 03:30 Yerevan`

Weekday Resolution Rules
If a message includes a weekday reference (e.g. `on Monday`), the bot MUST interpret it as the **next occurrence** of that weekday relative to the current date in the **source timezone**.

Modifiers MUST override the default interpretation. 
English:
- `next Monday` MUST refer to the Monday in the following week (skipping the next occurrence).
- `this Monday` MUST refer to the next occurrence of Monday within the current week context when applicable.
- `last Monday` MUST refer to the most recent occurrence of Monday in the past (the previous week’s Monday).
- `previous Monday` MUST behave the same as `last Monday`.
- `past Monday` MUST behave the same as `last Monday`.
Russian:
- `следующий понедельник` MUST refer to the Monday in the following week (skipping the next occurrence).
- `этот понедельник` MUST refer to the next occurrence of Monday within the current week context when applicable.
- `прошлый понедельник` MUST refer to the most recent occurrence of Monday in the past (the previous week’s Monday).
- `тот понедельник` MUST behave the same as `прошлый понедельник`.
- `понедельник на той неделе` MUST behave the same as `прошлый понедельник`.

### 9.4 Sorting Order (Telegram Public Replies)
When output includes multiple target timezones (Telegram group replies), the bot MUST order timezones by UTC offset (from lowest to highest) for the resolved datetime.

### 9.5 DST
All conversions MUST use IANA timezone rules and therefore correctly account for daylight-saving time transitions.

## 10. Multi-Time Mentions

### 10.1 Multiple Times in One Message
If a message contains multiple distinct time mentions, the bot MUST convert **all detected times**.

Examples:
- `10:30 or 14:00` → conversions are produced for both `10:30` and `14:00`
- `10am and 2pm` → conversions are produced for both `10am` and `2pm`

### 10.2 Time Ranges
If a message contains a time range, the bot MUST convert **both endpoints** of the range.

Examples:
- `10:00–11:00` → conversions are produced for both `10:00` and `11:00`
- `10:00-11:00` → conversions are produced for both `10:00` and `11:00`

Telegram Public Reply Aggregation:

If multiple times are detected within a single message, the bot MUST respond with a **single combined reply** that includes conversions for all detected times.

## 11. Rate Limiting & Spam Prevention (MVP)

- The bot MUST respond whenever a time mention is detected in a monitored location.
- The bot MUST ignore messages sent by bot accounts (including itself).
- The bot MUST respond only to newly sent messages (not edited messages).

- The bot processes newly sent messages only. If a message is edited and a time is added (or changed), the MVP bot ignores the edit and does not perform conversions. This is an intentional simplification to reduce complexity in the MVP.

Future consideration (not in MVP):
- Add optional support for responding to edited messages (e.g. when a user edits a message to add a time).


## 12. Data Storage & Privacy

### 12.1 Stored Data (MVP)
The bot MUST persist the minimum data required to function:

Per user (per platform):
- `user_id`
- `timezone` (IANA timezone string, e.g. `Europe/Amsterdam`)
- `dm_enabled` (Telegram only; boolean)
- `muted` (boolean)

The bot MUST store feedback submissions in persistent storage for later review.

Per group/server:
- Discord: monitored channel IDs (admin-configured)
- Telegram: monitoring enabled flag per group (set by admins via `/monitor_on`)
- Telegram: active timezone list overrides configured by admins (if any)

### 12.2 User Controls
Users MUST be able to change their timezone at any time using:
- Discord: `/tz set <timezone>`
- Telegram: `/tz set <timezone>`

Telegram users MUST be able to opt in/out of DM delivery at any time using:
- `/dm on`
- `/dm off`

### 12.3 Data Deletion
The bot MUST support a user command to delete their stored data:

- `/delete_me`
  - Removes the user's stored timezone and delivery preferences for that platform.
  - After deletion, if the user triggers a conversion without an explicit timezone in the message, the bot MUST request the user to set a timezone.

### 12.4 Retention (MVP)
No user activity timestamps are stored in MVP.

## 13. Error Handling
User-facing errors and fallbacks.

## 14. Observability
### 14.1 Logging
What events must be logged.

### 14.2 Metrics
## Metrics & Events (MVP)

The bot MUST record structured events in persistent storage (SQLite).
Events are used to measure activation, adoption, complaints, and shutdown behavior.

### Core Activation Events
Discord:
- discord_time_detected (bot posted a "Convert for me" button)
- discord_convert_button_clicked
- discord_conversion_success
- discord_conversion_onboarding_shown
- discord_conversion_blocked_user_muted

Telegram:
- telegram_time_detected
- telegram_public_reply_sent
- telegram_dm_sent
- telegram_dm_skipped_disabled
- telegram_dm_skipped_not_eligible
- telegram_dm_blocked_user_muted

### Monitoring/Shutdown Events
Discord:
- discord_monitor_channel_added
- discord_monitor_channel_removed

Telegram:
- telegram_monitor_enabled
- telegram_monitor_disabled

### User Preference Events
- user_timezone_set
- user_timezone_cleared
- user_muted
- user_unmuted
- user_deleted_data

### Feedback Events
- feedback_submitted

## 15. Acceptance Criteria
A checklist of must-have behaviors.

## 16. Non-Goals (Explicitly Out of Scope)
List what we are *not* doing in this version.
