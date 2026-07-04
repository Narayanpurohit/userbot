"""Async MongoDB access layer for bot users."""

from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from config import config

SAVE_TYPE_FIELDS = ("text", "photo", "video", "audio", "file", "gif")
SAVE_TYPE_DEFAULTS = dict.fromkeys(SAVE_TYPE_FIELDS, True)

client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(config.mongodb_uri)
database = client[config.database_name]
users = database[config.users_collection]


def _default_user(user_id: int) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "string": None,
        "premium_expire": None,
        "auto_chats": [],
        "log_channel": None,
        **SAVE_TYPE_DEFAULTS,
    }


def _insert_defaults(user_id: int, *exclude: str) -> dict[str, Any]:
    defaults = _default_user(user_id)
    for field in exclude:
        defaults.pop(field, None)
    return defaults


def _missing_save_type_defaults(user: dict[str, Any]) -> dict[str, bool]:
    return {
        field: default
        for field, default in SAVE_TYPE_DEFAULTS.items()
        if field not in user
    }


async def _ensure_save_type_defaults(user: dict[str, Any]) -> dict[str, Any]:
    missing = _missing_save_type_defaults(user)
    if missing:
        await users.update_one({"user_id": user["user_id"]}, {"$set": missing})
        user.update(missing)
    return user


async def init_db() -> None:
    """Create indexes and backfill default save-type settings."""

    await users.create_index([("user_id", ASCENDING)], unique=True)
    for field, default in SAVE_TYPE_DEFAULTS.items():
        await users.update_many(
            {field: {"$exists": False}},
            {"$set": {field: default}},
        )


async def close_db() -> None:
    """Close the MongoDB client."""

    client.close()


async def create_user(user_id: int) -> bool:
    """Create a user with default values if it does not exist."""

    try:
        await users.insert_one(_default_user(user_id))
        return True
    except DuplicateKeyError:
        return False


async def is_user_exist(user_id: int) -> bool:
    return await users.count_documents({"user_id": user_id}, limit=1) > 0


async def get_user(user_id: int) -> dict[str, Any] | None:
    user = await users.find_one({"user_id": user_id}, {"_id": 0})
    if user is None:
        return None
    return await _ensure_save_type_defaults(user)


async def delete_user(user_id: int) -> bool:
    result = await users.delete_one({"user_id": user_id})
    return result.deleted_count == 1


async def get_string(user_id: int) -> str | None:
    user = await get_user(user_id)
    return user.get("string") if user else None


async def set_string(user_id: int, string: str) -> None:
    await users.update_one(
        {"user_id": user_id},
        {
            "$set": {"string": string},
            "$setOnInsert": _insert_defaults(user_id, "string"),
        },
        upsert=True,
    )


async def delete_string(user_id: int) -> None:
    await users.update_one({"user_id": user_id}, {"$set": {"string": None}})


async def get_premium(user_id: int) -> datetime | None:
    user = await get_user(user_id)
    return user.get("premium_expire") if user else None


async def set_premium(user_id: int, premium_expire: datetime) -> None:
    await users.update_one(
        {"user_id": user_id},
        {
            "$set": {"premium_expire": premium_expire},
            "$setOnInsert": _insert_defaults(user_id, "premium_expire"),
        },
        upsert=True,
    )


async def remove_premium(user_id: int) -> None:
    await users.update_one({"user_id": user_id}, {"$set": {"premium_expire": None}})


async def get_auto_chats(user_id: int) -> list[int]:
    user = await get_user(user_id)
    return list(user.get("auto_chats", [])) if user else []


async def add_auto_chat(user_id: int, chat_id: int) -> bool:
    before = await get_auto_chats(user_id)
    await users.update_one(
        {"user_id": user_id},
        {
            "$addToSet": {"auto_chats": chat_id},
            "$setOnInsert": _insert_defaults(user_id, "auto_chats"),
        },
        upsert=True,
    )
    return chat_id not in before


async def remove_auto_chat(user_id: int, chat_id: int) -> bool:
    result = await users.update_one(
        {"user_id": user_id},
        {"$pull": {"auto_chats": chat_id}},
    )
    return result.modified_count > 0


async def clear_auto_chats(user_id: int) -> None:
    await users.update_one({"user_id": user_id}, {"$set": {"auto_chats": []}})


async def get_log_channel(user_id: int) -> int | None:
    user = await get_user(user_id)
    return user.get("log_channel") if user else None


async def set_log_channel(user_id: int, log_channel: int) -> None:
    await users.update_one(
        {"user_id": user_id},
        {
            "$set": {"log_channel": log_channel},
            "$setOnInsert": _insert_defaults(user_id, "log_channel"),
        },
        upsert=True,
    )


async def remove_log_channel(user_id: int) -> None:
    await users.update_one({"user_id": user_id}, {"$set": {"log_channel": None}})


async def get_save_types(user_id: int) -> dict[str, bool]:
    user = await get_user(user_id)
    if user is None:
        return SAVE_TYPE_DEFAULTS.copy()
    return {field: bool(user.get(field, True)) for field in SAVE_TYPE_FIELDS}


async def _set_save_type(user_id: int, field: str, value: bool) -> None:
    if field not in SAVE_TYPE_FIELDS:
        raise ValueError(f"Unsupported save type: {field}")
    await users.update_one(
        {"user_id": user_id},
        {
            "$set": {field: bool(value)},
            "$setOnInsert": _insert_defaults(user_id, field),
        },
        upsert=True,
    )


async def _toggle_save_type(user_id: int, field: str) -> bool:
    current = await get_save_types(user_id)
    value = not current[field]
    await _set_save_type(user_id, field, value)
    return value


async def set_text(user_id: int, value: bool) -> None:
    await _set_save_type(user_id, "text", value)


async def set_photo(user_id: int, value: bool) -> None:
    await _set_save_type(user_id, "photo", value)


async def set_video(user_id: int, value: bool) -> None:
    await _set_save_type(user_id, "video", value)


async def set_audio(user_id: int, value: bool) -> None:
    await _set_save_type(user_id, "audio", value)


async def set_file(user_id: int, value: bool) -> None:
    await _set_save_type(user_id, "file", value)


async def set_gif(user_id: int, value: bool) -> None:
    await _set_save_type(user_id, "gif", value)


async def toggle_text(user_id: int) -> bool:
    return await _toggle_save_type(user_id, "text")


async def toggle_photo(user_id: int) -> bool:
    return await _toggle_save_type(user_id, "photo")


async def toggle_video(user_id: int) -> bool:
    return await _toggle_save_type(user_id, "video")


async def toggle_audio(user_id: int) -> bool:
    return await _toggle_save_type(user_id, "audio")


async def toggle_file(user_id: int) -> bool:
    return await _toggle_save_type(user_id, "file")


async def toggle_gif(user_id: int) -> bool:
    return await _toggle_save_type(user_id, "gif")


async def total_users() -> int:
    return await users.count_documents({})


async def get_all_users() -> AsyncIterator[dict[str, Any]]:
    async for user in users.find({}, {"_id": 0}):
        yield await _ensure_save_type_defaults(user)
