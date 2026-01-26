from __future__ import annotations

import re
from datetime import time
from typing import List, Optional, Sequence, Tuple

from .models import (
    DateAnchor,
    DateAnchorKind,
    ExplicitTimezoneMention,
    Language,
    ParseResult,
    TimeMention,
    TimeMentionKind,
    TimeStyle,
    WeekdayModifier,
)
from .timezones import KNOWN_CITY_NAMES

# English weekday names / abbreviations -> weekday index (Mon=0 ... Sun=6)
EN_WEEKDAYS = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}

RU_WEEKDAYS = {
    # Monday
    "пн": 0,
    "понедельник": 0,
    "понедельника": 0,
    # Tuesday
    "вт": 1,
    "вторник": 1,
    "вторника": 1,
    # Wednesday
    "ср": 2,
    "среда": 2,
    "среду": 2,
    # Thursday
    "чт": 3,
    "четверг": 3,
    "четверга": 3,
    # Friday
    "пт": 4,
    "пятница": 4,
    "пятницу": 4,
    # Saturday
    "сб": 5,
    "суббота": 5,
    "субботу": 5,
    # Sunday
    "вс": 6,
    "воскресенье": 6,
    "воскресенья": 6,
}

# Russian hour words mapping
RU_HOUR_WORDS = {
    # nominative
    "один": 1,
    "два": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    # genitive (used in "полпятого", "половина пятого")
    "первого": 1,
    "второго": 2,
    "третьего": 3,
    "четвертого": 4,
    "четвёртого": 4,
    "пятого": 5,
    "шестого": 6,
    "седьмого": 7,
    "восьмого": 8,
    "девятого": 9,
    "десятого": 10,
    "одиннадцатого": 11,
    "двенадцатого": 12,
    # Special cases
    "полдень": 12,
    "полночь": 0,
    "полуночь": 0,
}

# English hour words
EN_HOUR_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _normalize_russian_city(word: str) -> str:
    """
    Remove Russian case endings to match city base form.
    Examples:
      Амстердаму -> Амстердам
      Амстердамом -> Амстердам
      Москве -> Москв
    """
    # Common dative/instrumental/prepositional endings
    endings = ["ом", "ою", "ой", "у", "е", "ам", "ами", "ах"]
    word_lower = word.lower()
    
    for ending in endings:
        if word_lower.endswith(ending) and len(word) > len(ending) + 2:
            # Return with original capitalization pattern
            base = word[:-len(ending)]
            # Try to find exact match in KNOWN_CITY_NAMES
            for city in KNOWN_CITY_NAMES:
                if city.lower().startswith(base.lower()):
                    return city
            return base
    
    return word


# -----------------------------
# Regex patterns
# -----------------------------

# Code blocks:
# - Inline: `...`
# - Fenced: ```...```
INLINE_CODE_RE = re.compile(r"`[^`]*`", re.DOTALL)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)

# Time formats (single times)
# HH:MM, e.g. 10:30, 17:45
TIME_HHMM_RE = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")

# HHhMM, e.g. 22h30
TIME_HHhMM_RE = re.compile(r"\b([01]?\d|2[0-3])h([0-5]\d)\b", re.IGNORECASE)

# 12-hour forms:
# - 10am, 10pm
# - 10 am, 10 a.m.
TIME_AMPM_RE = re.compile(
    r"\b(1[0-2]|0?[1-9])\s*(a\.?m\.?|p\.?m\.?|am|pm)\b",
    re.IGNORECASE,
)

# 12-hour forms WITH minutes:
# - 10:30 AM, 10:30 A.M.
# - 10.30 AM, 10.30 A.M.
# NOTE: standalone "10.30" WITHOUT AM/PM is intentionally NOT supported.
TIME_HHMM_AMPM_RE = re.compile(
    r"\b(1[0-2]|0?[1-9])(?:[:.])([0-5]\d)\s*(a\.?m\.?|p\.?m\.?|am|pm)\b",
    re.IGNORECASE,
)

# Keywords:
NOON_RE = re.compile(r"\bnoon\b", re.IGNORECASE)
MIDNIGHT_RE = re.compile(r"\bmidnight\b", re.IGNORECASE)

