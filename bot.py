"""Production entrypoint for the Telethon Telegram bot."""

from __future__ import annotations

import asyncio
import importlib
import logging
import pkgutil
from types import ModuleType

from telethon import TelegramClient

from config import ConfigError, config
from db import close_db, init_db

LOGGER_NAME = "telegram_bot"
logger = logging.getLogger(LOGGER_NAME)


def configure_logging() -> None:
    """Configure structured console logging."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _load_plugin(module: ModuleType, bot: TelegramClient) -> None:
    setup = getattr(module, "setup", None)
    if not callable(setup):
        logger.warning("Skipping plugin %s: missing setup(bot)", module.__name__)
        return
    setup(bot)
    logger.info("Loaded plugin: %s", module.__name__)


def load_plugins(bot: TelegramClient, package: str = "plugins") -> None:
    """Auto-import every module in the plugins package."""

    plugin_package = importlib.import_module(package)
    for module_info in pkgutil.iter_modules(plugin_package.__path__, f"{package}."):
        if module_info.ispkg:
            continue
        module = importlib.import_module(module_info.name)
        _load_plugin(module, bot)


async def main() -> None:
    configure_logging()
    logger.info("Starting Telegram bot")

    await init_db()
    bot = TelegramClient("bot", config.api_id, config.api_hash)
    load_plugins(bot)

    try:
        await bot.start(bot_token=config.bot_token)
        me = await bot.get_me()
        logger.info("Bot started as @%s (%s)", me.username, me.id)
        await bot.run_until_disconnected()
    finally:
        await bot.disconnect()
        await close_db()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ConfigError as exc:
        configure_logging()
        logger.critical("Configuration error: %s", exc)
        raise SystemExit(1) from exc
