# Timetable Assistant Bot — Acceptance Tests (v0.1)

A test is considered passing if the observable behavior matches the expectations below.

---

## 0. Test Setup

### 0.1 Users & Timezones
Create users with saved timezones:

- Alice — `Europe/Amsterdam`
- Bob — `Asia/Yerevan`
- Charlie — `America/Vancouver`
- Diana — no timezone set

### 0.2 Discord Setup
- Bot is installed in a Discord server.
- Admin configures at least one monitored channel using `/monitor add`.
- At least one other channel exists but is NOT monitored.

### 0.3 Telegram Setup
- Bot is added to a Telegram group.
- Admin enables monitoring in this group using `/monitor_on`.
- A second Telegram group exists where monitoring is NOT enabled.

### 0.4 Language Setup
- Team members write messages in English and Russian.
- Bot response language MUST match the message language.

---

## 1. Monitoring & Permissions

### 1.1 Discord: bot ignores messages outside monitored channels
**Given** a Discord channel that is NOT monitored  
**When** a user sends a message containing a valid time mention (e.g. `see you at 10:30`)  
**Then** the bot MUST NOT respond.

### 1.2 Discord: bot responds inside monitored channels
**Given** a Discord channel that IS monitored  
**When** a user sends a message containing a valid time mention (e.g. `see you at 10:30`)  
**Then** the bot MUST respond.

### 1.3 Discord: only admins can configure monitoring
**Given** a non-admin user  
**When** they attempt to run `/monitor add`  
**Then** the bot MUST NOT allow configuration to change (expected: permission error).

### 1.4 Telegram: bot responds only in monitored groups
**Given** a Telegram group where `/monitor_on` has been executed  
**When** a user sends a message containing a valid time mention  
**Then** the bot MUST respond.

**Given** a Telegram group where `/monitor_on` has NOT been executed  
**When** a user sends a message containing a valid time mention  
**Then** the bot MUST NOT respond.

### 1.5 Telegram: only admins can enable monitoring
**Given** a non-admin user in a Telegram group  
**When** they attempt to run `/monitor_on`  
**Then** monitoring MUST NOT become enabled (expected: permission error or denial).

---

## 2. Discord Reply Mode (Button + Ephemeral)

### 2.1 Discord: public message contains a "Convert for me" button
**Given** a monitored Discord channel  
**When** Alice sends: `see you at 10:00 Amsterdam`  
**Then** the bot MUST post a public message  
**And** that public message MUST include a **"Convert for me"** button.

### 2.2 Discord: clicking the button returns the user's local conversion
**Given** a monitored Discord channel  
**And** Alice sends: `see you at 10:00 Amsterdam`  
**And** the bot posts a public message with **"Convert for me"**  
**When** Bob clicks the button  
**Then** the bot MUST respond with an **ephemeral** message visible only to Bob  
**And** the ephemeral message MUST include the converted time in Bob’s configured timezone (`Asia/Yerevan`).

### 2.3 Discord: clicking the button with no timezone triggers onboarding
**Given** a monitored Discord channel  
**And** Alice sends: `see you at 10:00 Amsterdam`  
**When** Diana (no timezone configured) clicks the button  
**Then** the bot MUST respond with an **ephemeral onboarding** message  
**And** the onboarding message MUST instruct Diana to set a timezone via `/tz set <timezone>`.

---

## 3. Telegram Reply Mode (Public + Optional DM)

### 3.1 Telegram: bot replies publicly in the group
**Given** monitoring is enabled in a Telegram group  
**And** at least two participants have configured timezones (e.g. Amsterdam, Yerevan)  
**When** Alice sends: `see you at 10:00 Amsterdam`  
**Then** the bot MUST reply publicly in the group  
**And** the reply MUST include conversions for all **active timezones** of that group.

### 3.2 Telegram: combined reply for multiple times
**Given** monitoring is enabled in a Telegram group  
**When** Alice sends: `10:30 or 14:00 works`  
**Then** the bot MUST reply with a **single combined reply**  
**And** that reply MUST include conversions for both detected times (`10:30` and `14:00`).

### 3.3 Telegram: DM opt-in sends per-user conversion
**Given** monitoring is enabled in a Telegram group  
**And** Bob has enabled DMs via `/dm on`  
**And** Bob is eligible to receive bot DMs (has started a private chat with the bot at least once)  
**When** Alice sends: `see you at 10:00 Amsterdam`  
**Then** the bot MUST reply publicly in the group  
**And** the bot MAY send Bob a DM  
**And** if sent, the DM MUST include the converted time in Bob’s configured timezone.

