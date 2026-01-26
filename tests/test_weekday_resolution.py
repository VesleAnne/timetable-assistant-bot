"""
Test weekday date resolution logic.

Tests the conversion module's weekday resolution (spec Section 9.3):

Default behavior (no modifier):
- "on Monday" → next occurrence of Monday from today

Modifiers:
- "next Monday" → Monday in the following week (skips next occurrence)
- "this Monday" → Next occurrence within current week context
- "last/previous/past Monday" → Most recent Monday in the past

Examples from Thu Jan 22, 2026:
- "Monday" → Mon Jan 26 (next Monday, 4 days away)
- "next Monday" → Mon Feb 2 (following week, 11 days away)
- "last Monday" → Mon Jan 19 (previous week, 3 days ago)

This ensures weekday references are unambiguous and match user expectations.
"""

from __future__ import annotations

from datetime import date

from src.conversion import resolve_weekday_date
from src.models import WeekdayModifier


def test_weekday_default_next_occurrence():
    # Thu, 2026-01-22
    base = date(2026, 1, 22)

    # "on Monday" => next occurrence => 2026-01-26
    resolved = resolve_weekday_date(
        base_date=base,
        target_weekday=0,  # Monday
        modifier=WeekdayModifier.DEFAULT_NEXT,
    )
    assert resolved.isoformat() == "2026-01-26"


def test_weekday_next_skips_one_week():
    # Thu, 2026-01-22
    base = date(2026, 1, 22)

    # "next Monday" => skip next occurrence => 2026-02-02
    resolved = resolve_weekday_date(
        base_date=base,
        target_weekday=0,
        modifier=WeekdayModifier.NEXT,
    )
    assert resolved.isoformat() == "2026-02-02"


def test_weekday_this_behaves_like_default_next():
    # Thu, 2026-01-22
    base = date(2026, 1, 22)

    resolved = resolve_weekday_date(
        base_date=base,
        target_weekday=0,
        modifier=WeekdayModifier.THIS,
    )
    assert resolved.isoformat() == "2026-01-26"


def test_weekday_last_goes_back():
    # Thu, 2026-01-22
    base = date(2026, 1, 22)

    # "last Monday" => most recent Monday => 2026-01-19
    resolved = resolve_weekday_date(
        base_date=base,
        target_weekday=0,
        modifier=WeekdayModifier.LAST,
    )
    assert resolved.isoformat() == "2026-01-19"
