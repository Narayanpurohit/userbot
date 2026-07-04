"""Inline settings plugin."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from telethon import Button, TelegramClient, events

from db import (
    SAVE_TYPE_FIELDS,
    add_auto_chat,
    create_user,
    get_auto_chats,
    get_log_channel,
    get_save_types,
    is_user_exist,
    remove_auto_chat,
    remove_log_channel,
    set_log_channel,
    toggle_audio,
    toggle_file,
    toggle_gif,
    toggle_photo,
    toggle_text,
    toggle_video,
)
from functions import parse_int
from Userbot.listener import refresh_userbot

logger = logging.getLogger(__name__)
ToggleFunc = Callable[[int], Awaitable[bool]]

SAVE_TYPE_LABELS = {
    "text": "Text",
    "photo": "Photo",
    "video": "Video",
    "audio": "Audio",
    "file": "File",
    "gif": "GIF",
}
SAVE_TYPE_TOGGLES: dict[str, ToggleFunc] = {
    "text": toggle_text,
    "photo": toggle_photo,
    "video": toggle_video,
    "audio": toggle_audio,
    "file": toggle_file,
    "gif": toggle_gif,
}


def _main_buttons() -> list[list[Button]]:
    return [
        [Button.inline("💬 Chats", b"settings:chats")],
        [Button.inline("📢 Log Channel", b"settings:log")],
        [Button.inline("💾 Save Types", b"settings:save_types")],
        [
            Button.inline("🛑 Stop", b"settings:stop"),
            Button.inline("🗑 Delete", b"settings:delete"),
        ],
    ]


def _chat_buttons() -> list[list[Button]]:
    return [
        [Button.inline("➕ Add Chat", b"settings:chat:add")],
        [Button.inline("➖ Remove Chat", b"settings:chat:remove")],
        [Button.inline("⬅️ Back", b"settings:back")],
    ]


def _log_buttons() -> list[list[Button]]:
    return [
        [
            Button.inline("➕ Add", b"settings:log:add"),
            Button.inline("➖ Remove", b"settings:log:remove"),
        ],
        [Button.inline("⬅️ Back", b"settings:back")],
    ]


def _save_type_buttons(save_types: dict[str, bool]) -> list[list[Button]]:
    buttons = []
    for field in SAVE_TYPE_FIELDS:
        status = "✅" if save_types.get(field, True) else "❌"
        label = SAVE_TYPE_LABELS[field]
        buttons.append([Button.inline(f"{label} : {status}", f"settings:save:{field}")])
    buttons.append([Button.inline("⬅️ Back", b"settings:back")])
    return buttons


async def _ensure_user(user_id: int) -> None:
    if not await is_user_exist(user_id):
        await create_user(user_id)


async def settings_handler(event: events.NewMessage.Event) -> None:
    if not event.is_private or event.sender_id is None:
        return

    await _ensure_user(event.sender_id)
    await event.reply("⚙️ Settings", buttons=_main_buttons())


async def callback_handler(event: events.CallbackQuery.Event) -> None:
    if event.sender_id is None:
        await event.answer("Unknown user", alert=True)
        return

    data = event.data.decode("utf-8")
    user_id = event.sender_id
    await _ensure_user(user_id)

    try:
        if data == "settings:back":
            await event.edit("⚙️ Settings", buttons=_main_buttons())
        elif data == "settings:stop":
            await event.edit("✅ Settings closed.")
        elif data == "settings:delete":
            await event.delete()
        elif data == "settings:chats":
            await _show_chats(event, user_id)
        elif data == "settings:log":
            await _show_log_channel(event, user_id)
        elif data == "settings:save_types":
            await _show_save_types(event, user_id)
        elif data.startswith("settings:save:"):
            await _toggle_save_type(event, user_id, data.rsplit(":", 1)[-1])
        elif data == "settings:chat:add":
            await _ask_chat(event, add=True)
        elif data == "settings:chat:remove":
            await _ask_chat(event, add=False)
        elif data == "settings:log:add":
            await _ask_log_channel(event)
        elif data == "settings:log:remove":
            await remove_log_channel(user_id)
            await refresh_userbot(user_id)
            await event.edit("✅ Log channel removed.", buttons=_log_buttons())
        else:
            await event.answer("Unknown action", alert=True)
    except Exception:
        logger.exception("Settings callback failed for user %s", user_id)
        await event.answer("Something went wrong", alert=True)


async def _show_chats(event: events.CallbackQuery.Event, user_id: int) -> None:
    chats = await get_auto_chats(user_id)
    body = "💬 Auto chats:\n" + (
        "\n".join(str(chat) for chat in chats) if chats else "None"
    )
    await event.edit(body, buttons=_chat_buttons())


async def _show_log_channel(event: events.CallbackQuery.Event, user_id: int) -> None:
    log_channel = await get_log_channel(user_id)
    await event.edit(
        f"📢 Current log channel: {log_channel or 'None'}",
        buttons=_log_buttons(),
    )


async def _show_save_types(event: events.CallbackQuery.Event, user_id: int) -> None:
    save_types = await get_save_types(user_id)
    await event.edit(
        "Select which message types should be saved.",
        buttons=_save_type_buttons(save_types),
    )


async def _toggle_save_type(
    event: events.CallbackQuery.Event,
    user_id: int,
    field: str,
) -> None:
    toggle = SAVE_TYPE_TOGGLES.get(field)
    if toggle is None:
        await event.answer("Unknown save type", alert=True)
        return
    await toggle(user_id)
    await _show_save_types(event, user_id)
    await event.answer("Updated")


async def _ask_chat(event: events.CallbackQuery.Event, *, add: bool) -> None:
    user_id = event.sender_id
    action = "add" if add else "remove"
    async with event.client.conversation(user_id, timeout=120, exclusive=False) as conv:
        await conv.send_message(f"Send the chat ID to {action}.")
        response = await conv.get_response()
        chat_id = parse_int(response.raw_text)
        if chat_id is None:
            await conv.send_message("❌ Invalid chat ID.")
            return

        if add:
            created = await add_auto_chat(user_id, chat_id)
            text = "✅ Chat added." if created else "ℹ️ Chat already exists."
        else:
            removed = await remove_auto_chat(user_id, chat_id)
            text = "✅ Chat removed." if removed else "ℹ️ Chat was not in your list."
        await refresh_userbot(user_id)
        chats = await get_auto_chats(user_id)
        await conv.send_message(f"{text}\nCurrent chats: {chats or 'None'}")


async def _ask_log_channel(event: events.CallbackQuery.Event) -> None:
    user_id = event.sender_id
    async with event.client.conversation(user_id, timeout=120, exclusive=False) as conv:
        await conv.send_message(
            "Send the log channel ID. This replaces the current value."
        )
        response = await conv.get_response()
        log_channel = parse_int(response.raw_text)
        if log_channel is None:
            await conv.send_message("❌ Invalid channel ID.")
            return
        await set_log_channel(user_id, log_channel)
        await refresh_userbot(user_id)
        await conv.send_message(f"✅ Log channel set to {log_channel}.")


def setup(bot: TelegramClient) -> None:
    bot.add_event_handler(settings_handler, events.NewMessage(pattern=r"^/settings$"))
    bot.add_event_handler(
        callback_handler,
        events.CallbackQuery(pattern=rb"^settings:"),
    )
