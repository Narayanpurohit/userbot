

import os
import re
import json
import logging
import aiohttp
from pyrogram import Client, filters, idle
from pyrogram.types import Message

# ================= CONFIG =================

API_ID = 15191874
API_HASH = "3037d39233c6fad9b80d83bb8a339a07"

BOT_TOKEN = "7350676839:AAGlgApZke3RNYzS2ggLBdJjOiBmOq7Tq_U"
SESSION_STRING = "BQDnz0IAJzOoxRzgimGKUJn10SeMh23vIVn7VzZRkHqfHvzdAs7Tc2vKY_li_dv6oD5207CYf3SpXmmkKRjbM5LFYCxLs8KtHcMZ4dx99Lkw7SMZOprSGHh_-ZQ8P4Lrur7a0ro5JqMi3OD7K3o_JOuHJuUZ4_sZU2oPmOR2UA-U0ClMKeUbGsVF6xWZpAE0Q2u64nsq3u52yS2mKg761udlELDNKk-S_gdIvfP_vAu9SW0zoIpYxhuhxXjxh3TmzNYacwotTVfUT3gtuWiR-JareKyPXaW80d2c9U-74u3LrrcVaYnO2WJG1pUUDNsmkH14KybnXE0Jn0RjnvruAbsnQPCtZQAAAAGQaum1AA"



A_CHAT = -1002513087490
C_CHAT = -1002687789677

FILES_DIR = "."
QUEUE_RUNNING = False
CURRENT_LINK = None

DATA_FILE = "data.json"
PENDING_FILE = "pending_A.json"

API_URL = "https://api.teamdev.sbs/v2/download?url={}&api=teamdev_qjic7fb1jz"

# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("CombinedBot")

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

LINK_REGEX = r"(https?://\S+|t\.me/\S+)"

# ================= JSON HELPERS =================

def load_json(file):

    if not os.path.exists(file):
        return {} if file == DATA_FILE else []

    with open(file, "r") as f:
        return json.load(f)


def save_json(file, data):

    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ================= DOWNLOAD =================

async def download_file(a_link):

    url = API_URL.format(a_link)

    file_path = "video.mp4"

    async with aiohttp.ClientSession() as session:

        async with session.get(url, allow_redirects=True) as resp:

            with open(file_path, "wb") as f:

                while True:

                    chunk = await resp.content.read(1024 * 1024)

                    if not chunk:
                        break

                    f.write(chunk)

    return file_path

# ================= DATA UPDATE =================

def update_data_json(a_link, c_msg_id):

    data = load_json(DATA_FILE)

    for key in data:

        if data[key]["A_MSG_LINK"] == a_link:

            data[key]["C_MSG_ID"] = c_msg_id

    save_json(DATA_FILE, data)

# ================= QUEUE PROCESS =================

async def process_pending_link():

    global QUEUE_RUNNING, CURRENT_LINK

    pending = load_json(PENDING_FILE)

    if not pending:

        logger.info("No pending links. Queue OFF")

        QUEUE_RUNNING = False
        CURRENT_LINK = None

        return

    QUEUE_RUNNING = True

    link = pending[0]

    CURRENT_LINK = link

    logger.info(f"Processing link: {link}")

    try:

        file_path = await download_file(link)

        logger.info("Download completed")

        c_msg = await userbot.send_video(
            C_CHAT,
            file_path,
            supports_streaming=True
        )

        logger.info("Uploaded to C_CHAT")

        update_data_json(link, c_msg.id)

        if os.path.exists(file_path):

            os.remove(file_path)

            logger.info("Local file deleted")

        pending.remove(link)

        save_json(PENDING_FILE, pending)

        CURRENT_LINK = None

        await process_pending_link()

    except Exception as e:

        logger.error(f"Processing error: {e}")

# ================= LINK DETECTOR =================

@userbot.on_message(filters.chat(A_CHAT))
async def detect_links(client, message: Message):

    try:

        text = message.text or message.caption

        if not text:
            return

        links = re.findall(LINK_REGEX, text)

        if not links:
            return

        data = load_json(DATA_FILE)
        pending = load_json(PENDING_FILE)

        msg_id = message.id

        for link in links:

            data[str(msg_id)] = {
                "A_MSG_ID": msg_id,
                "A_MSG_LINK": link,
                "C_MSG_ID": "",
                "D_CHAT_LINK": ""
            }

            if link not in pending:
                pending.append(link)

        save_json(DATA_FILE, data)
        save_json(PENDING_FILE, pending)

        logger.info(f"Links added to queue: {links}")

        global QUEUE_RUNNING

        if not QUEUE_RUNNING:
            await process_pending_link()

    except Exception as e:

        logger.error(f"A_CHAT error: {e}")

# ================= BOT COMMANDS =================

@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):

    await message.reply_text(
        "Hello 👋\n\nCommands:\n/get filename\n/reset filename"
    )


@bot.on_message(filters.command("get"))
async def get_file(client, message: Message):

    try:

        if len(message.command) < 2:

            await message.reply_text("Usage:\n/get filename")
            return

        file_name = message.command[1]

        file_path = os.path.join(FILES_DIR, file_name)

        if os.path.exists(file_path):

            await message.reply_document(file_path)

        else:

            await message.reply_text("File not found.")

    except Exception as e:

        logger.error(e)


@bot.on_message(filters.command("reset"))
async def reset_file(client, message: Message):

    try:

        if len(message.command) < 2:

            await message.reply_text("Usage:\n/reset filename")
            return

        filename = message.command[1]

        if not os.path.exists(filename):

            await message.reply_text("File not found.")
            return

        empty_data = {} if filename == DATA_FILE else []

        with open(filename, "w") as f:

            json.dump(empty_data, f, indent=4)

        await message.reply_text(f"{filename} reset successfully")

    except Exception as e:

        logger.error(f"Reset error: {e}")

# ================= RUN =================

async def main():

    await bot.start()
    await userbot.start()

    logger.info("Bot + Userbot Started Successfully")

    await idle()


if __name__ == "__main__":

    bot.run(main())

