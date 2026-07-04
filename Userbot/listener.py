"""Telethon userbot listeners for configured user sessions."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from telethon import TelegramClient, events
from telethon.errors import FileReferenceExpiredError, FloodWaitError, RPCError
from telethon.sessions import StringSession
from telethon.tl.custom.message import Message

from config import config
from db import get_all_users, get_user
from Userbot.helpers import (
    build_caption,
    build_text_log,
    detect_message_type,
    safe_unlink,
)
from Userbot.metadata import extract_metadata
from Userbot.sender import send_media_log, send_text_log

logger = logging.getLogger(__name__)
_active_clients: dict[int, TelegramClient] = {}


async def start_all_userbots() -> None:
    """Start listeners for every user with a saved session and settings."""

    async for user in get_all_users():
        await start_userbot(int(user["user_id"]), user=user)


async def stop_all_userbots() -> None:
    """Disconnect all running userbot clients."""

    for user_id in list(_active_clients):
        await stop_userbot(user_id)


async def stop_userbot(user_id: int) -> None:
    """Stop one running userbot client if present."""

    client = _active_clients.pop(user_id, None)
    if client is None:
        return
    try:
        await client.disconnect()
    except Exception:
        logger.exception("Failed to disconnect userbot for user %s", user_id)


async def refresh_userbot(user_id: int) -> None:
    """Restart a userbot listener after session/settings changes."""

    await stop_userbot(user_id)
    await start_userbot(user_id)


async def start_userbot(
    user_id: int,
    *,
    user: dict | None = None,
) -> None:
    """Start a listener for a user's configured auto chats."""

    user = user or await get_user(user_id)
    if not user:
        return

    session = user.get("string")
    auto_chats = list(user.get("auto_chats") or [])
    log_channel = user.get("log_channel")
    if not session or not auto_chats or not log_channel:
        await stop_userbot(user_id)
        return

    await stop_userbot(user_id)
    client = TelegramClient(
        StringSession(session),
        config.api_id,
        config.api_hash,
    )

    async def handler(event: events.NewMessage.Event) -> None:
        await process_message(client, user_id, event.message)

    client.add_event_handler(handler, events.NewMessage(chats=auto_chats))
    try:
        await client.connect()
        if not await client.is_user_authorized():
            logger.warning("Stored session is unauthorized for user %s", user_id)
            await client.disconnect()
            return
        _active_clients[user_id] = client
        logger.info(
            "Started userbot for user %s with %s chats",
            user_id,
            len(auto_chats),
        )
    except (RPCError, OSError):
        logger.exception("Failed to start userbot for user %s", user_id)
        await client.disconnect()
    except Exception:
        logger.exception("Unexpected error starting userbot for user %s", user_id)
        await client.disconnect()


async def process_message(
    client: TelegramClient,
    user_id: int,
    message: Message,
) -> None:
    """Process one incoming message for a user's log channel."""

    try:
        user = await get_user(user_id)
        if not user or not user.get("log_channel"):
            return

        message_type = detect_message_type(message)
        if message_type is None or not bool(user.get(message_type, True)):
            return

        if message_type == "text":
            body = build_text_log(
                text=message.raw_text or "",
                source_chat=message.chat_id,
                message_id=message.id,
                date=message.date,
                sender_id=message.sender_id,
            )
            await send_text_log(client, int(user["log_channel"]), body)
            return

        await _process_media_message(
            client,
            int(user["log_channel"]),
            message_type,
            message,
        )
    except FloodWaitError:
        logger.exception("Flood wait while processing user %s message", user_id)
    except FileReferenceExpiredError:
        logger.exception("File reference expired for user %s message", user_id)
    except RPCError:
        logger.exception("Telegram RPC error for user %s message", user_id)
    except OSError:
        logger.exception("Network error for user %s message", user_id)
    except Exception:
        logger.exception("Unexpected processing error for user %s", user_id)


async def _process_media_message(
    client: TelegramClient,
    log_channel: int,
    message_type: str,
    message: Message,
) -> None:
    temp_dir = tempfile.TemporaryDirectory(prefix="userbot_")
    downloaded_path: str | None = None
    try:
        downloaded_path = await _download_message_media(client, message, temp_dir.name)
        if downloaded_path is None:
            logger.warning("Media download returned no path for message %s", message.id)
            return

        metadata = extract_metadata(message, message_type, downloaded_path)
        caption = build_caption(
            original_caption=message.raw_text,
            metadata=metadata,
            source_chat=message.chat_id,
            message_id=message.id,
            date=message.date,
            sender_id=message.sender_id,
        )
        await send_media_log(client, log_channel, downloaded_path, caption)
    except FileReferenceExpiredError:
        fresh_message = await client.get_messages(message.chat_id, ids=message.id)
        if fresh_message is None:
            raise
        safe_unlink(downloaded_path)
        downloaded_path = await _download_message_media(
            client,
            fresh_message,
            temp_dir.name,
        )
        if downloaded_path is None:
            return
        metadata = extract_metadata(fresh_message, message_type, downloaded_path)
        caption = build_caption(
            original_caption=fresh_message.raw_text,
            metadata=metadata,
            source_chat=fresh_message.chat_id,
            message_id=fresh_message.id,
            date=fresh_message.date,
            sender_id=fresh_message.sender_id,
        )
        await send_media_log(client, log_channel, downloaded_path, caption)
    finally:
        safe_unlink(downloaded_path)
        temp_dir.cleanup()


async def _download_message_media(
    client: TelegramClient,
    message: Message,
    directory: str,
) -> str | None:
    """Download message media once to an isolated temporary directory."""

    try:
        path = await client.download_media(message, file=directory)
    except FloodWaitError:
        logger.exception("Flood wait while downloading message %s", message.id)
        raise
    except FileReferenceExpiredError:
        raise
    except RPCError:
        logger.exception("Telegram RPC error while downloading message %s", message.id)
        raise
    except OSError:
        logger.exception("Network error while downloading message %s", message.id)
        raise
    except Exception:
        logger.exception("Download error for message %s", message.id)
        raise

    if path is None:
        return None
    return str(Path(path))
