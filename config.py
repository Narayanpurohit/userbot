"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Raised when a required configuration value is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Config:
    """Runtime configuration for the Telegram bot."""

    api_id: int
    api_hash: str
    bot_token: str
    mongodb_uri: str
    owner_id: int
    database_name: str = "TelegramBot"
    users_collection: str = "Users"


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ConfigError(f"Missing required environment variable: {name}")
    return value.strip()


def _require_int(name: str) -> int:
    value = _require(name)
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"Environment variable {name} must be an integer") from exc


def load_config() -> Config:
    """Load and validate all required environment variables."""

    return Config(
        api_id=_require_int("API_ID"),
        api_hash=_require("API_HASH"),
        bot_token=_require("BOT_TOKEN"),
        mongodb_uri=_require("MONGODB_URI"),
        owner_id=_require_int("OWNER_ID"),
    )


config = load_config()
