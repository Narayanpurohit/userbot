# Production Telethon Telegram Bot

A fully asynchronous Telegram bot built with Python 3.11+, Telethon, Motor, and MongoDB.

## Features

- Environment-based configuration with validation.
- Async MongoDB user storage using Motor.
- Auto-loading plugin architecture.
- `/start`, `/login`, and `/settings` plugins.
- Telethon StringSession generation with OTP and 2FA handling.
- Inline settings for auto chats, log channel, and message save types.
- Userbot listeners that monitor configured chats from saved user sessions.
- Async media download, metadata extraction, log-channel upload, and cleanup.
- Production-oriented logging and exception handling.

## Project structure

```text
bot.py
config.py
db.py
functions.py
requirements.txt
README.md
plugins/
  __init__.py
  start.py
  login.py
  settings.py
Userbot/
  __init__.py
  init.py
  listener.py
  metadata.py
  sender.py
  helpers.py
```

## Requirements

- Python 3.11+
- MongoDB
- Telegram API credentials from <https://my.telegram.org>
- Telegram bot token from BotFather

## Environment variables

Create and export these variables before running the bot:

```bash
export API_ID="123456"
export API_HASH="your_api_hash"
export BOT_TOKEN="123456:bot_token"
export MONGODB_URI="mongodb://localhost:27017"
export OWNER_ID="123456789"
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python bot.py
```

## Commands

- `/start` - creates a user record with default values and sends a welcome message. Private chats only.
- `/login` - starts an interactive login flow and stores a Telethon StringSession.
- `/settings` - opens inline settings for auto chats, log channel, and save types.

## Save types

Every user has the following save-type flags, defaulting to `True`:

- `text`
- `photo`
- `video`
- `audio`
- `file`
- `gif`

The **Save Types** settings menu toggles these values with CallbackQuery buttons and refreshes the same inline message.

## Userbot listener

When a user has a saved session string, at least one auto chat, and a log channel, the userbot listener monitors the configured chats. Enabled message types are downloaded asynchronously, metadata is extracted, media is sent to the configured log channel, and temporary files are removed after upload.

Plain text messages are copied to the log channel with source chat ID, sender ID, message ID, date, and original text.

## Plugin development

Add a new `.py` file inside `plugins/` and expose a `setup(bot)` function. The plugin loader imports every plugin automatically, so `bot.py` does not need to be modified for future plugins.
