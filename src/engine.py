from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .models import (
    EngineResponse,
    EngineResult,
    Language,
    OnboardingResponse,
    Platform,
    SourceTimezoneResolution,
)
from .parser import parse_message
from .conversion import resolve_anchor_date, convert_mentions, TimezoneConversionError
from .formatting import (
    DisplayTimezone,
    format_discord_ephemeral,
    format_telegram_public_reply,
)
from .storage import SQLiteStorage
from .timezones import CITY_TO_IANA, ABBR_TO_IANA, tz_display_name

def resolve_explicit_timezone(raw: str) -> Optional[str]:
    """
    Resolve an explicit timezone mention into an IANA timezone string.

    Supported inputs (per spec):
    - city names (Amsterdam, Yerevan, ...) [curated list in MVP]
    - IANA timezone strings (Europe/Amsterdam)
    - timezone abbreviations (CET, PST, ...) [small curated list in MVP]
    - UTC offsets (UTC+4, +04:00) [extracted; support depends on conversion layer]
    """
    raw_clean = raw.strip()

    # 1) City mapping (curated MVP list)
    if raw_clean in CITY_TO_IANA:
        return CITY_TO_IANA[raw_clean]

    # 2) Abbreviation mapping (curated MVP list)
    upper = raw_clean.upper()
    if upper in ABBR_TO_IANA:
        return ABBR_TO_IANA[upper]

    # 3) IANA string "Area/City"
    if "/" in raw_clean and raw_clean[0].isalpha():
        return raw_clean

    # 4) UTC offsets (we keep raw and let conversion validate later)
    if raw_clean.upper().startswith("UTC") or raw_clean.startswith(("+", "-")):
        return raw_clean

    # Unknown / unsupported explicit timezone token
    return None


def tz_label_from_iana(tz: str, lang: Language = Language.EN) -> str:
    """
    Produce a "city name" label for output.
    Returns city name in the appropriate language.
    
    Example:
      Europe/Amsterdam, EN -> Amsterdam
      Europe/Amsterdam, RU -> Амстердам
    """
    return tz_display_name(tz, lang)


@dataclass(frozen=True)
class TelegramMessageContext:
    chat_id: str
    sender_id: str
    sender_is_bot: bool = False
    is_edited: bool = False


@dataclass(frozen=True)
class DiscordMessageContext:
    guild_id: str
    channel_id: str
    sender_id: str
    sender_is_bot: bool = False
    is_edited: bool = False




