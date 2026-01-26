
"""
Test English language parsing.

Tests the parser's ability to detect and extract:
1. Time mentions (HH:MM, 10am, noon, midnight, time ranges)
2. Multiple times in one message
3. Explicit timezone mentions (city names, IANA strings)
4. Date anchors (today, tomorrow, weekdays with modifiers)
5. Ignore rules (version numbers, dates, ratings, currency, units, floats, code blocks)

All tests verify that:
- Correct language (EN) is detected
- Time formats are properly identified (12h vs 24h)
- Invalid patterns are ignored
"""

from __future__ import annotations

from src.models import (
    DateAnchorKind,
    Language,
    TimeMentionKind,
    TimeStyle,
    WeekdayModifier,
)
from src.parser import parse_message


def _get_times(parsed):
    assert hasattr(parsed, "times"), "ParseResult must have .times"
    return parsed.times


def _get_anchor(parsed):
    assert hasattr(parsed, "date_anchor"), "ParseResult must have .date_anchor"
    return parsed.date_anchor


def _get_tz(parsed):
    assert hasattr(parsed, "explicit_timezone"), "ParseResult must have .explicit_timezone"
    return parsed.explicit_timezone


def test_en_detect_hhmm_time():
    parsed = parse_message("see you 10:30")
    times = _get_times(parsed)

    assert parsed.language == Language.EN
    assert len(times) == 1
    assert times[0].kind == TimeMentionKind.TIME
    assert times[0].raw == "10:30"
    assert times[0].style == TimeStyle.H24


def test_en_detect_am_pm_no_minutes():
    parsed = parse_message("next call at 10am")
    times = _get_times(parsed)

    assert len(times) == 1
    assert times[0].kind == TimeMentionKind.TIME
    assert times[0].raw.lower() == "10am"
    assert times[0].style == TimeStyle.H12

def test_en_detect_hhmm_format():
    """HHhMM format like 22h30 should be detected."""
    parsed = parse_message("meeting at 22h30")
    times = _get_times(parsed)

    assert len(times) == 1
    assert times[0].kind == TimeMentionKind.TIME
    assert "22h30" in times[0].raw.lower() or "22:30" in times[0].raw
    assert times[0].style == TimeStyle.H24


def test_en_detect_hhmm_format_lowercase():
    """HHhMM format should work with lowercase h."""
    parsed = parse_message("call at 14h45")
    times = _get_times(parsed)

    assert len(times) == 1
    assert times[0].kind == TimeMentionKind.TIME

def test_en_detect_time_range():
    parsed = parse_message("meeting 10:00–11:00")
    times = _get_times(parsed)

    assert len(times) == 1
    assert times[0].kind == TimeMentionKind.RANGE
    assert "10:00" in times[0].raw
    assert "11:00" in times[0].raw


def test_en_detect_multiple_times():
    parsed = parse_message("either 10:30 or 14:00 works")
    times = _get_times(parsed)

    assert len(times) == 2
    assert times[0].kind == TimeMentionKind.TIME
    assert times[1].kind == TimeMentionKind.TIME


def test_en_detect_noon_midnight():
    parsed = parse_message("let's do noon or midnight")
    times = _get_times(parsed)

    assert len(times) == 2


def test_en_explicit_timezone_city_name():
    parsed = parse_message("see you at 10:00 Amsterdam")
    tz = _get_tz(parsed)

    assert tz is not None
    assert "amsterdam" in str(tz).lower()

def test_en_explicit_timezone_abbreviation_cet():
    """CET timezone abbreviation should be recognized."""
    parsed = parse_message("see you at 10:00 CET")
    tz = _get_tz(parsed)

    assert tz is not None
    assert "cet" in str(tz).lower()


def test_en_explicit_timezone_abbreviation_pst():
    """PST timezone abbreviation should be recognized."""
    parsed = parse_message("call at 10:00 PST")
    tz = _get_tz(parsed)

    assert tz is not None
    assert "pst" in str(tz).lower()


def test_en_explicit_timezone_abbreviation_eet():
    """EET timezone abbreviation should be recognized."""
    parsed = parse_message("meeting at 14:00 EET")
    tz = _get_tz(parsed)

    assert tz is not None
    assert "eet" in str(tz).lower()


def test_en_explicit_timezone_utc_offset_plus():
    """UTC offset with + should be recognized."""
    parsed = parse_message("call at 10:00 UTC+4")
    tz = _get_tz(parsed)

    assert tz is not None
    assert "utc" in str(tz).lower() or "+4" in str(tz) or "+04" in str(tz)


def test_en_explicit_timezone_utc_offset_minus():
    """UTC offset with minus should be recognized."""
    parsed = parse_message("meeting at 10:00 UTC-5")
    tz = _get_tz(parsed)

    assert tz is not None
    assert "utc" in str(tz).lower() or "-5" in str(tz)

def test_en_explicit_timezone_iana_string():
    """IANA timezone string should be recognized."""
    parsed = parse_message("call at 10:00 Europe/Amsterdam")
    tz = _get_tz(parsed)

    assert tz is not None
    assert "europe/amsterdam" in str(tz).lower()

def test_en_date_anchor_today():
    parsed = parse_message("today 10:00")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.TODAY


def test_en_date_anchor_tomorrow():
    parsed = parse_message("tomorrow at 10am")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.TOMORROW


def test_en_weekday_default_next_occurrence():
    parsed = parse_message("on Monday 10:00")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.WEEKDAY
    assert anchor.weekday_index == 0
    assert anchor.modifier == WeekdayModifier.DEFAULT_NEXT


def test_en_weekday_next_monday_modifier():
    parsed = parse_message("next Monday 10:00")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.WEEKDAY
    assert anchor.weekday_index == 0
    assert anchor.modifier == WeekdayModifier.NEXT


def test_en_weekday_this_monday_modifier():
    parsed = parse_message("this Monday 10:00")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.WEEKDAY
    assert anchor.weekday_index == 0
    assert anchor.modifier == WeekdayModifier.THIS


def test_en_weekday_last_monday_modifier():
    parsed = parse_message("last Monday 10:00")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.WEEKDAY
    assert anchor.weekday_index == 0
    assert anchor.modifier == WeekdayModifier.LAST


def test_ignore_version_numbers():
    parsed = parse_message("release v10.3.0 is out")
    assert len(_get_times(parsed)) == 0


def test_ignore_dates_like_10_11():
    parsed = parse_message("deadline is 10/11")
    assert len(_get_times(parsed)) == 0


def test_ignore_rating_like_10_10():
    parsed = parse_message("this is 10/10")
    assert len(_get_times(parsed)) == 0


def test_ignore_currency_and_units():
    parsed = parse_message("cost is 10$ and distance 10km")
    assert len(_get_times(parsed)) == 0


def test_ignore_decimal_float_numbers():
    parsed = parse_message("score was 5.836 yesterday")
    assert len(_get_times(parsed)) == 0


def test_ignore_inline_code_blocks():
    parsed = parse_message("`see you 10:30`")
    assert len(_get_times(parsed)) == 0


def test_ignore_multiline_code_blocks():
    parsed = parse_message(
        "```txt\n"
        "see you 10:30\n"
        "```"
    )
    assert len(_get_times(parsed)) == 0
