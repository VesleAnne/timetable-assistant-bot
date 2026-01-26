# Engine + Parser Tests (End-to-End + Fixes)

## Goal
Expand test coverage beyond unit tests by adding:
- parser tests (English + Russian)
- engine end-to-end Telegram tests
…and fix issues discovered during test-driven development.

---

## What we added

### ✅ Parser test suite
We created a parser test suite that validates:

**English parsing**
- `10:30` (24h)
- `10am` (12h)
- ranges like `10:00–11:00`
- multiple times in one message (`10:30 or 14:00`)
- noon / midnight keywords

**Russian parsing**
- `в 10:30` style detection
- `в 10 утра` with qualifier
- ignore ambiguous “в 10” (standalone hour without qualifier)

**Parser ignores false positives**
- version numbers: `v10.3.0`
- dates: `10/11`
- ratings: `10/10`
- currency / units: `10$`, `10km`
- decimal floats: `5.836`
- inline and multiline code blocks

✅ Result: parser tests now validate both detection and safe ignore rules.

---

### ✅ Engine Telegram end-to-end tests
We added a true “black-box” style test file:
`tests/test_engine_end_to_end.py`

It tests these Telegram flows:

1) **Basic conversion works**
- sender has timezone configured
- message contains time mention
- engine responds with conversions for active group timezones

2) **Onboarding when sender has no timezone**
- sender has no stored timezone
- message contains time mention
- engine responds with `/tz set Europe/Amsterdam`

3) **Range conversion**
- message contains a time range
- both endpoints are converted

4) **Weekday anchor produces resolved calendar date**
- freeze “now” for deterministic output
- `on Monday 10:00` resolves to a concrete date (example: `Mon, Feb 2`)

5) **Russian input → Russian-friendly output**
- RU message triggers RU parsing + conversion
- we validate output contains expected converted times

---

## Key implementation decisions

### 1) E2E tests call the real Engine method
Engine does not expose a generic `handle_telegram_message(...)`.

Instead, the correct Telegram entrypoint is:

- `Engine.telegram_build_public_reply(message_text, ctx, active_timezones, ...)`

So the E2E test file calls the engine directly using that method rather than trying to guess handler names.

This makes the E2E suite stable and aligned with the actual architecture.

---

### 2) Context dataclass construction is explicit and stable
We build a `TelegramMessageContext` with the fields the engine expects:

- `chat_id`
- `sender_id`
- `sender_is_bot`
- `is_edited`

This avoids fragile test assumptions and keeps context setup readable.

---

## Bugs found and fixed


### ✅ Bug: Engine E2E range test failed due to timezone false-positive
The test used:

- `meeting 10:00-11:00`

This produced an engine error:

- `"Could not resolve the timezone mentioned in the message."`

Why?
The engine supports timezone tokens like `+04:00` or `-11:00`.
So the substring `-11:00` inside `10:00-11:00` accidentally looked like a timezone offset.

✅ Fix: Mask time spans before extracting explicit timezone
In parse_message(), after extracting time spans, we create a masked version of the input where all detected time mention spans are replaced by spaces.

This prevents timezone regexes from accidentally matching substrings inside time mentions.

---

## Final result
✅ All tests passing:

- `166 passed`

Command:
```bash
python3 -m pytest -q
