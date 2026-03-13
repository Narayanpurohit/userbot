import os
import re
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG =================

API_ID = 15191874
API_HASH = "3037d39233c6fad9b80d83bb8a339a07"

BOT_TOKEN = "7350676839:AAGlgApZke3RNYzS2ggLBdJjOiBmOq7Tq_U"
SESSION_STRING = "BQGZqnkAWSiUjFwWgWKFAeiczK7pIa_hunvbXRbfI6sl_71r0AwPsmvi9QFOo2ziKqG8_-OouWLeWephqt58W8Qwi4rQ0BhlSUTQmn8kl6V2a6_w4Su-SjRwpF_tZH89Kf2nEccI7CmDl6bxRDF8ce0reeRsdMU0p1HTzMQLlb87WWRsVT9WQjW9cM9-NwHlm5MvEasYdH2wsPqaI3H92AqdfO5E1HjX2jIrF1G-okyGgGEDAropP3ir10bFXWn5uGFOaUcO1TSJSywMHQF32KXyJj1yaIT3hwcjdwE7OQl62mBRNhye0DT7AI55DAC2IQr_ypMzV0FOODEMCEY_VUJuEW6amgAAAAHRJC-ZAA"

A_CHAT = -1001234567890   # Chat ID jaha links detect karne hain
FILES_DIR = "./files"     # Directory jaha files stored hain

# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("CombinedBot")

# Clients
bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

userbot = Client(
    "userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Regex for links
LINK_REGEX = r"(https?://\S+|t\.me/\S+)"

# ================= USERBOT =================

@userbot.on_message(filters.chat(A_CHAT))
async def detect_links(client, message: Message):
    try:
        if message.text:
            links = re.findall(LINK_REGEX, message.text)

            if links:
                logger.info(f"Links detected in {A_CHAT}: {links}")
    except Exception as e:
        logger.error(f"Link detection error: {e}")

# ================= BOT =================

@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):
    logger.info(f"/start used by {message.from_user.id}")

    await message.reply_text(
        "Hello 👋\n\n"
        "Available Commands:\n"
        "/get filename"
    )


@bot.on_message(filters.command("get"))
async def get_file(client, message: Message):
    try:
        logger.info(f"/get command from {message.from_user.id}")

        if len(message.command) < 2:
            await message.reply_text("Usage:\n/get filename")
            return

        file_name = message.command[1]

        file_path = os.path.join(FILES_DIR, file_name)

        if os.path.exists(file_path):
            logger.info(f"Sending file: {file_name}")

            await message.reply_document(file_path)

        else:
            logger.warning(f"File not found: {file_name}")

            await message.reply_text("File not found.")

    except Exception as e:
        logger.error(f"File sending error: {e}")
        await message.reply_text("Error while sending file.")

# ================= RUN =================

async def main():
    await bot.start()
    await userbot.start()

    logger.info("Bot + Userbot Started Successfully")

    await idle()

from pyrogram import idle

if __name__ == "__main__":
    bot.run(main())
