"""Async MongoDB access layer for bot users."""

from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from config import config

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
    }


def _insert_defaults(user_id: int, *exclude: str) -> dict[str, Any]:
    defaults = _default_user(user_id)
    for field in exclude:
        defaults.pop(field, None)
    return defaults


async def init_db() -> None:
    """Create indexes required by the application."""

    await users.create_index([("user_id", ASCENDING)], unique=True)


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
    return await users.find_one({"user_id": user_id}, {"_id": 0})


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


async def total_users() -> int:
    return await users.count_documents({})


async def get_all_users() -> AsyncIterator[dict[str, Any]]:
    async for user in users.find({}, {"_id": 0}):
        yield user
