from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformLimits(BaseModel):
    max_time_mentions_per_message: int = 10
    # Telegram-only (Discord doesn't use active timezone list in MVP)
    max_active_timezones_in_public_reply: Optional[int] = None


class DiscordPlatformConfig(BaseModel):
    enabled: bool = True
    limits: PlatformLimits = Field(default_factory=PlatformLimits)


class TelegramPlatformConfig(BaseModel):
    enabled: bool = True
    limits: PlatformLimits = Field(
        default_factory=lambda: PlatformLimits(max_active_timezones_in_public_reply=12)
    )


class PlatformsConfig(BaseModel):
    discord: DiscordPlatformConfig = Field(default_factory=DiscordPlatformConfig)
    telegram: TelegramPlatformConfig = Field(default_factory=TelegramPlatformConfig)


class BehaviorConfig(BaseModel):
    respond_to_edited_messages: bool = False  # for MVP 
    ignore_bots: bool = True


class I18nConfig(BaseModel):
    supported_languages: list[str] = Field(default_factory=lambda: ["en", "ru"])
    default_language: str = "en"
    reply_language: str = "match_message"  # must match triggering message


class TelegramDMDeliveryConfig(BaseModel):
    enabled: bool = True


class TelegramConfig(BaseModel):
    dm_delivery: TelegramDMDeliveryConfig = Field(default_factory=TelegramDMDeliveryConfig)


class StorageConfig(BaseModel):
    backend: str = "sqlite"
    sqlite_path: str = "./data/bot.db"


class MetricsConfig(BaseModel):
    enabled: bool = True
    store_events_in_db: bool = True


class FormattingConfig(BaseModel):
    mirror_sender_time_format: bool = True
    timezone_label_style: str = "city_name"
    telegram_sort_order: str = "utc_offset"
    show_day_markers_on_rollover: bool = True




class Settings(BaseSettings):
    """
    Loads configuration from:
    1) configuration.yaml (repo-level, non-secret)
    2) environment variables (deployment overrides, secrets)
    3) .env (local dev convenience)

    IMPORTANT:
    - environment variables override configuration.yaml
    - init kwargs override both
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    # --- Global runtime ---
    env: str = Field(default="dev", validation_alias="ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # --- YAML-driven project configuration ---
    platforms: PlatformsConfig = Field(default_factory=PlatformsConfig)
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
    i18n: I18nConfig = Field(default_factory=I18nConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    formatting: FormattingConfig = Field(default_factory=FormattingConfig)

    # --- Secrets (ENV only) ---
    discord_bot_token: Optional[str] = Field(default=None, validation_alias="DISCORD_BOT_TOKEN")
    telegram_bot_token: Optional[str] = Field(default=None, validation_alias="TELEGRAM_BOT_TOKEN")

    # Optional: override YAML path 
    config_path: str = Field(default="configuration.yaml", validation_alias="CONFIG_PATH")

    @field_validator("env")
    @classmethod
    def _validate_env(cls, v: str) -> str:
        allowed = {"dev", "prod", "test"}
        if v not in allowed:
            raise ValueError(f"ENV must be one of {sorted(allowed)}, got: {v}")
        return v

    def validate_runtime(self, platform: Optional[str] = None) -> None:
        """
        Fail fast if a platform is enabled but missing required secrets.
        
        Args:
            platform: If specified, only validate this platform (discord/telegram).
                    If None, validate all enabled platforms.
        """
        if platform is None or platform == "discord":
            if self.platforms.discord.enabled and not self.discord_bot_token:
                raise ValueError(
                    "Discord is enabled but DISCORD_BOT_TOKEN is missing. "
                    "Set DISCORD_BOT_TOKEN or disable Discord in configuration.yaml."
                )

        if platform is None or platform == "telegram":
            if self.platforms.telegram.enabled and not self.telegram_bot_token:
                raise ValueError(
                    "Telegram is enabled but TELEGRAM_BOT_TOKEN is missing. "
                    "Set TELEGRAM_BOT_TOKEN or disable Telegram in configuration.yaml."
                )

        if self.storage.backend != "sqlite":
            raise ValueError(
                f"Unsupported storage.backend={self.storage.backend!r} (MVP supports sqlite only)"
            )


def _load_yaml_config(path: str) -> Dict[str, Any]:
    """
    Load configuration.yaml content.
    If the file does not exist, return an empty dict (env + defaults still work).
    """
    p = Path(path)
    if not p.exists():
        return {}

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping/object at top-level")
    return data


def _yaml_settings_source(settings_cls: type[BaseSettings]) -> Dict[str, Any]:
    """
    Custom Settings source: reads configuration.yaml.
    This source is intentionally low priority (ENV overrides it).
    """
    # For pydantic-settings v2, sources receive the class, not instance
    # We need to get the config_path from class defaults
    cfg_path = "configuration.yaml"  # Use hardcoded default for now
    return _load_yaml_config(cfg_path)

# Custom source priority method for Settings class
@classmethod
def settings_customise_sources(
    cls,
    settings_cls,
    init_settings,
    env_settings,
    dotenv_settings,
    file_secret_settings,
):
    """
    Define the priority order for settings sources.
    Later sources override earlier ones: YAML < ENV < DOTENV < INIT
    """
    # Wrap the yaml source function to match expected signature
    def yaml_source():
        return _yaml_settings_source(settings_cls)
    
    return (
        yaml_source,        # lowest priority (base config from YAML)
        env_settings,       # deployment environment variables
        dotenv_settings,    # local .env file
        init_settings,      # test/manual overrides (highest priority)
    )

# Attach the method to the Settings class before it's used
Settings.settings_customise_sources = settings_customise_sources


def load_settings(config_path: str = "configuration.yaml") -> Settings:
    """
    Main entrypoint used by the app.
    Returns validated Settings with env > yaml override behavior.
    Note: Validation happens in main.py per-platform.
    """
    settings = Settings()
    # Don't validate here - main.py validates per-platform
    return settings
