# 10 — Test Suite Foundation + Packaging Fixes

## Goal
The MVP must be easy to validate and safe to extend.  
This milestone focused on building a reliable test foundation that:

- runs fast (`< 1s`)
- does not require real Discord/Telegram connections
- tests core logic + storage behavior deterministically
- supports easy onboarding for a new developer

This directly supports evaluation criteria:
- **Does the project run? How easy is it to test?**
- **What is your test coverage?**
- **How clear and robust is the implementation?**

---

## What We Implemented

### 1) Added pytest-based test suite
Created the first set of tests in `tests/`, focusing on the core system boundaries:

#### Storage (SQLite)
✅ `tests/test_storage_active_timezones.py`

Coverage:
- Active timezone computation for Telegram groups:
  - Base = member timezones
  - Overrides add/remove behave correctly
  - Timezone expiration when members leave

#### Engine behavior
✅ `tests/test_engine_unknown_timezone.py`  
✅ `tests/test_engine_onboarding_missing_sender_timezone.py`  
✅ `tests/test_engine_ignores_bots_and_edits.py`

Coverage:
- Unknown explicit timezone (e.g. “Berlin”) → returns a “try Europe/Berlin” hint
- Missing sender timezone + no explicit timezone → onboarding message (`/tz set ...`)
- Ignores bot messages
- Ignores edited messages (MVP constraint)

All engine tests avoid relying on real parsing by monkeypatching `parse_message()`.

---

## Technical Fixes Discovered During Testing

### 1) Python packaging/import correctness
Initial failures showed that Python did not discover modules inside `src/` during tests.

✅ Fix:
- Added `src/__init__.py`
- Converted internal imports across `src/` to package-aware imports:

Example change:
```py
# before
from models import Something

# after
from .models import Something

```

## Result
The test suite runs successfully and quickly:
✅ 10 tests passing
runtime: ~0.2s