### 3.4 Telegram: DM opt-out does not DM the user
**Given** monitoring is enabled in a Telegram group  
**And** Bob has disabled DMs via `/dm off`  
**When** Alice sends: `see you at 10:00 Amsterdam`  
**Then** the bot MUST NOT send Bob a DM.

---

## 4. Timezone Resolution

### 4.1 Explicit timezone in the message is always trusted
**Given** Alice’s configured timezone is `Europe/Amsterdam`  
**And** Bob’s configured timezone is `Asia/Yerevan`  
**When** Alice sends: `meet at 10:00 Yerevan`  
**Then** the bot MUST treat the source timezone as Yerevan  
**And** the conversion MUST reflect 10:00 in Yerevan time (not Amsterdam).

### 4.2 No timezone in message uses sender timezone
**Given** Alice’s configured timezone is `Europe/Amsterdam`  
**When** Alice sends: `meet at 10:00`  
**Then** the bot MUST interpret the time as `10:00 Europe/Amsterdam`.

### 4.3 No timezone in message and sender has no timezone → onboarding
**Given** Diana has no configured timezone  
**When** Diana sends: `meet at 10:00`  
**Then** the bot MUST respond with an onboarding message  
**And** MUST NOT attempt any conversions.

---

## 5. Supported Time Mentions (English)

### 5.1 Detect HH:MM
**When** a user sends: `see you 10:30`  
**Then** the bot MUST detect a time mention and respond.

### 5.2 Detect am/pm format
**When** a user sends: `see you at 10am`  
**Then** the bot MUST detect a time mention and respond.

### 5.3 Detect a.m./p.m. format
**When** a user sends: `see you at 10 a.m.`  
**Then** the bot MUST detect a time mention and respond.

### 5.4 Detect HHhMM
**When** a user sends: `see you at 22h30`  
**Then** the bot MUST detect a time mention and respond.

### 5.5 Detect noon and midnight
**When** a user sends: `see you at noon`  
**Then** the bot MUST detect a time mention and respond.

**When** a user sends: `see you at midnight`  
**Then** the bot MUST detect a time mention and respond.

### 5.6 Detect time ranges
**When** a user sends: `available 10:00–11:00`  
**Then** the bot MUST detect a time range  
**And** MUST convert both endpoints (`10:00` and `11:00`).

### 5.7 Detect multiple times in one message
**When** a user sends: `10:30 or 14:00`  
**Then** the bot MUST convert both times.

---

## 6. Supported Time Mentions (Russian)

### 6.1 Detect "в HH:MM"
**When** a user sends: `в 10:30`  
**Then** the bot MUST detect a time mention and respond.

**When** a user sends: `в 22:30`  
**Then** the bot MUST detect a time mention and respond.

### 6.2 Detect "в H утра/вечера/дня/ночи"
**When** a user sends: `в 10 утра`  
**Then** the bot MUST detect a time mention and respond.

**When** a user sends: `в 7 вечера`  
**Then** the bot MUST detect a time mention and respond.

### 6.3 Ignore "в 10"
**When** a user sends: `в 10`  
**Then** the bot MUST NOT detect a time mention  
**And** MUST NOT respond.

---

## 7. Ignored Patterns (False Positive Prevention)

### 7.1 Ignore software versions
**When** a user sends: `release v10.3.0`  
**Then** the bot MUST NOT respond.

### 7.2 Ignore numeric dates
**When** a user sends: `we met on 10/11`  
**Then** the bot MUST NOT respond.

### 7.3 Ignore ratings
**When** a user sends: `10/10 amazing`  
**Then** the bot MUST NOT respond.

### 7.4 Ignore units and currency
**When** a user sends: `ran 10km today`  
**Then** the bot MUST NOT respond.

**When** a user sends: `paid 10$`  
**Then** the bot MUST NOT respond.

### 7.5 Ignore float numbers
**When** a user sends: `result is 5.836`  
**Then** the bot MUST NOT respond.

### 7.6 Ignore code blocks
**When** a user sends a message containing a time inside inline code: `` `see you at 10:30` ``  
**Then** the bot MUST NOT respond.

## 8. Date Anchors & Weekdays 

### 8.1 English: today / tomorrow
**When** a user sends: tomorrow 10am
**Then** the bot MUST resolve the date as tomorrow in the source timezone
And MUST convert that datetime correctly across target timezones.

