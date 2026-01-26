from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .models import DateAnchor, DateAnchorKind, TimeMention, TimeMentionKind, WeekdayModifier


class TimezoneConversionError(ValueError):
    """Raised when timezone conversion cannot be performed (invalid timezone, etc.)."""


def get_zoneinfo(tz_name: str) -> ZoneInfo:
    """
    Load an IANA timezone as ZoneInfo.
    Raises a clear error if tz_name is invalid.
    """
    try:
        return ZoneInfo(tz_name)
    except Exception as e:  # ZoneInfoNotFoundError is not always available in typing contexts
        raise TimezoneConversionError(f"Invalid IANA timezone: {tz_name}") from e


def now_in_timezone(tz_name: str) -> datetime:
    tz = get_zoneinfo(tz_name)
    return datetime.now(tz=tz)


def to_local(dt_utc_or_local: datetime, tz_name: str) -> datetime:
    """
    Convert an aware datetime to the target timezone.
    """
    tz = get_zoneinfo(tz_name)
    if dt_utc_or_local.tzinfo is None:
        raise TimezoneConversionError("Datetime must be timezone-aware to convert")
    return dt_utc_or_local.astimezone(tz)


def day_delta(source_dt: datetime, target_dt: datetime) -> int:
    """
    Returns the integer date difference between target and source datetimes
    in their respective local calendars:
      target_date - source_date
    """
    return (target_dt.date() - source_dt.date()).days



def resolve_anchor_date(anchor: DateAnchor | None, source_tz: str, reference: datetime | None = None) -> date | None:
    """
    Resolve DateAnchor into a concrete date in the source timezone.

    Rules (per spec):
    - today => current date in source timezone
    - tomorrow => +1 day in source timezone
    - weekday => resolved based on "next occurrence" default + modifiers (THIS/NEXT/LAST)
    - if no anchor => None

    `reference` is injectable for tests (defaults to "now in source_tz").
    """
    if anchor is None or anchor.kind == DateAnchorKind.NONE:
        return None

    ref = reference or now_in_timezone(source_tz)
    base_date = ref.date()

    if anchor.kind == DateAnchorKind.TODAY:
        return base_date

    if anchor.kind == DateAnchorKind.TOMORROW:
        return base_date + timedelta(days=1)

    if anchor.kind == DateAnchorKind.WEEKDAY:
        if anchor.weekday_index is None:
            raise ValueError("WEEKDAY anchor requires weekday_index")

        return resolve_weekday_date(
            base_date=base_date,
            target_weekday=anchor.weekday_index,
            modifier=anchor.modifier,
        )

    return None


def resolve_weekday_date(base_date: date, target_weekday: int, modifier: WeekdayModifier) -> date:
    """
    Resolve a weekday reference into a concrete date.

    Definitions:
    - base_date.weekday(): Mon=0 ... Sun=6
    - DEFAULT_NEXT: next occurrence of the weekday relative to base_date
    - THIS: same as DEFAULT_NEXT for MVP (next occurrence in current-week context)
    - NEXT: skip the next occurrence (add 7 days)
    - LAST: most recent occurrence in the past (if same weekday, go back 7 days)

    This matches the spec and journal/07_weekday_resolution.md.
    """
    if target_weekday < 0 or target_weekday > 6:
        raise ValueError("target_weekday must be 0..6 (Mon..Sun)")

    current_wd = base_date.weekday()

    # Default forward delta: 0..6 (0 means "today" if same weekday)
    forward_delta = (target_weekday - current_wd) % 7

    if modifier in (WeekdayModifier.DEFAULT_NEXT, WeekdayModifier.THIS):
        return base_date + timedelta(days=forward_delta)

    if modifier == WeekdayModifier.NEXT:
        # Skip the next occurrence => ensure at least +7 days
        return base_date + timedelta(days=forward_delta + 7)

    if modifier == WeekdayModifier.LAST:
        # Most recent in the past:
        # backward delta: 0..6, where 0 means same weekday; but LAST must go to the previous week's weekday.
        backward_delta = (current_wd - target_weekday) % 7
        if backward_delta == 0:
            backward_delta = 7
        return base_date - timedelta(days=backward_delta)

    # Safe fallback
    return base_date + timedelta(days=forward_delta)



