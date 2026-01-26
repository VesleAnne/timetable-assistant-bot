from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from typing import Optional

from .models import Language, TimeMention, TimeMentionKind, TimeStyle
from .conversion import ConvertedMention


EN_WEEKDAYS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
RU_WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

RU_MONTHS_SHORT = [
    "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек"
]
CITY_NAME_TRANSLATIONS = {
    "Amsterdam": "Амстердам",
    "Moscow": "Москва",
    "Lisbon": "Лиссабон",
    "Milan": "Милан",
    "Belgrade": "Белград",
    "Cyprus": "Кипр",
    "Limassol": "Лимассол",
    "Tbilisi": "Тбилиси",
    "Yerevan": "Ереван",
    "Vancouver": "Ванкувер",
    "Miami": "Майами",
    "New York": "Нью-Йорк",
    "London": "Лондон",
    "Paris": "Париж",
    "Berlin": "Берлин",
    "Tokyo": "Токио",
    "Sydney": "Сидней",
    "Los Angeles": "Лос-Анджелес",
    "Chicago": "Чикаго",
}



def _format_month_day_en(d: date) -> str:
    # Example: "Feb 2"
    return d.strftime("%b").strip() + f" {d.day}"


def _format_month_day_ru(d: date) -> str:
    # Example: "24 янв"
    month_idx = d.month - 1  # 0-indexed
    return f"{d.day} {RU_MONTHS_SHORT[month_idx]}"

def _format_date_with_weekday(d: date, lang: Language) -> str:
    wd = d.weekday()
    if lang == Language.RU:
        return f"{RU_WEEKDAYS_SHORT[wd]}, {_format_month_day_ru(d)}"
    return f"{EN_WEEKDAYS_SHORT[wd]}, {_format_month_day_en(d)}"

def _format_weekday_marker(d: date, lang: Language) -> str:
    wd = d.weekday()
    return RU_WEEKDAYS_SHORT[wd] if lang == Language.RU else EN_WEEKDAYS_SHORT[wd]

def _translate_city_name(city: str, lang: Language) -> str:
    """Translate city name to target language."""
    if lang == Language.RU and city in CITY_NAME_TRANSLATIONS:
        return CITY_NAME_TRANSLATIONS[city]
    return city

