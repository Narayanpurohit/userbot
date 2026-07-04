"""Reusable helpers for userbot message processing."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from telethon.tl.custom.message import Message

SAVE_TYPE_LABELS = {
    "text": "Text",
    "photo": "Photo",
    "video": "Video",
    "audio": "Audio",
    "file": "File",
    "gif": "GIF",
}


def detect_message_type(message: Message) -> str | None:
    """Return the supported save type for a Telethon message."""

    if message.gif:
        return "gif"
    if message.video:
        return "video"
    if message.audio or message.voice:
        return "audio"
    if message.photo:
        return "photo"
    if message.document:
        return "file"
    if message.raw_text:
        return "text"
    return None


def format_bytes(size: int | None) -> str:
    """Format bytes into a human-readable string."""

    if size is None:
        return "Unknown"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def format_duration(seconds: int | float | None) -> str:
    """Format a duration value as HH:MM:SS."""

    if seconds is None:
        return "Unknown"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def utc_timestamp(value: datetime | None) -> str:
    """Return a UTC ISO-8601 timestamp for message dates."""

    if value is None:
        value = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def safe_unlink(path: str | Path | None) -> None:
    """Delete a file without raising cleanup errors."""

    if path is None:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        return


def build_caption(
    *,
    original_caption: str | None,
    metadata: dict[str, Any],
    source_chat: int | None,
    message_id: int,
    date: datetime | None,
    sender_id: int | None,
) -> str:
    """Build a compact metadata caption for uploaded log-channel media."""

    lines: list[str] = []
    if original_caption:
        lines.extend(["Original Caption:", original_caption.strip(), ""])

    for key, value in metadata.items():
        if value is None or value == "":
            continue
        lines.extend([f"{key}:", str(value), ""])

    lines.extend(
        [
            "Source Chat:",
            str(source_chat),
            "",
            "Message ID:",
            str(message_id),
            "",
            "Date:",
            utc_timestamp(date),
            "",
            "Sender ID:",
            str(sender_id),
        ]
    )
    caption = "\n".join(lines).strip()
    return caption[:4096]


def build_text_log(
    *,
    text: str,
    source_chat: int | None,
    message_id: int,
    date: datetime | None,
    sender_id: int | None,
) -> str:
    """Build the log-channel body for plain text messages."""

    body = (
        "Source Chat ID:\n"
        f"{source_chat}\n\n"
        "Sender ID:\n"
        f"{sender_id}\n\n"
        "Message ID:\n"
        f"{message_id}\n\n"
        "Date:\n"
        f"{utc_timestamp(date)}\n\n"
        "Original Text:\n"
        f"{text}"
    )
    return body[:4096]
