"""Metadata extraction helpers for Telethon messages."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from telethon.tl.custom.message import Message
from telethon.tl.types import (
    DocumentAttributeAudio,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
)

from Userbot.helpers import format_bytes, format_duration


def _document_attributes(message: Message) -> list[Any]:
    document = message.document
    return list(getattr(document, "attributes", []) or [])


def _file_name(message: Message, downloaded_path: str | None) -> str | None:
    for attribute in _document_attributes(message):
        if isinstance(attribute, DocumentAttributeFilename):
            return attribute.file_name
    if message.file and message.file.name:
        return message.file.name
    if downloaded_path:
        return Path(downloaded_path).name
    return None


def _video_attribute(message: Message) -> DocumentAttributeVideo | None:
    for attribute in _document_attributes(message):
        if isinstance(attribute, DocumentAttributeVideo):
            return attribute
    return None


def _audio_attribute(message: Message) -> DocumentAttributeAudio | None:
    for attribute in _document_attributes(message):
        if isinstance(attribute, DocumentAttributeAudio):
            return attribute
    return None


def extract_metadata(
    message: Message,
    message_type: str,
    downloaded_path: str | None,
) -> dict[str, str]:
    """Extract supported metadata from a Telethon message."""

    file = message.file
    size = getattr(file, "size", None)
    mime_type = getattr(file, "mime_type", None)

    if message_type == "video":
        video = _video_attribute(message)
        width = getattr(video, "w", None)
        height = getattr(video, "h", None)
        return {
            "File Name": _file_name(message, downloaded_path) or "Unknown",
            "Duration": format_duration(getattr(video, "duration", None)),
            "Width": str(width or "Unknown"),
            "Height": str(height or "Unknown"),
            "Resolution": f"{width}×{height}" if width and height else "Unknown",
            "MIME Type": mime_type or "Unknown",
            "File Size": format_bytes(size),
        }

    if message_type == "audio":
        audio = _audio_attribute(message)
        return {
            "File Name": _file_name(message, downloaded_path) or "Unknown",
            "Performer": getattr(audio, "performer", None) or "Unknown",
            "Title": getattr(audio, "title", None) or "Unknown",
            "Duration": format_duration(getattr(audio, "duration", None)),
            "File Size": format_bytes(size),
        }

    if message_type == "file":
        name = _file_name(message, downloaded_path) or "Unknown"
        return {
            "File Name": name,
            "Extension": Path(name).suffix or "Unknown",
            "MIME Type": mime_type or "Unknown",
            "File Size": format_bytes(size),
        }

    if message_type == "gif":
        video = _video_attribute(message)
        width = getattr(video, "w", None)
        height = getattr(video, "h", None)
        return {
            "Duration": format_duration(getattr(video, "duration", None)),
            "Resolution": f"{width}×{height}" if width and height else "Unknown",
            "File Size": format_bytes(size),
        }

    if message_type == "photo":
        width = getattr(file, "width", None)
        height = getattr(file, "height", None)
        return {
            "Resolution": f"{width}×{height}" if width and height else "Unknown",
            "File Size": format_bytes(size),
        }

    return {}