@dataclass(frozen=True)
class ConvertedEndpoint:
    """
    Represents one converted endpoint (a single time) into a target timezone.
    """
    target_timezone: str
    target_datetime: datetime
    day_offset: int  # target_date - source_date


@dataclass(frozen=True)
class ConvertedMention:
    """
    Represents a converted TimeMention (single time or range).

    For TIME:
      - source_datetimes has 1 element
      - target_datetimes maps each target tz to 1 ConvertedEndpoint

    For RANGE:
      - source_datetimes has 2 elements (start, end)
      - target_datetimes maps each target tz to 2 ConvertedEndpoints (start, end)
    """
    mention: TimeMention
    source_timezone: str
    source_datetimes: tuple[datetime, ...]
    target_datetimes: dict[str, tuple[ConvertedEndpoint, ...]]


def build_source_datetimes(
    mention: TimeMention,
    source_tz: str,
    resolved_date: date | None,
    reference: datetime | None = None,
) -> tuple[datetime, ...]:
    """
    Create timezone-aware datetime(s) for a mention in source timezone.

    If resolved_date is None, we anchor the time-of-day to "today" in source timezone
    for conversion purposes. This allows day rollover detection and offset calculations.
    (Output formatting will decide whether to show explicit dates or only markers.)
    """
    tz = get_zoneinfo(source_tz)
    ref = reference or now_in_timezone(source_tz)
    base_date = resolved_date or ref.date()

    def make_dt(d: date, t: time) -> datetime:
        return datetime.combine(d, t).replace(tzinfo=tz)

    if mention.kind == TimeMentionKind.TIME:
        return (make_dt(base_date, mention.start),)

    if mention.kind == TimeMentionKind.RANGE:
        if mention.end is None:
            raise ValueError("Range mention requires end time")

        start_dt = make_dt(base_date, mention.start)
        end_dt = make_dt(base_date, mention.end)

        # Robust behavior: if end < start, treat end as next day
        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)

        return (start_dt, end_dt)

    raise ValueError(f"Unknown TimeMentionKind: {mention.kind}")



def convert_mentions(
    mentions: list[TimeMention],
    source_timezone: str,
    target_timezones: list[str],
    resolved_date: date | None,
    reference: datetime | None = None,
) -> list[ConvertedMention]:
    """
    Convert a list of TimeMentions from source_timezone into all target_timezones.

    Inputs:
    - mentions: extracted from parser
    - source_timezone: IANA tz name
    - target_timezones: list of IANA tz names
    - resolved_date: concrete date if date anchor present, else None

    Output:
    - list of ConvertedMention objects
    """
    # Validate timezones early for clear errors
    _ = get_zoneinfo(source_timezone)
    for tz in target_timezones:
        _ = get_zoneinfo(tz)

    results: list[ConvertedMention] = []

    for mention in mentions:
        source_dts = build_source_datetimes(
            mention=mention,
            source_tz=source_timezone,
            resolved_date=resolved_date,
            reference=reference,
        )

        target_map: dict[str, tuple[ConvertedEndpoint, ...]] = {}

        for target_tz in target_timezones:
            converted_endpoints: list[ConvertedEndpoint] = []
            for src_dt in source_dts:
                tgt_dt = to_local(src_dt, target_tz)
                converted_endpoints.append(
                    ConvertedEndpoint(
                        target_timezone=target_tz,
                        target_datetime=tgt_dt,
                        day_offset=day_delta(src_dt, tgt_dt),
                    )
                )
            target_map[target_tz] = tuple(converted_endpoints)

        results.append(
            ConvertedMention(
                mention=mention,
                source_timezone=source_timezone,
                source_datetimes=tuple(source_dts),
                target_datetimes=target_map,
            )
        )

    return results
