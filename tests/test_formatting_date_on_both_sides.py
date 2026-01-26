"""
Test date formatting when date anchor is present.

Tests output formatting rule from spec Section 9.3:
"If a weekday/date anchor was present in the message (e.g., 'on Monday 10am'),
the bot MUST include the resolved calendar date in output for BOTH the source
and target timezones."

Expected output format:
  Mon, Feb 2 — 10:00 Amsterdam → Mon, Feb 2 — 14:00 Yerevan

If timezone conversion changes the calendar date, target must reflect that:
  Mon, Feb 2 — 23:30 Amsterdam → Tue, Feb 3 — 03:30 Yerevan

This ensures users see the actual calendar date in their own timezone,
preventing confusion when meetings cross midnight boundaries.
"""
from __future__ import annotations

from datetime import datetime

from zoneinfo import ZoneInfo

from src.conversion import ConvertedEndpoint, ConvertedMention
from src.formatting import format_discord_ephemeral
from src.models import Language, TimeMention, TimeMentionKind, TimeStyle


def test_discord_formatting_date_on_both_sides_when_anchor_present():
    """
    If a weekday/date anchor was present, output must show resolved calendar date
    on BOTH sides:
      Mon, Feb 2 — 10:00 Amsterdam → Mon, Feb 2 — 14:00 Yerevan
    """
    # Mon, Feb 2, 2026 10:00 Amsterdam
    src_dt = datetime(2026, 2, 2, 10, 0, tzinfo=ZoneInfo("Europe/Amsterdam"))
    tgt_dt = src_dt.astimezone(ZoneInfo("Asia/Yerevan"))

    mention = TimeMention(
        kind=TimeMentionKind.TIME,
        raw="10:00",
        start=src_dt.time(),
        end=None,
        style=TimeStyle.H24,
    )

    cm = ConvertedMention(
        mention=mention,
        source_timezone="Europe/Amsterdam",
        source_datetimes=(src_dt,),
        target_datetimes={
            "Asia/Yerevan": (
                ConvertedEndpoint(
                    target_timezone="Asia/Yerevan",
                    target_datetime=tgt_dt,
                    day_offset=(tgt_dt.date() - src_dt.date()).days,
                ),
            )
        },
    )

    out = format_discord_ephemeral(
        converted=[cm],
        lang=Language.EN,
        source_label="Amsterdam",
        target_label="Yerevan",
        include_resolved_date=True,
    )

    # Date must appear on both sides
    assert "Mon, Feb 2" in out
    assert out.count("Mon, Feb 2") >= 2
    assert "10:00 Amsterdam" in out
    assert f"{tgt_dt.strftime('%H:%M')} Yerevan" in out

def test_formatting_mirrors_12h_time_style():
    """Output should use 12h format when source uses 12h."""
    # Mon, Feb 2, 2026 10:00 AM Amsterdam
    src_dt = datetime(2026, 2, 2, 10, 0, tzinfo=ZoneInfo("Europe/Amsterdam"))
    tgt_dt = src_dt.astimezone(ZoneInfo("Asia/Yerevan"))

    mention = TimeMention(
        kind=TimeMentionKind.TIME,
        raw="10am",
        start=src_dt.time(),
        end=None,
        style=TimeStyle.H12,  # 12-hour format
    )

    cm = ConvertedMention(
        mention=mention,
        source_timezone="Europe/Amsterdam",
        source_datetimes=(src_dt,),
        target_datetimes={
            "Asia/Yerevan": (
                ConvertedEndpoint(
                    target_timezone="Asia/Yerevan",
                    target_datetime=tgt_dt,
                    day_offset=(tgt_dt.date() - src_dt.date()).days,
                ),
            )
        },
    )

    out = format_discord_ephemeral(
        converted=[cm],
        lang=Language.EN,
        source_label="Amsterdam",
        target_label="Yerevan",
        include_resolved_date=True,
    )

    # Should use 12-hour format with AM/PM
    assert "am" in out.lower() or "pm" in out.lower()


def test_formatting_mirrors_24h_time_style():
    """Output should use 24h format when source uses 24h."""
    src_dt = datetime(2026, 2, 2, 14, 0, tzinfo=ZoneInfo("Europe/Amsterdam"))
    tgt_dt = src_dt.astimezone(ZoneInfo("Asia/Yerevan"))

    mention = TimeMention(
        kind=TimeMentionKind.TIME,
        raw="14:00",
        start=src_dt.time(),
        end=None,
        style=TimeStyle.H24,  # 24-hour format
    )

    cm = ConvertedMention(
        mention=mention,
        source_timezone="Europe/Amsterdam",
        source_datetimes=(src_dt,),
        target_datetimes={
            "Asia/Yerevan": (
                ConvertedEndpoint(
                    target_timezone="Asia/Yerevan",
                    target_datetime=tgt_dt,
                    day_offset=(tgt_dt.date() - src_dt.date()).days,
                ),
            )
        },
    )

    out = format_discord_ephemeral(
        converted=[cm],
        lang=Language.EN,
        source_label="Amsterdam",
        target_label="Yerevan",
        include_resolved_date=True,
    )

    # Should use 24-hour format (14:00, 17:00)
    # The presence of these times proves it's using 24h format, not 12h with AM/PM
    assert "14:00" in out or "14.00" in out
    assert "17:00" in out or "17.00" in out
    
def test_formatting_shows_day_rollover_marker():
    """Output should show day change when timezone conversion crosses midnight."""
    # Mon, Feb 2, 2026 23:30 Amsterdam
    src_dt = datetime(2026, 2, 2, 23, 30, tzinfo=ZoneInfo("Europe/Amsterdam"))
    # Converts to Tue, Feb 3 in Yerevan (UTC+4)
    tgt_dt = src_dt.astimezone(ZoneInfo("Asia/Yerevan"))

    mention = TimeMention(
        kind=TimeMentionKind.TIME,
        raw="23:30",
        start=src_dt.time(),
        end=None,
        style=TimeStyle.H24,
    )

    cm = ConvertedMention(
        mention=mention,
        source_timezone="Europe/Amsterdam",
        source_datetimes=(src_dt,),
        target_datetimes={
            "Asia/Yerevan": (
                ConvertedEndpoint(
                    target_timezone="Asia/Yerevan",
                    target_datetime=tgt_dt,
                    day_offset=(tgt_dt.date() - src_dt.date()).days,
                ),
            )
        },
    )

    out = format_discord_ephemeral(
        converted=[cm],
        lang=Language.EN,
        source_label="Amsterdam",
        target_label="Yerevan",
        include_resolved_date=True,
    )

    # Should show both dates
    assert "Feb 2" in out  # Source date
    assert "Feb 3" in out or "Tue" in out  # Target date (next day)