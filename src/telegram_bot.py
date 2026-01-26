from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from .engine import Engine, TelegramMessageContext
from .models import Language, Platform
from .storage import SQLiteStorage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramBotSettings:
    token: str
    sqlite_path: str
    # public reply: cap number of target timezones shown
    max_active_timezones_public_reply: Optional[int] = 12
    # send optional per-user DM conversions (if user enabled /dm on)
    enable_dm_delivery: bool = True


class TelegramBot:
    """
    Telegram adapter (MVP).
    Uses python-telegram-bot v20+ (async).
    """

    def __init__(self, settings: TelegramBotSettings) -> None:
        self.settings = settings
        self.storage = SQLiteStorage(settings.sqlite_path)
        self.engine = Engine(self.storage)

    def run(self) -> None:
        """
        Starts the Telegram bot (long polling).
        Synchronous entry point - blocks until stopped.
        """
        try:
            from telegram import Update
            from telegram.constants import ChatType
            from telegram.ext import (
                Application,
                CommandHandler,
                ContextTypes,
                MessageHandler,
                filters,
            )
        except Exception as e:
            raise RuntimeError(
                "python-telegram-bot is not installed or incompatible. "
                "Install it with: pip install python-telegram-bot==20.*"
            ) from e

        app = Application.builder().token(self.settings.token).build()

        # Commands
        app.add_handler(CommandHandler("monitor_on", self._cmd_monitor_on))
        app.add_handler(CommandHandler("monitor_off", self._cmd_monitor_off))
        app.add_handler(CommandHandler("monitor_status", self._cmd_monitor_status))
        app.add_handler(CommandHandler("tz", self._cmd_tz))
        app.add_handler(CommandHandler("dm", self._cmd_dm))
        app.add_handler(CommandHandler("feedback", self._cmd_feedback))
        app.add_handler(CommandHandler("delete_me", self._cmd_delete_me))

        # Group messages (non-command)
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._on_text_message,
            )
        )

        # Detect member left events
        app.add_handler(
            MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self._on_left_chat_member)
        )

        logger.info("Telegram bot starting polling...")
        # Synchronous - handles event loop internally
        app.run_polling(allowed_updates=Update.ALL_TYPES)


    async def _is_admin(self, update, context) -> bool:
        """
        Admin check for group commands.
        """
        try:
            chat = update.effective_chat
            user = update.effective_user
            if not chat or not user:
                return False

            member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user.id)
            return member.status in ("administrator", "creator")
        except Exception:
            return False

    def _lang_from_text(self, text: str) -> Language:
        """
        Cheap heuristic: use parser later for real language detection.
        This is only for command UX.
        """
        # If contains Cyrillic -> RU
        for ch in text:
            if "А" <= ch <= "я" or ch == "ё" or ch == "Ё":
                return Language.RU
        return Language.EN

    def _reply_text_for_lang(self, lang: Language, en: str, ru: str) -> str:
        return ru if lang == Language.RU else en


    async def _cmd_monitor_on(self, update, context) -> None:
        lang = self._lang_from_text(update.effective_message.text or "")
        if not await self._is_admin(update, context):
            await update.effective_message.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en="Only admins can enable monitoring in this group.",
                    ru="Только администраторы могут включить мониторинг в этой группе.",
                )
            )
            return

        chat = update.effective_chat
        if not chat:
            return

        self.storage.telegram_set_monitoring(str(chat.id), True)
        await update.effective_message.reply_text(
            self._reply_text_for_lang(
                lang,
                en="✅ Monitoring enabled for this group.",
                ru="✅ Мониторинг включён для этой группы.",
            )
        )

    async def _cmd_monitor_off(self, update, context) -> None:
        lang = self._lang_from_text(update.effective_message.text or "")
        if not await self._is_admin(update, context):
            await update.effective_message.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en="Only admins can disable monitoring in this group.",
                    ru="Только администраторы могут выключить мониторинг в этой группе.",
                )
            )
            return

        chat = update.effective_chat
        if not chat:
            return

        self.storage.telegram_set_monitoring(str(chat.id), False)
        await update.effective_message.reply_text(
            self._reply_text_for_lang(
                lang,
                en="🛑 Monitoring disabled for this group.",
                ru="🛑 Мониторинг выключен для этой группы.",
            )
        )

    async def _cmd_monitor_status(self, update, context) -> None:
        lang = self._lang_from_text(update.effective_message.text or "")
        chat = update.effective_chat
        if not chat:
            return

        enabled = self.storage.telegram_get_monitoring(str(chat.id))
        await update.effective_message.reply_text(
            self._reply_text_for_lang(
                lang,
                en=f"Monitoring status: {'ON ✅' if enabled else 'OFF 🛑'}",
                ru=f"Статус мониторинга: {'ВКЛ ✅' if enabled else 'ВЫКЛ 🛑'}",
            )
        )


    async def _cmd_tz(self, update, context) -> None:
        """
        /tz set Europe/Amsterdam
        /tz show
        /tz clear
        """
        msg = update.effective_message
        if not msg:
            return

        text = msg.text or ""
        lang = self._lang_from_text(text)

        parts = text.strip().split(maxsplit=2)
        if len(parts) < 2:
            await msg.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en="Usage: /tz set <IANA timezone> | /tz show | /tz clear",
                    ru="Использование: /tz set <IANA часовой пояс> | /tz show | /tz clear",
                )
            )
            return

        action = parts[1].lower()
        user = update.effective_user
        if not user:
            return

        platform = Platform.TELEGRAM.value
        user_id = str(user.id)

        if action == "show":
            tz = self.storage.get_user_timezone(platform, user_id)
            if tz:
                await msg.reply_text(
                    self._reply_text_for_lang(
                        lang,
                        en=f"Your timezone: `{tz}`",
                        ru=f"Ваш часовой пояс: `{tz}`",
                    ),
                    parse_mode="Markdown",
                )
            else:
                await msg.reply_text(
                    self._reply_text_for_lang(
                        lang,
                        en="You don't have a timezone set yet. Use: /tz set Europe/Amsterdam",
                        ru="У вас ещё не задан часовой пояс. Используйте: /tz set Europe/Amsterdam",
                    )
                )
            return

        if action == "clear":
            self.storage.clear_user_timezone(platform, user_id)
            await msg.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en="✅ Your timezone was cleared.",
                    ru="✅ Ваш часовой пояс очищен.",
                )
            )
            return

        if action == "set":
            if len(parts) < 3:
                await msg.reply_text(
                    self._reply_text_for_lang(
                        lang,
                        en="Usage: /tz set <IANA timezone>, e.g. /tz set Europe/Amsterdam",
                        ru="Использование: /tz set <IANA часовой пояс>, например /tz set Europe/Amsterdam",
                    )
                )
                return

            tz_value = parts[2].strip()
            # Storage doesn't validate IANA strings; conversion will validate at runtime.
            self.storage.set_user_timezone(platform, user_id, tz_value)
            await msg.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en=f"✅ Timezone set to `{tz_value}`",
                    ru=f"✅ Часовой пояс установлен: `{tz_value}`",
                ),
                parse_mode="Markdown",
            )
            return

        await msg.reply_text(
            self._reply_text_for_lang(
                lang,
                en="Unknown /tz command. Use: /tz set | /tz show | /tz clear",
                ru="Неизвестная команда /tz. Используйте: /tz set | /tz show | /tz clear",
            )
        )



    async def _cmd_dm(self, update, context) -> None:
        """
        /dm on
        /dm off
        /dm status
        """
        msg = update.effective_message
        if not msg:
            return

        text = msg.text or ""
        lang = self._lang_from_text(text)
        parts = text.strip().split(maxsplit=2)

        if len(parts) < 2:
            await msg.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en="Usage: /dm on | /dm off | /dm status",
                    ru="Использование: /dm on | /dm off | /dm status",
                )
            )
            return

        action = parts[1].lower()
        user = update.effective_user
        if not user:
            return

        platform = Platform.TELEGRAM.value
        user_id = str(user.id)

        if action == "status":
            enabled = self.storage.get_user_dm_enabled(platform, user_id)
            await msg.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en=f"DM delivery: {'ON ✅' if enabled else 'OFF 🛑'}",
                    ru=f"Личные сообщения: {'ВКЛ ✅' if enabled else 'ВЫКЛ 🛑'}",
                )
            )
            return

        if action == "on":
            self.storage.set_user_dm_enabled(platform, user_id, True)
            await msg.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en="✅ DM delivery enabled. Note: you must start a private chat with the bot to receive DMs.",
                    ru="✅ Личные сообщения включены. Важно: нужно открыть личный чат с ботом, чтобы получать сообщения.",
                )
            )
            return

        if action == "off":
            self.storage.set_user_dm_enabled(platform, user_id, False)
            await msg.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en="🛑 DM delivery disabled.",
                    ru="🛑 Личные сообщения выключены.",
                )
            )
            return

        await msg.reply_text(
            self._reply_text_for_lang(
                lang,
                en="Unknown /dm command. Use: /dm on | /dm off | /dm status",
                ru="Неизвестная команда /dm. Используйте: /dm on | /dm off | /dm status",
            )
        )


    async def _cmd_feedback(self, update, context) -> None:
        msg = update.effective_message
        if not msg:
            return

        text = msg.text or ""
        lang = self._lang_from_text(text)

        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await msg.reply_text(
                self._reply_text_for_lang(
                    lang,
                    en="Usage: /feedback <your message>",
                    ru="Использование: /feedback <ваше сообщение>",
                )
            )
            return

        feedback_text = parts[1].strip()
        user = update.effective_user
        chat = update.effective_chat
        if not user:
            return

        self.storage.save_feedback(
            platform="telegram",
            user_id=str(user.id),
            text=feedback_text,
            scope_id=str(chat.id) if chat else None,
        )

        await msg.reply_text(
            self._reply_text_for_lang(
                lang,
                en="✅ Thanks! Your feedback was saved.",
                ru="✅ Спасибо! Ваш отзыв сохранён.",
            )
        )

    async def _cmd_delete_me(self, update, context) -> None:
        msg = update.effective_message
        if not msg:
            return

        text = msg.text or ""
        lang = self._lang_from_text(text)

        user = update.effective_user
        if not user:
            return

        self.storage.delete_user_data("telegram", str(user.id))
        await msg.reply_text(
            self._reply_text_for_lang(
                lang,
                en="✅ Your data has been deleted.",
                ru="✅ Ваши данные удалены.",
            )
        )

    async def _on_left_chat_member(self, update, context) -> None:
        """
        Best-effort cleanup: remove a member from membership tracking.
        """
        msg = update.effective_message
        chat = update.effective_chat
        if not msg or not chat:
            return

        left = msg.left_chat_member
        if not left:
            return

        self.storage.telegram_remove_member(str(chat.id), str(left.id))

    async def _on_text_message(self, update, context) -> None:
        """
        Main message handler (group chat only):
        - only reacts if monitoring enabled
        - parses time mentions and replies publicly
        - optionally sends per-user DMs (opt-in)
        """
        msg = update.effective_message
        chat = update.effective_chat
        user = update.effective_user
        if not msg or not chat or not user:
            return

        # Ignore bot messages
        if user.is_bot:
            return

        chat_id = str(chat.id)
        sender_id = str(user.id)

        # Only act if group monitoring enabled
        if not self.storage.telegram_get_monitoring(chat_id):
            return

        # Track member
        self.storage.telegram_touch_member(chat_id, sender_id)

        ctx = TelegramMessageContext(
            chat_id=chat_id,
            sender_id=sender_id,
            sender_is_bot=user.is_bot,
            is_edited=False,  # MVP: we ignore edited updates; this handler is for new text messages
        )

        active_tzs = sorted(list(self.storage.telegram_get_active_timezones(chat_id)))

        result = self.engine.telegram_build_public_reply(
            message_text=msg.text or "",
            ctx=ctx,
            active_timezones=active_tzs,
            max_active_timezones=self.settings.max_active_timezones_public_reply,
        )

        if result is None:
            return

        # Send public reply
        try:
            await msg.reply_text(result.text)
        except Exception as e:
            logger.exception("Failed to send Telegram public reply: %s", e)
            return

        # Optional DM delivery (best-effort)
        if not self.settings.enable_dm_delivery:
            return

        # Send DMs to members who opted in and have a timezone set
        # Telegram limitation: user must start a private chat with bot -> sending might fail. We ignore failures.
        members = self.storage.telegram_list_members(chat_id)
        for member_id in members:
            # Do not DM the sender for now (optional; can be changed later)
            if member_id == sender_id:
                continue

            tz = self.storage.get_user_timezone("telegram", member_id)
            if not tz:
                continue

            dm_result = self.engine.telegram_build_dm_for_user(
                message_text=msg.text or "",
                ctx=ctx,
                recipient_user_id=member_id,
                recipient_timezone=tz,
            )

            if dm_result is None:
                continue

            try:
                await context.bot.send_message(chat_id=int(member_id), text=dm_result.text)
            except Exception:
                # Most common reasons:
                # - bot was never started in private chat
                # - user blocked bot
                # We ignore in MVP.
                continue