# English natural language
EN_HALF_PAST_RE = re.compile(r"\bhalf\s+past\s+([a-z0-9]+)\b", re.IGNORECASE)
EN_QUARTER_PAST_RE = re.compile(r"\bquarter\s+past\s+([a-z0-9]+)\b", re.IGNORECASE)
EN_QUARTER_TO_RE = re.compile(r"\bquarter\s+to\s+([a-z0-9]+)\b", re.IGNORECASE)
EN_AND_HALF_RE = re.compile(r"\b([a-z0-9]+)\s+and\s+a\s+half\b", re.IGNORECASE)

# Russian:
# "в 10:30", "в 22:30"
RU_V_HHMM_RE = re.compile(r"\bв\s+([01]?\d|2[0-3]):([0-5]\d)\b", re.IGNORECASE)

# "в 10 утра/вечера/дня/ночи"
RU_V_H_QUALIFIER_RE = re.compile(
    r"\bв\s+(1[0-2]|0?[1-9])\s+(утра|вечера|дня|ночи)\b",
    re.IGNORECASE,
)

# "в три часа дня", "в пять утра", "в два часа"
RU_V_WORD_HOUR_QUALIFIER_RE = re.compile(
    r"\bв\s+(один|два|три|четыре|пять|шесть|семь|восемь|девять|десять|одиннадцать|двенадцать|полдень|полночь|полуночь)"
    r"(?:\s+час[аов]?)?"  # опционально "часа/часов"
    r"(?:\s+(утра|вечера|дня|ночи))?\b",
    re.IGNORECASE,
)

# "в час дня", "в час ночи"
RU_V_CHAS_QUALIFIER_RE = re.compile(
    r"\bв\s+час(?:\s+(утра|вечера|дня|ночи))?\b",
    re.IGNORECASE,
)

# Russian natural language
RU_HALF_PREFIX_RE = re.compile(r"\bпол([а-яё]+)\b", re.IGNORECASE)  # полпятого
RU_HALF_PHRASE_RE = re.compile(
    r"\b(?:в\s+)?половин[ау]\s+([а-яё]+)\b", re.IGNORECASE
)  # половина/половину пятого
RU_BEZ_RE = re.compile(
    r"\bбез\s+(пяти|5|четверти|15|\d{1,2})\s+([а-яё]+|\d{1,2})\b",
    re.IGNORECASE,
)
RU_HOUR_THIRTY_RE = re.compile(r"\b([а-яё]+|\d{1,2})\s+(тридцать|30)\b", re.IGNORECASE)

# Ignore "в 10" explicitly
RU_V_STANDALONE_HOUR_RE = re.compile(r"\bв\s+([01]?\d|2[0-3])\b", re.IGNORECASE)

# Range formats: 10:00–11:00 or 10:00-11:00
TIME_RANGE_RE = re.compile(
    r"\b([01]?\d|2[0-3]):([0-5]\d)\s*([–-])\s*([01]?\d|2[0-3]):([0-5]\d)\b"
)

# Explicit timezone expressions:
IANA_TZ_RE = re.compile(r"\b([A-Za-z]+/[A-Za-z_]+)\b")
UTC_OFFSET_RE = re.compile(r"\b(UTC[+-]\d{1,2}(?::\d{2})?|[+-]\d{2}:\d{2})\b", re.IGNORECASE)
TZ_ABBR_RE = re.compile(r"\b([A-Z]{2,4})\b")

# Date anchors:
TODAY_RE = re.compile(r"\b(today|сегодня)\b", re.IGNORECASE)
TOMORROW_RE = re.compile(r"\b(tomorrow|завтра)\b", re.IGNORECASE)

# English weekday references, optionally with modifiers:
EN_WEEKDAY_RE = re.compile(
    r"\b(?:(next|this|last|previous|past)\s+)?"
    r"(mon(day)?|tue(s(day)?)?|wed(nesday)?|thu(r(s(day)?)?)?|fri(day)?|sat(urday)?|sun(day)?)\b",
    re.IGNORECASE,
)

