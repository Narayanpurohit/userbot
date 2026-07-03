"""/start command plugin."""

from __future__ import annotations

import logging

from telethon import TelegramClient, events

from db import create_user, is_user_exist

logger = logging.getLogger(__name__)


async def start_handler(event: events.NewMessage.Event) -> None:
    """Create the private-chat user record and send a welcome message."""

    if not event.is_private or event.sender_id is None:
        return

    try:
        if not await is_user_exist(event.sender_id):
            await create_user(event.sender_id)
        await event.reply(
            "👋 Welcome!\n\n"
            "Use /login to save your Telegram session string, or /settings "
            "to manage auto chats and your log channel."
        )
    except Exception:
        logger.exception("Failed to handle /start for user %s", event.sender_id)
        await event.reply("❌ Something went wrong. Please try again later.")


def setup(bot: TelegramClient) -> None:
    bot.add_event_handler(start_handler, events.NewMessage(pattern=r"^/start$"))
