"""
Test timezone conversion logic.

Tests the conversion.py module directly for:
- Basic time conversion between timezones
- Date anchor resolution (today, tomorrow, weekday)
- DST handling
- Time range conversion
- Multiple time conversion
"""

from datetime import date, time
from zoneinfo import ZoneInfo

import pytest

from src.conversion import resolve_anchor_date, convert_mentions, TimezoneConversionError
from src.models import DateAnchor, DateAnchorKind, TimeMention, TimeMentionKind, TimeStyle, WeekdayModifier


def test_convert_single_time_basic():
    """Convert a single time between two timezones."""
    mentions = [
        TimeMention(
            kind=TimeMentionKind.TIME,
            raw="10:30",
            start=time(10, 30),
            end=None,
            style=TimeStyle.H24,
        )
    ]
    
    result = convert_mentions(
        mentions=mentions,
        source_timezone="Europe/Amsterdam",
        target_timezones=["Asia/Yerevan"],
        resolved_date=None,
    )
    
    assert len(result) == 1
    assert result[0].mention.start == time(10, 30)
    
    # Amsterdam is typically UTC+1/+2, Yerevan is UTC+4
    # So 10:30 Amsterdam should be ~13:30 or 14:30 Yerevan (depending on DST)
    yerevan_times = result[0].target_datetimes["Asia/Yerevan"]
    assert len(yerevan_times) == 1
    converted_time = yerevan_times[0].target_datetime.time()
    assert converted_time.hour in [13, 14]  # Allow for DST variations


def test_convert_time_range_both_endpoints():
    """Convert both endpoints of a time range."""
    mentions = [
        TimeMention(
            kind=TimeMentionKind.RANGE,
            raw="10:00-11:00",
            start=time(10, 0),
            end=time(11, 0),
            style=TimeStyle.H24,
        )
    ]
    
    result = convert_mentions(
        mentions=mentions,
        source_timezone="Europe/Amsterdam",
        target_timezones=["America/Vancouver"],
        resolved_date=None,
    )
    
    # Should return ONE converted mention with both start and end
    assert len(result) == 1
    assert result[0].mention.kind == TimeMentionKind.RANGE
    assert result[0].mention.start == time(10, 0)
    assert result[0].mention.end == time(11, 0)
    
    # Should have conversions for both endpoints
    vancouver_times = result[0].target_datetimes["America/Vancouver"]
    assert len(vancouver_times) == 2  # Start and end converted

def test_convert_multiple_separate_times():
    """Convert multiple separate time mentions."""
    mentions = [
        TimeMention(
            kind=TimeMentionKind.TIME,
            raw="10:30",
            start=time(10, 30),
            end=None,
            style=TimeStyle.H24,
        ),
        TimeMention(
            kind=TimeMentionKind.TIME,
            raw="14:00",
            start=time(14, 0),
            end=None,
            style=TimeStyle.H24,
        ),
    ]
    
    result = convert_mentions(
        mentions=mentions,
        source_timezone="Europe/Amsterdam",
        target_timezones=["Asia/Yerevan"],
        resolved_date=None,
    )
    
    assert len(result) == 2
    assert result[0].mention.start == time(10, 30)
    assert result[1].mention.start == time(14, 0)


def test_convert_to_multiple_target_timezones():
    """Convert one time to multiple target timezones."""
    mentions = [
        TimeMention(
            kind=TimeMentionKind.TIME,
            raw="10:30",
            start=time(10, 30),
            end=None,
            style=TimeStyle.H24,
        )
    ]
    
    result = convert_mentions(
        mentions=mentions,
        source_timezone="Europe/Amsterdam",
        target_timezones=["Asia/Yerevan", "America/Vancouver", "Asia/Tbilisi"],
        resolved_date=None,
    )
    
    assert len(result) == 1
    # Should have conversions for all 3 target timezones
    assert "Asia/Yerevan" in result[0].target_datetimes
    assert "America/Vancouver" in result[0].target_datetimes
    assert "Asia/Tbilisi" in result[0].target_datetimes


def test_resolve_anchor_date_today():
    """Resolve 'today' anchor to current date in source timezone."""
    anchor = DateAnchor(kind=DateAnchorKind.TODAY)
    tz = "Europe/Amsterdam"
    
    resolved = resolve_anchor_date(anchor, tz)
    
    assert resolved is not None
    assert isinstance(resolved, date)


def test_resolve_anchor_date_tomorrow():
    """Resolve 'tomorrow' anchor to next day in source timezone."""
    anchor = DateAnchor(kind=DateAnchorKind.TOMORROW)
    tz = "Europe/Amsterdam"
    
    resolved = resolve_anchor_date(anchor, tz)
    
    assert resolved is not None
    assert isinstance(resolved, date)


def test_resolve_anchor_date_weekday():
    """Resolve weekday anchor to specific date."""
    anchor = DateAnchor(
        kind=DateAnchorKind.WEEKDAY,
        weekday_index=0,  # Monday
        modifier=WeekdayModifier.NEXT,
    )
    tz = "Europe/Amsterdam"
    
    resolved = resolve_anchor_date(anchor, tz)
    
    assert resolved is not None
    assert isinstance(resolved, date)
    # Should be a Monday
    assert resolved.weekday() == 0


def test_resolve_anchor_date_none_returns_none():
    """No anchor should return None."""
    resolved = resolve_anchor_date(None, "Europe/Amsterdam")
    assert resolved is None


def test_conversion_with_resolved_date():
    """Conversion with a specific date should include date in output."""
    mentions = [
        TimeMention(
            kind=TimeMentionKind.TIME,
            raw="10:30",
            start=time(10, 30),
            end=None,
            style=TimeStyle.H24,
        )
    ]
    
    test_date = date(2025, 1, 15)
    
    result = convert_mentions(
        mentions=mentions,
        source_timezone="Europe/Amsterdam",
        target_timezones=["Asia/Yerevan"],
        resolved_date=test_date,
    )
    
    assert len(result) == 1
    # Source datetime should have the resolved date
    assert result[0].source_datetimes[0].date() == test_date


def test_conversion_handles_date_boundary_crossing():
    """Converting late-night time should handle date rollover."""
    mentions = [
        TimeMention(
            kind=TimeMentionKind.TIME,
            raw="23:30",
            start=time(23, 30),
            end=None,
            style=TimeStyle.H24,
        )
    ]
    
    test_date = date(2025, 1, 15)
    
    result = convert_mentions(
        mentions=mentions,
        source_timezone="Europe/Amsterdam",
        target_timezones=["America/Vancouver"],  # Far behind
        resolved_date=test_date,
    )
    
    assert len(result) == 1
    # Vancouver is many hours behind, so should still be same day
    vancouver_dt = result[0].target_datetimes["America/Vancouver"][0].target_datetime
    # Could be same day or previous day depending on exact offset
    assert vancouver_dt.date() in [test_date, date(2025, 1, 14)]


def test_invalid_timezone_raises_error():
    """Invalid timezone should raise TimezoneConversionError."""
    mentions = [
        TimeMention(
            kind=TimeMentionKind.TIME,
            raw="10:30",
            start=time(10, 30),
            end=None,
            style=TimeStyle.H24,
        )
    ]
    
    with pytest.raises(TimezoneConversionError):
        convert_mentions(
            mentions=mentions,
            source_timezone="Invalid/Timezone",
            target_timezones=["Europe/Amsterdam"],
            resolved_date=None,
        )