# Russian weekday references, optionally with modifiers:
RU_WEEKDAY_RE = re.compile(
    r"\b(?:в\s+|во\s+)?"
    r"(?:(следующ\w*|эт\w*|прошл\w*|тот|той)\s+)?"
    r"(пн|понедельник|понедельника|"
    r"вт|вторник|вторника|"
    r"ср|среда|среду|"
    r"чт|четверг|четверга|"
    r"пт|пятница|пятницу|"
    r"сб|суббота|субботу|"
    r"вс|воскресенье|воскресенья)"
    r"(?:\s+на\s+той\s+неделе)?\b",
    re.IGNORECASE,
)


# -----------------------------
# Helper functions
# -----------------------------

def _strip_code_blocks(text: str) -> str:
    """
    Replace inline and fenced code blocks with whitespace so we do not detect
    time mentions inside them.
    """
    text = FENCED_CODE_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    return text


def detect_language(text: str) -> Language:
    """
    Simple deterministic EN/RU detection:
    - if Cyrillic characters exist -> RU
    - else -> EN
    """
    if re.search(r"[А-Яа-яЁё]", text):
        return Language.RU
    return Language.EN


def _time_from_hhmm(h: str, m: str) -> time:
    return time(hour=int(h), minute=int(m))


def _time_from_hour_ampm(hour_str: str, ampm: str) -> time:
    """
    Convert 12-hour written hour + am/pm marker into 24-hour time.
    """
    hour = int(hour_str)
    ampm_norm = ampm.lower().replace(".", "")
    if ampm_norm in ("am", "a m"):
        if hour == 12:
            hour = 0
    elif ampm_norm in ("pm", "p m"):
        if hour != 12:
            hour += 12
    return time(hour=hour, minute=0)


def _time_from_hhmm_ampm(hour_str: str, minute_str: str, ampm: str) -> time:
    """
    Convert 12-hour written hour:minute + am/pm marker into 24-hour time.
    Supports both ':' and '.' separators via regex.
    """
    hour = int(hour_str)
    minute = int(minute_str)

    ampm_norm = ampm.lower().replace(".", "")
    if ampm_norm in ("am", "a m"):
        if hour == 12:
            hour = 0
    elif ampm_norm in ("pm", "p m"):
        if hour != 12:
            hour += 12

    return time(hour=hour, minute=minute)


def _time_from_ru_qualifier(hour_str: str, qualifier: str) -> time:
    """
    Convert Russian time-of-day qualifier into 24h time.
    Supports:
      утра  => AM
      дня   => PM (typically 12-17)
      вечера=> PM
      ночи  => AM (late night)
    """
    hour = int(hour_str)
    q = qualifier.lower()

    if q in ("утра", "ночи"):
        # AM
        if hour == 12:
            hour = 0
        return time(hour=hour, minute=0)

    # дня/вечера => PM
    if hour != 12:
        hour += 12
    return time(hour=hour, minute=0)


def _apply_ru_qualifier(hour: int, qualifier: str) -> int:
    """
    Apply Russian time-of-day qualifier to hour.
    Examples:
      (3, "дня") -> 15
      (5, "утра") -> 5
      (8, "вечера") -> 20
    """
    q = qualifier.lower()
    
    if q == "утра":  # Morning (00:00-11:59)
        if hour == 12:
            return 0  # "12 утра" -> midnight
        return hour
    elif q == "дня":  # Afternoon (12:00-17:59)
        if hour == 12:
            return 12  # noon
        return hour + 12
    elif q == "вечера":  # Evening (18:00-23:59)
        if hour == 12:
            return 0  # "12 вечера" is unusual, default to midnight
        return hour + 12
    elif q == "ночи":  # Night (00:00-05:59)
        if hour == 12:
            return 0  # midnight
        return hour
    else:
        return hour


def _parse_hour_token_en(token: str) -> Optional[int]:
    token = token.strip().lower()
    if token.isdigit():
        h = int(token)
        return h if 1 <= h <= 12 else None
    return EN_HOUR_WORDS.get(token)


def _parse_hour_token_ru(token: str) -> Optional[int]:
    token = token.strip().lower()
    if token.isdigit():
        h = int(token)
        return h if 1 <= h <= 12 else None
    return RU_HOUR_WORDS.get(token)


