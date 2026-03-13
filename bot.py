import os
import re
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG =================

API_ID = 15191874
API_HASH = "3037d39233c6fad9b80d83bb8a339a07"

BOT_TOKEN = "7350676839:AAGlgApZke3RNYzS2ggLBdJjOiBmOq7Tq_U"
SESSION_STRING = "BQDnz0IATv-jJ1F-gGuFwa2v3l8FbpC76LGw_xlTGtsHJt6pwhZ58-ZHUj7Qur16VOVUaMZim5vZYgwszsqtrKe4HJuW-HumekctOASH9h7mPO7-7MZPfmfBirkcG-Mji82Vw_G7F73phb8Zu_QP_q5ZsOIcxa5cZtl3MNN2fr5H84zBHhsPGYRNPnprnLywkv195TnFAmrsFmhGIlKJKWLVtKAavp3OfmCdqe24or4jWwM1vX_GG79mtWAksiiJEzh2ksfdLGmRWyvKUSeIJhqKtaUrEGDpFww19P1HjBNZ5TIi630DQYMEdrdIjZKq0OKEtgiQKnR9VXc9Zex6WVRaXL3B-wAAAAHRJC-ZAA"

A_CHAT = -1002513087490   # Chat ID jaha links detect karne hain
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
import json

DATA_FILE = "data.json"
PENDING_FILE = "pending_A.json"


def load_json(file):
    if not os.path.exists(file):
        return {} if file == DATA_FILE else []
    with open(file, "r") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


@userbot.on_message(filters.chat(A_CHAT))
async def detect_links(client, message: Message):
    try:

        logger.info(f"Message received in A_CHAT: {A_CHAT}")

        text = message.text or message.caption

        if not text:
            return

        links = re.findall(LINK_REGEX, text)

        if not links:
            return

        logger.info(f"Links detected: {links}")

        # load files
        data = load_json(DATA_FILE)
        pending = load_json(PENDING_FILE)

        msg_id = message.id

        for link in links:

            # save in data.json
            data[str(msg_id)] = {
                "A_MSG_ID": msg_id,
                "A_MSG_LINK": link,
                "C_MSG_ID": "",
                "D_CHAT_LINK": ""
            }

            # add to pending list
            pending.append(link)

        save_json(DATA_FILE, data)
        save_json(PENDING_FILE, pending)

        logger.info("Data saved to JSON files")

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
