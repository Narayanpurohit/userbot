"""Reusable asynchronous helper functions."""

from __future__ import annotations

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.sessions import StringSession

from config import config


async def generate_session_string(
    phone: str,
    otp: str,
    password: str | None = None,
    *,
    phone_code_hash: str | None = None,
    client: TelegramClient | None = None,
) -> str:
    """Generate a Telethon StringSession for a user account.

    The public flow requires ``phone`` and ``otp`` and may require ``password``
    when two-step verification is enabled. Bot conversations should pass the
    ``phone_code_hash`` returned by ``send_code_request`` and the same connected
    ``client`` used to request the code, which keeps Telethon's auth state
    consistent for production login flows.
    """

    owns_client = client is None
    session_client = client or TelegramClient(
        StringSession(),
        config.api_id,
        config.api_hash,
    )

    if not session_client.is_connected():
        await session_client.connect()

    try:
        try:
            await session_client.sign_in(
                phone=phone,
                code=otp,
                phone_code_hash=phone_code_hash,
            )
        except SessionPasswordNeededError:
            if password is None:
                raise
            await session_client.sign_in(password=password)
        return session_client.session.save()
    finally:
        if owns_client:
            await session_client.disconnect()


def parse_int(value: str) -> int | None:
    """Parse an integer from user input, returning None on invalid input."""

    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return None
