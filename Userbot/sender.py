"""Log-channel sending helpers."""

from __future__ import annotations

import logging

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError

logger = logging.getLogger(__name__)


async def send_text_log(
    client: TelegramClient,
    log_channel: int,
    text: str,
) -> None:
    """Send a text log message to the configured log channel."""

    try:
        await client.send_message(log_channel, text)
    except FloodWaitError:
        logger.exception("Flood wait while sending text log to %s", log_channel)
        raise
    except RPCError:
        logger.exception("Telegram RPC error while sending text log")
        raise
    except OSError:
        logger.exception("Network error while sending text log")
        raise


async def send_media_log(
    client: TelegramClient,
    log_channel: int,
    file_path: str,
    caption: str,
) -> None:
    """Upload downloaded media to the configured log channel."""

    try:
        await client.send_file(log_channel, file_path, caption=caption)
    except FloodWaitError:
        logger.exception("Flood wait while uploading media to %s", log_channel)
        raise
    except RPCError:
        logger.exception("Telegram RPC error while uploading media")
        raise
    except OSError:
        logger.exception("Network error while uploading media")
        raise