def _parse_hour_word_ru(word: str) -> Optional[int]:
    """
    Parse Russian hour word to number.
    Examples:
      "три" -> 3
      "пять" -> 5
      "полдень" -> 12
      "полночь" -> 0
    """
    if not word:
        return None
    
    word_lower = word.lower().strip()
    return RU_HOUR_WORDS.get(word_lower)


def _find_non_overlapping_spans(spans: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Utility to maintain non-overlapping match spans.
    """
    spans_sorted = sorted(spans, key=lambda x: (x[0], x[1]))
    result: List[Tuple[int, int]] = []
    last_end = -1
    for s, e in spans_sorted:
        if s >= last_end:
            result.append((s, e))
            last_end = e
    return result


def _span_overlaps(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    return not (a[1] <= b[0] or b[1] <= a[0])


def _extract_time_mentions(text: str) -> List[Tuple[Tuple[int, int], TimeMention]]:
    """
    Extract TimeMention objects with spans.
    Ranges are extracted first, then singles, avoiding overlap.
    """
    mentions: List[Tuple[Tuple[int, int], TimeMention]] = []

    # 1) Ranges (HH:MM–HH:MM only, per spec)
    for m in TIME_RANGE_RE.finditer(text):
        raw = m.group(0)
        start_t = _time_from_hhmm(m.group(1), m.group(2))
        end_t = _time_from_hhmm(m.group(4), m.group(5))
        span = (m.start(), m.end())

        mentions.append(
            (
                span,
                TimeMention(
                    raw=raw,
                    style=TimeStyle.H24,
                    kind=TimeMentionKind.RANGE,
                    start=start_t,
                    end=end_t,
                ),
            )
        )

    occupied_spans = [s for s, _ in mentions]

    def add_single(span: Tuple[int, int], tm: TimeMention) -> None:
        for occ in occupied_spans:
            if _span_overlaps(span, occ):
                return
        mentions.append((span, tm))
        occupied_spans.append(span)

    # 2) Russian "в HH:MM"
    for m in RU_V_HHMM_RE.finditer(text):
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H24,
                kind=TimeMentionKind.TIME,
                start=_time_from_hhmm(m.group(1), m.group(2)),
            ),
        )

    # 3) 12-hour WITH minutes (e.g., 10:30 AM, 10.30 A.M.)  <-- IMPORTANT: before HH:MM
    for m in TIME_HHMM_AMPM_RE.finditer(text):
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H12,
                kind=TimeMentionKind.TIME,
                start=_time_from_hhmm_ampm(m.group(1), m.group(2), m.group(3)),
            ),
        )

    # 4) HH:MM
    for m in TIME_HHMM_RE.finditer(text):
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H24,
                kind=TimeMentionKind.TIME,
                start=_time_from_hhmm(m.group(1), m.group(2)),
            ),
        )

    # 5) HHhMM
    for m in TIME_HHhMM_RE.finditer(text):
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H24,
                kind=TimeMentionKind.TIME,
                start=_time_from_hhmm(m.group(1), m.group(2)),
            ),
        )

    # 6) English am/pm (hour only)
    for m in TIME_AMPM_RE.finditer(text):
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H12,
                kind=TimeMentionKind.TIME,
                start=_time_from_hour_ampm(m.group(1), m.group(2)),
            ),
        )

    # 7) noon / midnight
    for m in NOON_RE.finditer(text):
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H12,
                kind=TimeMentionKind.TIME,
                start=time(hour=12, minute=0),
            ),
        )

    for m in MIDNIGHT_RE.finditer(text):
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H12,
                kind=TimeMentionKind.TIME,
                start=time(hour=0, minute=0),
            ),
        )

    # 8) Russian qualifier: "в 10 утра/вечера/дня/ночи"
    for m in RU_V_H_QUALIFIER_RE.finditer(text):
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H12,
                kind=TimeMentionKind.TIME,
                start=_time_from_ru_qualifier(m.group(1), m.group(2)),
            ),
        )

    # 8b) Russian text-based hour with qualifier: "в три часа дня", "в пять утра"
    for m in RU_V_WORD_HOUR_QUALIFIER_RE.finditer(text):
        hour_word = m.group(1)
        qualifier = m.group(2) if m.lastindex and m.lastindex >= 2 else None
        
        hour = _parse_hour_word_ru(hour_word)
        if hour is None:
            continue
        
        # Apply qualifier if present
        if qualifier:
            hour_24 = _apply_ru_qualifier(hour, qualifier.lower())
        else:
            # Without qualifier, assume current context (could be am or pm)
            # Default to am for hours 1-11, keep 12 as is, 0 for midnight
            hour_24 = hour
        
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H12 if qualifier else TimeStyle.H24,
                kind=TimeMentionKind.TIME,
                start=time(hour=hour_24 % 24, minute=0),
            ),
        )

    # 8c) "в час дня/ночи/утра/вечера"
    for m in RU_V_CHAS_QUALIFIER_RE.finditer(text):
        qualifier = m.group(1) if m.lastindex and m.lastindex >= 1 else None
        hour = 1
        
        if qualifier:
            hour_24 = _apply_ru_qualifier(hour, qualifier.lower())
        else:
            hour_24 = 1  # Default to 1:00 (01:00)
        
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(
                raw=raw,
                style=TimeStyle.H12 if qualifier else TimeStyle.H24,
                kind=TimeMentionKind.TIME,
                start=time(hour=hour_24 % 24, minute=0),
            ),
        )

    # 9) English natural-language times
    for m in EN_HALF_PAST_RE.finditer(text):
        hour = _parse_hour_token_en(m.group(1))
        if hour is None:
            continue
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(raw=raw, style=TimeStyle.H24, kind=TimeMentionKind.TIME, start=time(hour=hour % 24, minute=30)),
        )

    for m in EN_QUARTER_PAST_RE.finditer(text):
        hour = _parse_hour_token_en(m.group(1))
        if hour is None:
            continue
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(raw=raw, style=TimeStyle.H24, kind=TimeMentionKind.TIME, start=time(hour=hour % 24, minute=15)),
        )

    for m in EN_QUARTER_TO_RE.finditer(text):
        hour = _parse_hour_token_en(m.group(1))
        if hour is None:
            continue
        # quarter to ten = 09:45
        h = hour - 1
        if h == 0:
            h = 12
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(raw=raw, style=TimeStyle.H24, kind=TimeMentionKind.TIME, start=time(hour=h % 24, minute=45)),
        )

    for m in EN_AND_HALF_RE.finditer(text):
        hour = _parse_hour_token_en(m.group(1))
        if hour is None:
            continue
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(raw=raw, style=TimeStyle.H24, kind=TimeMentionKind.TIME, start=time(hour=hour % 24, minute=30)),
        )

    # 10) Russian natural-language times

    # полпятого -> 04:30 (i.e. half to five)
    for m in RU_HALF_PREFIX_RE.finditer(text):
        target_hour = _parse_hour_token_ru(m.group(1))
        if target_hour is None:
            continue
        hour = target_hour - 1
        if hour == 0:
            hour = 12
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(raw=raw, style=TimeStyle.H24, kind=TimeMentionKind.TIME, start=time(hour=hour % 24, minute=30)),
        )

    # половина пятого / в половину пятого -> 04:30
    for m in RU_HALF_PHRASE_RE.finditer(text):
        target_hour = _parse_hour_token_ru(m.group(1))
        if target_hour is None:
            continue
        hour = target_hour - 1
        if hour == 0:
            hour = 12
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(raw=raw, style=TimeStyle.H24, kind=TimeMentionKind.TIME, start=time(hour=hour % 24, minute=30)),
        )

    # без пяти пять / без 5 пять -> 04:55
    # без четверти пять -> 04:45
    for m in RU_BEZ_RE.finditer(text):
        mins_token = m.group(1).lower()
        hour_token = m.group(2).lower()

        target_hour = _parse_hour_token_ru(hour_token)
        if target_hour is None:
            continue

        if mins_token in ("четверти", "15"):
            delta = 15
        elif mins_token in ("пяти", "5"):
            delta = 5
        elif mins_token.isdigit():
            delta = int(mins_token)
        else:
            continue

        hour = target_hour - 1
        if hour == 0:
            hour = 12

        minute = 60 - delta
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(raw=raw, style=TimeStyle.H24, kind=TimeMentionKind.TIME, start=time(hour=hour % 24, minute=minute)),
        )

    # пять тридцать -> 05:30
    for m in RU_HOUR_THIRTY_RE.finditer(text):
        hour_token = m.group(1).lower()
        hour = _parse_hour_token_ru(hour_token)
        if hour is None:
            continue
        raw = m.group(0)
        span = (m.start(), m.end())
        add_single(
            span,
            TimeMention(raw=raw, style=TimeStyle.H24, kind=TimeMentionKind.TIME, start=time(hour=hour % 24, minute=30)),
        )

    # Sort by occurrence
    mentions.sort(key=lambda x: x[0][0])
    return mentions


def _extract_date_anchor(text: str) -> Optional[DateAnchor]:
    """
    Extract one date anchor. MVP spec requires support for:
    - today / сегодня
    - tomorrow / завтра
    - weekday references (EN/RU) with modifiers
    """
    # today/tomorrow have priority
    if TODAY_RE.search(text):
        return DateAnchor(kind=DateAnchorKind.TODAY)

    if TOMORROW_RE.search(text):
        return DateAnchor(kind=DateAnchorKind.TOMORROW)

    # Weekdays: English
    m_en = EN_WEEKDAY_RE.search(text)
    m_ru = RU_WEEKDAY_RE.search(text)

    # If both exist, pick the earliest occurrence in the message
    best = None
    if m_en:
        best = ("en", m_en.start(), m_en)
    if m_ru:
        if best is None or m_ru.start() < best[1]:
            best = ("ru", m_ru.start(), m_ru)

    if best is None:
        return None

    lang, _, m = best

    if lang == "en":
        modifier_raw = m.group(1)
        weekday_raw = m.group(2)
        weekday_index = EN_WEEKDAYS.get(weekday_raw.lower())
        if weekday_index is None:
            return None

        mod = WeekdayModifier.DEFAULT_NEXT
        if modifier_raw:
            mod_word = modifier_raw.lower()
            if mod_word == "next":
                mod = WeekdayModifier.NEXT
            elif mod_word == "this":
                mod = WeekdayModifier.THIS
            elif mod_word in ("last", "previous", "past"):
                mod = WeekdayModifier.LAST

        return DateAnchor(kind=DateAnchorKind.WEEKDAY, weekday_index=weekday_index, modifier=mod)

    # Russian
    modifier_raw = m.group(1)
    weekday_raw = m.group(2)
    weekday_index = RU_WEEKDAYS.get(weekday_raw.lower())
    if weekday_index is None:
        return None

    mod = WeekdayModifier.DEFAULT_NEXT

    # Special case: "на той неделе" is treated as LAST
    if re.search(r"\bна\s+той\s+неделе\b", m.group(0), re.IGNORECASE):
        mod = WeekdayModifier.LAST
        return DateAnchor(kind=DateAnchorKind.WEEKDAY, weekday_index=weekday_index, modifier=mod)

    if modifier_raw:
        word = modifier_raw.lower()

        if word.startswith("следующ"):
            mod = WeekdayModifier.NEXT
        elif word.startswith("эт"):
            mod = WeekdayModifier.THIS
        elif word.startswith("прошл"):
            mod = WeekdayModifier.LAST
        elif word in ("тот", "той"):
            mod = WeekdayModifier.LAST

    return DateAnchor(kind=DateAnchorKind.WEEKDAY, weekday_index=weekday_index, modifier=mod)


def _extract_explicit_timezone(text: str) -> Optional[ExplicitTimezoneMention]:
    """
    Extract one explicit timezone mention from text.
    Priority order:
    1) IANA timezone strings (Europe/Amsterdam)
    2) UTC offsets (UTC+4, +04:00)
    3) Known city names (Amsterdam, Yerevan, ...)
    4) Abbreviations (CET, EET, PST)
    5) FALLBACK: Any capitalized word that might be a city name
    
    The fallback (#5) ensures unknown cities are captured and can be validated
    by engine.py, which will return helpful error messages per spec Section 5.2.
    """
    # 1) IANA timezone strings (Europe/Amsterdam)
    m = IANA_TZ_RE.search(text)
    if m:
        return ExplicitTimezoneMention(raw=m.group(1))

    # 2) UTC offsets (UTC+4, +04:00)
    m = UTC_OFFSET_RE.search(text)
    if m:
        return ExplicitTimezoneMention(raw=m.group(1))

    # 3) Known cities (exact match as word boundary)
    for city in KNOWN_CITY_NAMES:
        pattern = r'\b' + re.escape(city) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            return ExplicitTimezoneMention(raw=city)

    # 4) Try normalizing Russian city names with case endings
    # Examples: "по Амстердаму", "в Москве"
    words = text.split()
    for word in words:
        # Remove punctuation
        clean_word = word.strip('.,!?;:')
        normalized = _normalize_russian_city(clean_word)
        if normalized in KNOWN_CITY_NAMES:
            return ExplicitTimezoneMention(raw=normalized)

    # 5) Abbreviations (CET/EET/PST etc.)
    m = TZ_ABBR_RE.search(text)
    if m:
        return ExplicitTimezoneMention(raw=m.group(1))

    # 6) FALLBACK: Capture any capitalized word that looks like a city/place name
    # This allows engine.py to validate and return helpful error messages
    # Pattern matches:
    # - Single capitalized word (Eindhoven, Rotterdam, etc.)
    # - Two-word names with underscore (New_York) - though IANA would catch this
    # Excludes common English words that shouldn't be timezone candidates
    COMMON_ENGLISH_WORDS = {
        'A', 'An', 'The', 'And', 'Or', 'But', 'In', 'On', 'At', 'To', 'For',
        'Of', 'With', 'By', 'From', 'As', 'Is', 'Was', 'Are', 'Were', 'Be',
        'Been', 'Being', 'Have', 'Has', 'Had', 'Do', 'Does', 'Did', 'Will',
        'Would', 'Could', 'Should', 'May', 'Might', 'Can', 'About', 'Into',
        'Through', 'After', 'Before', 'During', 'Since', 'Until', 'While',
        'Today', 'Tomorrow', 'Yesterday', 'Monday', 'Tuesday', 'Wednesday',
        'Thursday', 'Friday', 'Saturday', 'Sunday', 'Сегодня', 'Завтра',
        'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 
        'Воскресенье', 'Next', 'This', 'Last', 'Следующий', 'Этот', 'Прошлый'
    }
    
    # Pattern: word starting with capital letter, possibly with underscore
    POTENTIAL_CITY_RE = re.compile(r'\b([A-ZА-ЯЁ][a-zа-яё]+(?:_[A-ZА-ЯЁ][a-zа-яё]+)?)\b')
    
    for match in POTENTIAL_CITY_RE.finditer(text):
        candidate = match.group(1)
        # Skip common English/Russian words
        if candidate not in COMMON_ENGLISH_WORDS:
            return ExplicitTimezoneMention(raw=candidate)

    return None


def parse_message(message_text: str) -> ParseResult:
    """
    Parse a chat message into a structured ParseResult.

    Guarantees (MVP spec):
    - ignores content inside inline/fenced code blocks
    - detects supported time formats (EN/RU)
    - extracts optional explicit timezone mention (raw text)
    - extracts optional date anchor (today/tomorrow/weekday)
    - does NOT detect:
      - standalone "10.30" (dot-separated) without AM/PM
      - standalone "10"
      - standalone "в 10"
    """
    cleaned = _strip_code_blocks(message_text)
    language = detect_language(cleaned)

    # Extract time mentions
    time_mentions_with_spans = _extract_time_mentions(cleaned)
    times: List[TimeMention] = [tm for _, tm in time_mentions_with_spans]

    # Extract explicit timezone mention (raw)
    masked = list(cleaned)
    for (start, end), _tm in time_mentions_with_spans:
        for i in range(start, end):
            masked[i] = " "

    explicit_tz = _extract_explicit_timezone("".join(masked))

    # Extract date anchor
    date_anchor = _extract_date_anchor(cleaned)

    return ParseResult(
        language=language,
        times=times,
        explicit_timezone=explicit_tz,
        date_anchor=date_anchor,
    ) # type: ignore