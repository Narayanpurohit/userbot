"""Compatibility module for deployments expecting Userbot/init.py."""

from Userbot.listener import start_all_userbots, start_userbot, stop_all_userbots

__all__ = ["start_all_userbots", "start_userbot", "stop_all_userbots"]