class Engine:
    """
    Core orchestration layer:
    - parse message
    - resolve source timezone
    - resolve date anchor -> concrete date
    - convert -> target tz list
    - format output

    Adapters remain thin and simply call these methods and send responses.
    """

    def __init__(self, storage: SQLiteStorage) -> None:
        self.storage = storage

    # -----------------------------
    # Shared steps
    # -----------------------------

    def resolve_source_timezone(
        self,
        platform: Platform,
        sender_id: str,
        explicit_tz_raw: Optional[str],
        language: Language,
    ) -> SourceTimezoneResolution:
        """
        Implements spec Section 6 priority:
        1) explicit timezone in message (always trust)
        2) sender configured timezone
        3) onboarding required

        Special case:
        - If explicit timezone exists but is unrecognized in MVP city/abbr lists,
          we return reason="explicit_unrecognized" and do NOT fall back to sender profile.
        """
        if explicit_tz_raw:
            resolved = resolve_explicit_timezone(explicit_tz_raw)
            if resolved:
                return SourceTimezoneResolution(timezone=resolved, reason="explicit")
            return SourceTimezoneResolution(timezone=None, reason="explicit_unrecognized")

        tz = self.storage.get_user_timezone(platform.value, sender_id)
        if tz:
            return SourceTimezoneResolution(timezone=tz, reason="sender_profile")

        return SourceTimezoneResolution(timezone=None, reason="missing")

    def onboarding_message(self, platform: Platform, language: Language) -> OnboardingResponse:
        if language == Language.RU:
            return OnboardingResponse(
                language=language,
                text="Я не знаю ваш часовой пояс. Установите его командой: /tz set Europe/Amsterdam",
            )
        return OnboardingResponse(
            language=language,
            text="I don't know your timezone yet. Set it with: /tz set Europe/Amsterdam",
        )

    def unknown_timezone_message(self, language: Language, raw_tz: str) -> EngineResponse:
        """
        Returned when the user explicitly mentioned a timezone token that the bot cannot resolve.
        We guide the user to the most reliable explicit format (IANA).
        """
        if language == Language.RU:
            return EngineResponse(
                language=language,
                text=(
                    f"Не удалось распознать часовой пояс **{raw_tz}**.\n"
                    f"Попробуйте формат IANA, например: `Europe/Berlin`."
                ),
            )
        return EngineResponse(
            language=language,
            text=(
                f"I couldn't recognize timezone **{raw_tz}**.\n"
                f"Try using an IANA timezone, e.g.: `Europe/Berlin`."
            ),
        )

    def telegram_build_public_reply(
        self,
        message_text: str,
        ctx: TelegramMessageContext,
        active_timezones: Sequence[str],
        max_active_timezones: Optional[int] = None,
    ) -> Optional[EngineResult]:
        """
        Telegram public reply flow:
        - caller decides monitoring enabled/disabled and passes active_timezones
        - returns EngineResponse if a time mention is detected and conversion possible
        - returns OnboardingResponse if missing source timezone
        - returns None if no time mentions or ignored conditions
        """
        if ctx.sender_is_bot:
            return None
        if ctx.is_edited:
            return None

        # Track membership best-effort
        self.storage.telegram_touch_member(ctx.chat_id, ctx.sender_id)

        parsed = parse_message(message_text)
        if not parsed.times:
            return None

        explicit_raw = parsed.explicit_timezone.raw if parsed.explicit_timezone else None

        src_res = self.resolve_source_timezone(
            platform=Platform.TELEGRAM,
            sender_id=ctx.sender_id,
            explicit_tz_raw=explicit_raw,
            language=parsed.language,
        )

        if src_res.reason == "explicit_unrecognized" and explicit_raw:
            return self.unknown_timezone_message(parsed.language, explicit_raw)

        if not src_res.timezone:
            # Onboarding, do not attempt conversion
            return self.onboarding_message(Platform.TELEGRAM, parsed.language)

        # Resolve date anchor (today/tomorrow/weekday) into a real date in source tz
        resolved_date = resolve_anchor_date(parsed.date_anchor, src_res.timezone)

        # Convert into active timezones
        target_ianas = list(dict.fromkeys(active_timezones))  # stable unique
        target_ianas = [t for t in target_ianas if t != src_res.timezone]

        # Build display target list with language-aware labels
        targets = [DisplayTimezone(tz=t, label=tz_label_from_iana(t, lang=parsed.language)) for t in target_ianas]

        try:
            converted = convert_mentions(
                mentions=list(parsed.times),
                source_timezone=src_res.timezone,
                target_timezones=[t.tz for t in targets],
                resolved_date=resolved_date,
            )
        except TimezoneConversionError:
            # If explicit tz was invalid (e.g. unsupported offset string), show a clear message
            if parsed.language == Language.RU:
                return EngineResponse(language=parsed.language, text="Не удалось распознать часовой пояс в сообщении.")
            return EngineResponse(language=parsed.language, text="Could not resolve the timezone mentioned in the message.")

        include_date = resolved_date is not None
        text = format_telegram_public_reply(
            converted=converted,
            lang=parsed.language,
            source_label=tz_label_from_iana(src_res.timezone, lang=parsed.language),
            targets=targets,
            include_resolved_date=include_date,
            sort_by_utc_offset=True,
            max_targets=max_active_timezones,
        )

        # Metrics hook (stored)
        self.storage.log_event(
            platform="telegram",
            event_name="telegram_public_reply_sent",
            scope_id=ctx.chat_id,
            user_id=ctx.sender_id,
            metadata={
                "times_detected": len(parsed.times),
                "source_tz_reason": src_res.reason,
                "resolved_date": bool(resolved_date),
                "active_timezones_count": len(active_timezones),
            },
        )

        return EngineResponse(language=parsed.language, text=text)

    def telegram_build_dm_for_user(
        self,
        message_text: str,
        ctx: TelegramMessageContext,
        recipient_user_id: str,
        recipient_timezone: str,
    ) -> Optional[EngineResult]:
        """
        Optional Telegram per-user DM conversion.
        Eligibility (started private chat) is enforced in adapter layer.
        This method checks user dm_enabled + muted.
        """
        # Respect user mute + dm setting
        if self.storage.get_user_muted("telegram", recipient_user_id):
            return None
        if not self.storage.get_user_dm_enabled("telegram", recipient_user_id):
            return None

        parsed = parse_message(message_text)
        if not parsed.times:
            return None

        explicit_raw = parsed.explicit_timezone.raw if parsed.explicit_timezone else None

        src_res = self.resolve_source_timezone(
            platform=Platform.TELEGRAM,
            sender_id=ctx.sender_id,
            explicit_tz_raw=explicit_raw,
            language=parsed.language,
        )

        if src_res.reason == "explicit_unrecognized" and explicit_raw:
            return self.unknown_timezone_message(parsed.language, explicit_raw)

        if not src_res.timezone:
            return self.onboarding_message(Platform.TELEGRAM, parsed.language)

        resolved_date = resolve_anchor_date(parsed.date_anchor, src_res.timezone)

        try:
            converted = convert_mentions(
                mentions=list(parsed.times),
                source_timezone=src_res.timezone,
                target_timezones=[recipient_timezone],
                resolved_date=resolved_date,
            )
        except TimezoneConversionError:
            return None

        include_date = resolved_date is not None
        text = format_discord_ephemeral(
            converted=converted,
            lang=parsed.language,
            source_label=tz_label_from_iana(src_res.timezone, lang=parsed.language),
            target_label=tz_label_from_iana(recipient_timezone, lang=parsed.language),
            include_resolved_date=include_date,
        )

        self.storage.log_event(
            platform="telegram",
            event_name="telegram_dm_sent",
            scope_id=ctx.chat_id,
            user_id=recipient_user_id,
            metadata={"from_sender_id": ctx.sender_id},
        )

        return EngineResponse(language=parsed.language, text=text)


    def discord_should_post_button_prompt(
        self,
        message_text: str,
        ctx: DiscordMessageContext,
    ) -> Optional[EngineResponse]:
        """
        Discord message flow:
        If time mentions are detected, we post a public message with a button.
        We do NOT post conversions publicly.
        """
        if ctx.sender_is_bot or ctx.is_edited:
            return None

        parsed = parse_message(message_text)
        if not parsed.times:
            return None

        # Button prompt text mirrors message language
        if parsed.language == Language.RU:
            text = "🕒 Найдено время. Нажмите кнопку, чтобы конвертировать для себя."
        else:
            text = "🕒 Time detected. Click the button to convert it for you."

        self.storage.log_event(
            platform="discord",
            event_name="discord_time_detected",
            scope_id=ctx.guild_id,
            channel_id=ctx.channel_id,
            user_id=ctx.sender_id,
            metadata={"times_detected": len(parsed.times)},
        )

        return EngineResponse(language=parsed.language, text=text)

    def discord_build_ephemeral_conversion_for_clicker(
        self,
        original_message_text: str,
        original_sender_id: str,
        clicking_user_id: str,
    ) -> Optional[EngineResult]:
        """
        Called when a user clicks "Convert for me".
        Converts based on original message content + clicker timezone.
        """
        # Respect user mute
        if self.storage.get_user_muted("discord", clicking_user_id):
            return None

        parsed = parse_message(original_message_text)
        if not parsed.times:
            return None

        explicit_raw = parsed.explicit_timezone.raw if parsed.explicit_timezone else None

        # Resolve source timezone from original message or original sender profile
        src_res = self.resolve_source_timezone(
            platform=Platform.DISCORD,
            sender_id=original_sender_id,
            explicit_tz_raw=explicit_raw,
            language=parsed.language,
        )

        if src_res.reason == "explicit_unrecognized" and explicit_raw:
            return self.unknown_timezone_message(parsed.language, explicit_raw)

        if not src_res.timezone:
            return self.onboarding_message(Platform.DISCORD, parsed.language)

        # Clicker must have timezone
        clicker_tz = self.storage.get_user_timezone("discord", clicking_user_id)
        if not clicker_tz:
            return self.onboarding_message(Platform.DISCORD, parsed.language)

        resolved_date = resolve_anchor_date(parsed.date_anchor, src_res.timezone)

        try:
            converted = convert_mentions(
                mentions=list(parsed.times),
                source_timezone=src_res.timezone,
                target_timezones=[clicker_tz],
                resolved_date=resolved_date,
            )
        except TimezoneConversionError:
            if parsed.language == Language.RU:
                return EngineResponse(language=parsed.language, text="Не удалось конвертировать время из-за часового пояса.")
            return EngineResponse(language=parsed.language, text="Could not convert time due to timezone resolution issue.")

        include_date = resolved_date is not None
        text = format_discord_ephemeral(
            converted=converted,
            lang=parsed.language,
            source_label=tz_label_from_iana(src_res.timezone, lang=parsed.language),
            target_label=tz_label_from_iana(clicker_tz, lang=parsed.language),
            include_resolved_date=include_date,
        )

        self.storage.log_event(
            platform="discord",
            event_name="discord_convert_button_clicked",
            user_id=clicking_user_id,
            metadata={"source_tz_reason": src_res.reason},
        )

        return EngineResponse(language=parsed.language, text=text)