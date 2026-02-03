from __future__ import annotations

import argparse
import logging
import sys

from .config import load_settings
from .discord_bot import DiscordBot, DiscordBotSettings
from .telegram_bot import TelegramBot, TelegramBotSettings

from dotenv import load_dotenv
load_dotenv()  

# ... остальной код

def _setup_logging(level: str) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Timetable Assistant Bot")
    parser.add_argument(
        "platform",
        choices=["discord", "telegram"],
        help="Which platform bot to run",
    )
    parser.add_argument(
        "--config",
        default="configuration.yaml",
        help="Path to configuration.yaml",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    args = parser.parse_args()

    _setup_logging(args.log_level)

    settings = load_settings(args.config)
    settings.validate_runtime(platform=args.platform)

    if args.platform == "telegram":
        # Validate only Telegram
        if not settings.telegram_bot_token:
            print("ERROR: TELEGRAM_BOT_TOKEN is missing. Set it in .env file.")
            sys.exit(1)

        bot = TelegramBot(
            TelegramBotSettings(
                token=settings.telegram_bot_token,
                sqlite_path=settings.storage.sqlite_path,
                max_active_timezones_public_reply=settings.platforms.telegram.limits.max_active_timezones_in_public_reply,
                enable_dm_delivery=settings.telegram.dm_delivery.enabled,
            )
        )

        bot.run()
        return

    if args.platform == "discord":
        # Validate only Discord
        if not settings.discord_bot_token:
            print("ERROR: DISCORD_BOT_TOKEN is missing. Set it in .env file.")
            sys.exit(1)

        bot = DiscordBot(
            DiscordBotSettings(
                token=settings.discord_bot_token,
                sqlite_path=settings.storage.sqlite_path,
            )
        )
        bot.run_bot()
        return


if __name__ == "__main__":
    main()