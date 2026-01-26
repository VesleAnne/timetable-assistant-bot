from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum
from typing import Optional, Sequence, Union


class Platform(str, Enum):
    DISCORD = "discord"
    TELEGRAM = "telegram"


class Language(str, Enum):
    EN = "en"
    RU = "ru"


class TimeStyle(str, Enum):
    """
    Represents how the time was written by the user, used to mirror output formatting.
    """
    H24 = "24h"
    H12 = "12h"


class TimeMentionKind(str, Enum):
    TIME = "time"      # a single time mention
    RANGE = "range"    # a time range (start-end)


class DateAnchorKind(str, Enum):
    NONE = "none"
    TODAY = "today"
    TOMORROW = "tomorrow"
    WEEKDAY = "weekday"


class WeekdayModifier(str, Enum):
    """
    Controls weekday resolution behavior.
    """
    DEFAULT_NEXT = "default_next"
    THIS = "this"
    NEXT = "next"
    LAST = "last"


@dataclass(frozen=True)
class ExplicitTimezoneMention:
    """
    Represents a timezone explicitly present in the message text.
    Examples:
      - "Amsterdam"
      - "Europe/Amsterdam"
      - "UTC+4"
      - "+04:00"
      - "CET"
    """
    raw: str


@dataclass(frozen=True)
class DateAnchor:
    """
    Represents a date anchor extracted from message text.
    - today / сегодня
    - tomorrow / завтра
    - weekday references with modifiers
    """
    kind: DateAnchorKind
    # For WEEKDAY, weekday_index is 0=Mon ... 6=Sun
    weekday_index: Optional[int] = None
    modifier: WeekdayModifier = WeekdayModifier.DEFAULT_NEXT


@dataclass(frozen=True)
class TimeMention:
    """
    Represents one detected time mention.
    - raw: exact substring matched (useful for debugging + user-facing context)
    - style: whether the user wrote 12h vs 24h time format
    - kind: TIME or RANGE
    - start/end: as datetime.time objects (end optional)
    """
    raw: str
    style: TimeStyle
    kind: TimeMentionKind
    start: time
    end: Optional[time] = None


@dataclass(frozen=True)
class ParseResult:
    """
    Output of parsing a message.
    """
    language: Language
    times: Sequence[TimeMention]
    explicit_timezone: Optional[ExplicitTimezoneMention] = None
    date_anchor: Optional[DateAnchor] = None



@dataclass(frozen=True)
class SourceTimezoneResolution:
    """
    Represents the outcome of deciding what timezone the detected time refers to.
    """
    timezone: Optional[str]  # IANA timezone string if resolved
    reason: str              # e.g. "explicit", "sender_profile", "missing"


@dataclass(frozen=True)
class ConversionTarget:
    """
    Target timezone for output.
    timezone: IANA string
    label: display label (city name) to show to user
    """
    timezone: str
    label: str


@dataclass(frozen=True)
class ConversionRequest:
    """
    Request passed into the core engine after parsing and source timezone resolution.

    If resolved_date is None => time-of-day conversion without a specific calendar date.
    If resolved_date exists => full datetime conversion with correct DST/day rollover rules.
    """
    platform: Platform
    language: Language
    source_timezone: str
    targets: Sequence[ConversionTarget]
    times: Sequence[TimeMention]
    resolved_date: Optional[date] = None


@dataclass(frozen=True)
class ConvertedTime:
    """
    One conversion output item (for a specific timezone).

    day_marker is optional, e.g.:
      - "(Wed)" or "(Thu)"
      - or "(next day)" if date isn't anchored (time-of-day only)
    """
    timezone_label: str
    formatted_time: str
    day_marker: Optional[str] = None


@dataclass(frozen=True)
class ConversionBlock:
    """
    Represents one group of conversions corresponding to one detected time mention
    (or one endpoint in case of range conversion output formatting).
    """
    original_raw: str
    converted: Sequence[ConvertedTime]


@dataclass(frozen=True)
class EngineResponse:
    """
    Final user-facing response constructed by engine/formatting.
    The adapter only sends this text and does not alter it.
    """
    text: str
    language: Language


@dataclass(frozen=True)
class OnboardingResponse:
    """
    Response returned when we cannot convert due to missing timezone.
    """
    text: str
    language: Language


# Utility union for engine output
EngineResult = Union[EngineResponse, OnboardingResponse]