### 8.2 Russian: сегодня / завтра
**When** a user sends: завтра в 10:30
**Then** the bot MUST resolve the date as tomorrow in the source timezone
And MUST convert that datetime correctly across target timezones.

### 8.3 Weekday references resolve to concrete calendar dates
**When** a user sends: on Monday 10am
**Then** the bot MUST resolve "Monday" into a concrete calendar date
And MUST include that date in the output (e.g. Mon, Feb 2).

### 8.4 Modifiers override default weekday resolution (English)
**When** a user sends: next Monday 10am
**Then** the bot MUST interpret it as the Monday in the following week (skipping the next occurrence).
**When** a user sends: last Monday 10am
**Then** the bot MUST interpret it as the most recent Monday in the past.

### 8.5 Modifiers override default weekday resolution (Russian)
**When** a user sends: в следующий понедельник в 10:30
**Then** the bot MUST interpret it as the Monday in the following week (skipping the next occurrence).
**When** a user sends: в прошлый понедельник в 10:30
**Then** the bot MUST interpret it as the most recent Monday in the past.

## 9. Output Formatting Rules
### 9.1 Mirror sender time format
**When** the sender writes time in 24-hour format (e.g. 17:45)
**Then** the bot output MUST use 24-hour format for conversions.
**When** the sender writes time in 12-hour format (e.g. 10am)
**Then** the bot output MUST use 12-hour format for conversions.

### 9.2 City names in output
**When** the bot outputs timezone labels
**Then** the timezone labels MUST be shown as city names (e.g. Amsterdam, Yerevan).

### 9.3 Date boundary handling
**When** conversion crosses midnight
**Then** the bot output MUST include a day marker indicating the day change.
Example expected behavior:
23:30 Amsterdam (Wed) → 03:30 (Thu) Yerevan

### 9.4 Telegram public reply sorted by UTC offset
Given Telegram group has multiple active timezones
**When** a conversion is displayed publicly
**Then** the listed timezones MUST be ordered by UTC offset for the resolved datetime (lowest → highest).

## 10. Commands & Data Management
### 10.1 Set timezone (both platforms)
**When** a user runs /tz set Europe/Amsterdam
**Then** the bot MUST store the timezone
And /tz show MUST return Europe/Amsterdam.

### 10.2 Clear timezone (both platforms)
Given a user has a stored timezone
**When** they run /tz clear
**Then** /tz show MUST indicate no timezone is configured.

### 10.3 Telegram DM setting
**When** a Telegram user runs /dm on
**Then** /dm status MUST indicate DM delivery is enabled.
**When** a Telegram user runs /dm off
**Then** /dm status MUST indicate DM delivery is disabled.

### 10.4 Delete user data
Given a user has a stored timezone and (Telegram) DM preference
**When** he runs /delete_me
**Then** his stored timezone MUST be deleted
And his stored DM preference MUST be deleted
And future conversions requiring sender timezone MUST trigger onboarding until timezone is set again.

## 11. Edited Messages (MVP constraint)
### 11.1 Ignore edited messages
Given a user sends: see you
**When** the user edits the message to: see you at 10:30
**Then** the bot MUST NOT respond (MVP behavior).

## 12. Bot Messages & Self-Ignore
### 12.1 Ignore bot accounts
**When** another bot posts: meet at 10:30
**Then** the bot MUST NOT respond.

### 12.2 Ignore itself
**When** the bot posts its own messages
**Then** the bot MUST NOT respond to them.

## 13.
### Date anchor output includes date for both source and target

**Given** a user posts a message containing a weekday/date anchor (e.g. `on Monday 10am Amsterdam`)  
**When** the bot converts the time into another timezone (e.g. Yerevan)  
**Then** the bot MUST include the resolved calendar date in output for BOTH the source and the target timezone.

Example:
- Input: `on Monday 10:00 Amsterdam`
- Output MUST include:
  - `Mon, Feb 2 — 10:00 Amsterdam`
  - `Mon, Feb 2 — 14:00 Yerevan`

**And** if timezone conversion changes the calendar date  
**Then** the target output MUST reflect the new date.

Example:
- Input: `on Monday 23:30 Amsterdam`
- Output MUST include:
  - `Mon, Feb 2 — 23:30 Amsterdam`
  - `Tue, Feb 3 — 03:30 Yerevan`