def _format_time_24h(t: time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


def _format_time_12h_en(t: time, drop_minutes_if_zero: bool = True) -> str:
    hour = t.hour
    minute = t.minute
    suffix = "am" if hour < 12 else "pm"

    hour12 = hour % 12
    if hour12 == 0:
        hour12 = 12

    if minute == 0 and drop_minutes_if_zero:
        return f"{hour12}{suffix}"
    return f"{hour12}:{minute:02d}{suffix}"


def _ru_qualifier_for_hour(hour_24: int) -> str:
    """
    Simple practical mapping (MVP):
    00-04 => ночи
    05-11 => утра
    12-16 => дня
    17-23 => вечера
    """
    if 0 <= hour_24 <= 4:
        return "ночи"
    if 5 <= hour_24 <= 11:
        return "утра"
    if 12 <= hour_24 <= 16:
        return "дня"
    return "вечера"


def _format_time_12h_ru(t: time, drop_minutes_if_zero: bool = True) -> str:
    """
    Russian 12h-ish output that mirrors "в 10 утра/вечера/дня/ночи".
    We keep a numeric time and attach qualifier.
    """
    hour24 = t.hour
    minute = t.minute

    # Render as hour in 1..12
    hour12 = hour24 % 12
    if hour12 == 0:
        hour12 = 12

    qualifier = _ru_qualifier_for_hour(hour24)

    if minute == 0 and drop_minutes_if_zero:
        return f"{hour12} {qualifier}"
    return f"{hour12}:{minute:02d} {qualifier}"


def format_time_by_style(
 t: time,
    style: TimeStyle,
    lang: Language,
    drop_minutes_if_zero: bool = True,
) -> str:
    # For Russian, always use 24h format regardless of input style
    # Russians don't typically use "1 дня" (1pm) - it sounds awkward
    if lang == Language.RU:
        return _format_time_24h(t)
    
    # For English, respect the original style
    if style == TimeStyle.H24:
        return _format_time_24h(t)
    
    # English 12h style
    return _format_time_12h_en(t, drop_minutes_if_zero=drop_minutes_if_zero)


def _utc_offset_seconds(dt: datetime) -> int:
    """
    Used for sorting Telegram outputs by UTC offset.
    """
    off = dt.utcoffset()
    if off is None:
        return 0
    return int(off.total_seconds())



@dataclass(frozen=True)
class DisplayTimezone:
    tz: str          # IANA timezone string
    label: str       # display label, e.g. "Amsterdam"




def format_discord_ephemeral(
    converted: list[ConvertedMention],
    lang: Language,
    source_label: str,
    target_label: str,
    include_resolved_date: bool,
) -> str:
    """
    Discord output is per clicking user: source -> user's timezone.
    """
    lines: list[str] = []

    for cm in converted:
        if cm.mention.kind == TimeMentionKind.TIME:
            src_dt = cm.source_datetimes[0]
            tgt_dt = cm.target_datetimes[next(iter(cm.target_datetimes.keys()))][0].target_datetime

            src_str = _format_one_side(
                dt=src_dt,
                label=source_label,
                mention=cm.mention,
                lang=lang,
                include_date=include_resolved_date,
                include_weekday_marker_if_no_date=True,
                force_weekday_marker=_should_force_weekday_marker(cm, include_resolved_date),
            )

            tgt_str = _format_one_side(
                dt=tgt_dt,
                label=target_label,
                mention=cm.mention,
                lang=lang,
                include_date=include_resolved_date,
                include_weekday_marker_if_no_date=True,
                force_weekday_marker=_should_force_weekday_marker(cm, include_resolved_date),
            )

            lines.append(f"{src_str} → {tgt_str}")

        else:
            # Range: convert both endpoints
            src_start, src_end = cm.source_datetimes
            tgt_start, tgt_end = cm.target_datetimes[next(iter(cm.target_datetimes.keys()))]
            tgt_start_dt = tgt_start.target_datetime
            tgt_end_dt = tgt_end.target_datetime

            src_start_str = _format_one_side(
                dt=src_start,
                label=source_label,
                mention=cm.mention,
                lang=lang,
                include_date=include_resolved_date,
                include_weekday_marker_if_no_date=True,
                force_weekday_marker=_should_force_weekday_marker(cm, include_resolved_date),
            )
            src_end_str = _format_time_only(src_end.time(), cm.mention.style, lang, cm.mention)

            tgt_start_str = _format_one_side(
                dt=tgt_start_dt,
                label=target_label,
                mention=cm.mention,
                lang=lang,
                include_date=include_resolved_date,
                include_weekday_marker_if_no_date=True,
                force_weekday_marker=_should_force_weekday_marker(cm, include_resolved_date),
            )
            tgt_end_str = _format_time_only(tgt_end_dt.time(), cm.mention.style, lang, cm.mention)

            lines.append(f"{src_start_str}–{src_end_str} → {tgt_start_str}–{tgt_end_str}")

    return "\n".join(lines)



def format_telegram_public_reply(
    converted: list[ConvertedMention],
    lang: Language,
    source_label: str,
    targets: list[DisplayTimezone],
    include_resolved_date: bool,
    sort_by_utc_offset: bool = True,
    max_targets: Optional[int] = None,

) -> str:
    """
    Telegram output: public reply containing conversions for active timezones.

    Output goal (single mention):
      - no anchor: 10:30 Amsterdam, 13:30 Yerevan, 11:30 Cyprus
      - with anchor: Mon, Feb 2 — 10:30 Amsterdam, Mon, Feb 2 — 14:30 Yerevan

    If dates differ across timezones (anchor present), we print date per timezone.
    """
    lines: list[str] = []

    # Optionally cap number of target timezones shown publicly
    if max_targets is not None and len(targets) > max_targets:
        targets = targets[:max_targets]

    for cm in converted:
        if cm.mention.kind == TimeMentionKind.TIME:
            line = _format_telegram_single_time(
                cm=cm,
                lang=lang,
                source_label=source_label,
                targets=targets,
                include_resolved_date=include_resolved_date,
                sort_by_utc_offset=sort_by_utc_offset,
            )
            lines.append(line)
        else:
            line = _format_telegram_range(
                cm=cm,
                lang=lang,
                source_label=source_label,
                targets=targets,
                include_resolved_date=include_resolved_date,
                sort_by_utc_offset=sort_by_utc_offset,
            )
            lines.append(line)

    return "\n".join(lines)



def _format_time_only(t: time, style: TimeStyle, lang: Language, mention: TimeMention) -> str:
    # For 12h mentions (like "10am"), we keep minutes hidden when zero.
    drop_minutes = True
    # If original raw contained minutes (e.g. "10:30"), keep minutes.
    if ":" in mention.raw or "h" in mention.raw.lower():
        drop_minutes = False
    return format_time_by_style(t, style, lang, drop_minutes_if_zero=drop_minutes)


def _format_one_side(
    dt: datetime,
    label: str,
    mention: TimeMention,
    lang: Language,
    include_date: bool,
    include_weekday_marker_if_no_date: bool,
    force_weekday_marker: bool,
) -> str:
    """
    Formats either source or target side.
    If include_date=True => "Mon, Feb 2 — 10:00 Amsterdam"
    Else => "23:30 Amsterdam (Wed)" or "03:30 (Thu) Yerevan"
    """
    t_str = _format_time_only(dt.time(), mention.style, lang, mention)
    translated_label = _translate_city_name(label, lang) 

    if include_date:
        d_str = _format_date_with_weekday(dt.date(), lang)
        return f"{d_str} — {t_str} {translated_label}"

    # No date anchor: optionally show weekday markers
    if include_weekday_marker_if_no_date and force_weekday_marker:
        wd = _format_weekday_marker(dt.date(), lang)
        return f"{t_str} {translated_label} ({wd})"

    return f"{t_str} {translated_label}"


def _should_force_weekday_marker(cm: ConvertedMention, include_resolved_date: bool) -> bool:
    """
    If no date anchor is present, we only show weekday markers when conversion
    crosses a day boundary for at least one target timezone.
    """
    if include_resolved_date:
        return False

    # Any day offset != 0 => marker needed
    for tz, endpoints in cm.target_datetimes.items():
        for ep in endpoints:
            if ep.day_offset != 0:
                return True
    return False


def _format_telegram_single_time(
    cm: ConvertedMention,
    lang: Language,
    source_label: str,
    targets: list[DisplayTimezone],
    include_resolved_date: bool,
    sort_by_utc_offset: bool,
) -> str:
    src_dt = cm.source_datetimes[0]

    # Build target outputs (dt + label)
    items: list[tuple[datetime, str]] = []
    for t in targets:
        if t.tz not in cm.target_datetimes:
            continue
        tgt_dt = cm.target_datetimes[t.tz][0].target_datetime
        items.append((tgt_dt, t.label))

    if sort_by_utc_offset:
        items.sort(key=lambda x: _utc_offset_seconds(x[0]))

    # Decide if anchor-date is shared across all outputs
    if include_resolved_date:
        all_dates = {src_dt.date()} | {dt.date() for dt, _ in items}
        if len(all_dates) == 1:
            # Same calendar date for everyone => print date prefix once
            date_prefix = _format_date_with_weekday(src_dt.date(), lang)
            parts = [f"{_format_time_only(src_dt.time(), cm.mention.style, lang, cm.mention)} {source_label}"]
            parts += [f"{_format_time_only(dt.time(), cm.mention.style, lang, cm.mention)} {lbl}" for dt, lbl in items]
            return f"{date_prefix} — " + ", ".join(parts)

        # Dates differ => print date per timezone explicitly
        parts = [
            f"{_format_date_with_weekday(src_dt.date(), lang)} — "
            f"{_format_time_only(src_dt.time(), cm.mention.style, lang, cm.mention)} {source_label}"
        ]
        for dt, lbl in items:
            parts.append(
                f"{_format_date_with_weekday(dt.date(), lang)} — "
                f"{_format_time_only(dt.time(), cm.mention.style, lang, cm.mention)} {lbl}"
            )
        return "; ".join(parts)

    # No anchor date: show weekday markers only if rollover exists
    force_marker = _should_force_weekday_marker(cm, include_resolved_date=False)

    src_part = _format_one_side(
        dt=src_dt,
        label=source_label,
        mention=cm.mention,
        lang=lang,
        include_date=False,
        include_weekday_marker_if_no_date=True,
        force_weekday_marker=force_marker,
    )

    target_parts: list[str] = []
    for dt, lbl in items:
        # For Telegram: we want target in similar style
        if force_marker:
            wd = _format_weekday_marker(dt.date(), lang)
            target_parts.append(f"{_format_time_only(dt.time(), cm.mention.style, lang, cm.mention)} ({wd}) {lbl}")
        else:
            target_parts.append(f"{_format_time_only(dt.time(), cm.mention.style, lang, cm.mention)} {lbl}")

    return ", ".join([src_part] + target_parts)


def _format_telegram_range(
    cm: ConvertedMention,
    lang: Language,
    source_label: str,
    targets: list[DisplayTimezone],
    include_resolved_date: bool,
    sort_by_utc_offset: bool,
) -> str:
    src_start, src_end = cm.source_datetimes

    # Build target endpoints
    items: list[tuple[datetime, datetime, str]] = []
    for t in targets:
        if t.tz not in cm.target_datetimes:
            continue
        tgt_start = cm.target_datetimes[t.tz][0].target_datetime
        tgt_end = cm.target_datetimes[t.tz][1].target_datetime
        items.append((tgt_start, tgt_end, t.label))

    if sort_by_utc_offset:
        items.sort(key=lambda x: _utc_offset_seconds(x[0]))

    # For ranges, we display start-end in each timezone.
    # Date anchor present => show date prefix logic similar to single time
    if include_resolved_date:
        all_dates = {src_start.date(), src_end.date()}
        for a, b, _ in items:
            all_dates.add(a.date())
            all_dates.add(b.date())

        # If everything stays on same date, print prefix once
        if len(all_dates) == 1:
            date_prefix = _format_date_with_weekday(src_start.date(), lang)

            src_part = (
                f"{_format_time_only(src_start.time(), cm.mention.style, lang, cm.mention)}–"
                f"{_format_time_only(src_end.time(), cm.mention.style, lang, cm.mention)} {source_label}"
            )
            parts = [src_part]
            for a, b, lbl in items:
                parts.append(
                    f"{_format_time_only(a.time(), cm.mention.style, lang, cm.mention)}–"
                    f"{_format_time_only(b.time(), cm.mention.style, lang, cm.mention)} {lbl}"
                )
            return f"{date_prefix} — " + ", ".join(parts)

        # Otherwise show date per timezone (can get long, but correct)
        parts = [
            f"{_format_date_with_weekday(src_start.date(), lang)} — "
            f"{_format_time_only(src_start.time(), cm.mention.style, lang, cm.mention)}–"
            f"{_format_time_only(src_end.time(), cm.mention.style, lang, cm.mention)} {source_label}"
        ]
        for a, b, lbl in items:
            parts.append(
                f"{_format_date_with_weekday(a.date(), lang)} — "
                f"{_format_time_only(a.time(), cm.mention.style, lang, cm.mention)}–"
                f"{_format_time_only(b.time(), cm.mention.style, lang, cm.mention)} {lbl}"
            )
        return "; ".join(parts)

    # No anchor date: show weekday markers only if rollover exists
    force_marker = _should_force_weekday_marker(cm, include_resolved_date=False)

    src_part = _format_one_side(
        dt=src_start,
        label=source_label,
        mention=cm.mention,
        lang=lang,
        include_date=False,
        include_weekday_marker_if_no_date=True,
        force_weekday_marker=force_marker,
    )
    src_end_part = _format_time_only(src_end.time(), cm.mention.style, lang, cm.mention)

    target_parts: list[str] = []
    for a, b, lbl in items:
        if force_marker:
            wd_a = _format_weekday_marker(a.date(), lang)
            wd_b = _format_weekday_marker(b.date(), lang)
            target_parts.append(
                f"{_format_time_only(a.time(), cm.mention.style, lang, cm.mention)} ({wd_a})–"
                f"{_format_time_only(b.time(), cm.mention.style, lang, cm.mention)} ({wd_b}) {lbl}"
            )
        else:
            target_parts.append(
                f"{_format_time_only(a.time(), cm.mention.style, lang, cm.mention)}–"
                f"{_format_time_only(b.time(), cm.mention.style, lang, cm.mention)} {lbl}"
            )

    return ", ".join([f"{src_part}–{src_end_part}"] + target_parts)
