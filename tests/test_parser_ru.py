"""
Test Russian language parsing.

Tests the parser's ability to detect and extract Russian time expressions:
1. Russian time formats (в 10:30, в 10 утра/вечера/дня/ночи)
2. Standalone hours without qualifiers must be ignored (в 10)
3. Weekday inflections (в пятницу, во вторник)
4. Weekday modifiers (следующий понедельник, этот понедельник, прошлый понедельник)
5. Date anchors (сегодня, завтра)
6. Code blocks should be ignored in Russian messages too

All tests verify that:
- Correct language (RU) is detected
- Russian-specific time phrases are recognized
- Russian grammar rules are respected
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


def test_ru_detect_v_hhmm():
    parsed = parse_message("в 10:30 созвон")
    times = _get_times(parsed)

    assert parsed.language == Language.RU
    assert len(times) == 1
    assert times[0].kind == TimeMentionKind.TIME
    # Your parser keeps raw including "в 10:30"
    assert "10:30" in times[0].raw
    assert times[0].style == TimeStyle.H24


def test_ru_detect_v_h_qualifier():
    parsed = parse_message("в 10 утра созвон")
    times = _get_times(parsed)

    assert len(times) == 1
    assert times[0].kind == TimeMentionKind.TIME
    assert times[0].style == TimeStyle.H12


def test_ru_ignore_v_10_standalone_hour():
    parsed = parse_message("в 10 созвон")
    assert len(_get_times(parsed)) == 0


def test_ru_weekday_inflection_v_pyatницу():
    parsed = parse_message("в пятницу в 10:30")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.WEEKDAY
    assert anchor.weekday_index == 4
    assert anchor.modifier == WeekdayModifier.DEFAULT_NEXT


def test_ru_weekday_inflection_vo_vtornik():
    parsed = parse_message("во вторник в 22:30")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.WEEKDAY
    assert anchor.weekday_index == 1
    assert anchor.modifier == WeekdayModifier.DEFAULT_NEXT


def test_ru_modifier_sleduyushchiy_ponedelnik():
    parsed = parse_message("в следующий понедельник в 10:00")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.WEEKDAY
    assert anchor.weekday_index == 0
    assert anchor.modifier == WeekdayModifier.NEXT


def test_ru_modifier_etot_ponedelnik():
    parsed = parse_message("в этот понедельник в 10:00")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.WEEKDAY
    assert anchor.weekday_index == 0
    assert anchor.modifier == WeekdayModifier.THIS


def test_ru_modifier_proshliy_ponedelnik():
    parsed = parse_message("в прошлый понедельник в 10:00")
    anchor = _get_anchor(parsed)

    assert anchor is not None
    assert anchor.kind == DateAnchorKind.WEEKDAY
    assert anchor.weekday_index == 0
    assert anchor.modifier == WeekdayModifier.LAST


def test_ru_today_and_tomorrow():
    parsed_today = parse_message("сегодня в 10:30")
    parsed_tomorrow = parse_message("завтра в 10:30")

    assert _get_anchor(parsed_today).kind == DateAnchorKind.TODAY
    assert _get_anchor(parsed_tomorrow).kind == DateAnchorKind.TOMORROW


def test_ru_ignore_code_blocks():
    parsed = parse_message("`в 10:30`")
    assert len(_get_times(parsed)) == 0
