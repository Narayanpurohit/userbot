"""/login command plugin for creating Telethon StringSessions."""

from __future__ import annotations

import logging

from telethon import TelegramClient, events
from telethon.errors import (
    FloodWaitError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
)
from telethon.sessions import StringSession

from config import config
from db import create_user, is_user_exist, set_string
from functions import generate_session_string

logger = logging.getLogger(__name__)


async def _ensure_user(user_id: int) -> None:
    if not await is_user_exist(user_id):
        await create_user(user_id)


async def login_handler(event: events.NewMessage.Event) -> None:
    """Run a private conversation to generate and store a session string."""

    if not event.is_private or event.sender_id is None:
        return

    user_id = event.sender_id
    await _ensure_user(user_id)

    async with event.client.conversation(user_id, timeout=300, exclusive=True) as conv:
        client = TelegramClient(StringSession(), config.api_id, config.api_hash)
        await client.connect()
        try:
            await conv.send_message(
                "📱 Send your phone number in international format "
                "(example: +15551234567)."
            )
            phone_msg = await conv.get_response()
            phone = phone_msg.raw_text.strip()

            try:
                sent_code = await client.send_code_request(phone)
            except PhoneNumberInvalidError:
                await conv.send_message(
                    "❌ Invalid phone number. Please run /login again."
                )
                return
            except FloodWaitError as exc:
                await conv.send_message(
                    f"⏳ Flood wait. Please try again in {exc.seconds} seconds."
                )
                return

            await conv.send_message("🔐 Enter the OTP code you received from Telegram.")
            otp_msg = await conv.get_response()
            otp = otp_msg.raw_text.replace(" ", "").strip()

            password: str | None = None
            try:
                session_string = await generate_session_string(
                    phone,
                    otp,
                    password,
                    phone_code_hash=sent_code.phone_code_hash,
                    client=client,
                )
            except SessionPasswordNeededError:
                await conv.send_message(
                    "🔑 Two-step verification is enabled. Send your password."
                )
                password_msg = await conv.get_response()
                password = password_msg.raw_text.strip()
                try:
                    session_string = await generate_session_string(
                        phone,
                        otp,
                        password,
                        phone_code_hash=sent_code.phone_code_hash,
                        client=client,
                    )
                except PasswordHashInvalidError:
                    await conv.send_message(
                        "❌ Wrong password. Please run /login again."
                    )
                    return
            except PhoneCodeInvalidError:
                await conv.send_message("❌ Invalid OTP. Please run /login again.")
                return
            except PhoneCodeExpiredError:
                await conv.send_message("❌ OTP expired. Please run /login again.")
                return
            except FloodWaitError as exc:
                await conv.send_message(
                    f"⏳ Flood wait. Please try again in {exc.seconds} seconds."
                )
                return

            await set_string(user_id, session_string)
            await conv.send_message("✅ Session string generated and saved securely.")
        except TimeoutError:
            await conv.send_message("⌛ Login timed out. Please run /login again.")
        except Exception:
            logger.exception("Login failed for user %s", user_id)
            await conv.send_message(
                "❌ Login failed unexpectedly. Please try again later."
            )
        finally:
            await client.disconnect()


def setup(bot: TelegramClient) -> None:
    bot.add_event_handler(login_handler, events.NewMessage(pattern=r"^/login$"))
