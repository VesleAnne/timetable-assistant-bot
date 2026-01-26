# 07 — Weekday Resolution Rules (Next/This/Last)

## Problem
Messages may include weekday references without a concrete date, e.g.:
- "on Monday at 10"
- "в пятницу в 10:30"

For a distributed team, conversions must be correct across timezones and DST.  
Therefore, weekday references must be resolved into an actual calendar date before conversion.

## MVP Rule (per spec)
If a message includes a weekday reference (e.g. `on Monday`, `в пятницу`), the bot MUST interpret it as the **next occurrence** of that weekday relative to the current date in the **source timezone**.

The "source timezone" is resolved using the priority order:
1. explicit timezone in the message
2. sender's configured timezone
3. if none -> onboarding, conversion not performed

## Modifiers (Override Default)
Modifiers override the default "next occurrence" behavior:

### English
- `next Monday` => Monday in the following week (skip the next occurrence)
- `this Monday` => the Monday in the current-week context when applicable
- `last Monday` => most recent Monday in the past
- `previous Monday` => same as `last Monday`
- `past Monday` => same as `last Monday`

### Russian
- `следующий понедельник` / `в следующую среду` => NEXT
- `этот понедельник` / `в эту пятницу` => THIS
- `прошлый понедельник` / `в прошлую пятницу` => LAST
- `тот понедельник` / `понедельник на той неделе` => LAST

## Practical Interpretation Notes
- Default weekday references are future-oriented and stable:
  - "в пятницу" on Thursday => tomorrow
  - "в пятницу" on Saturday => next week's Friday
- LAST modifier is always past-oriented and must resolve backward.

## Display Requirements
When a weekday/date anchor was present, the bot MUST display the resolved calendar date in output for BOTH source and target timezones:
- `Mon, Feb 2 — 10:00 Amsterdam` → `Mon, Feb 2 — 14:00 Yerevan`

If timezone conversion changes the calendar date, the target output MUST reflect that:
- `Mon, Feb 2 — 23:30 Amsterdam` → `Tue, Feb 3 — 03:30 Yerevan`

This ensures users see the concrete date the bot assumed.

## Implementation Plan
- Weekday resolution will happen in `conversion.py` / engine layer (not inside the parser).
- Parser extracts:
  - weekday index (Mon=0..Sun=6)
  - modifier (DEFAULT_NEXT / THIS / NEXT / LAST)
- Engine/conversion resolves into an actual date using the "source timezone" calendar date.