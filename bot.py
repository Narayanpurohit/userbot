


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

DATA_FILE = "data.json"

API_URL = "https://api.teamdev.sbs/v2/download?url={}&api=teamdev_sgovr3nf4x&json=1"

LINK_REGEX = r"(https?://\S+|t\.me/\S+)"

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

# ================= JSON =================

def load_json():

    if not os.path.exists(DATA_FILE):
        return {}

    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_json(data):

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= API CALL =================

async def get_file_info(a_link):

    url = API_URL.format(a_link)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:

            data = await resp.json()

            if not data.get("success"):
                raise Exception("API request failed")

            file_data = data["file"]

            return {
                "name": file_data["name"],
                "download_link": file_data["link"],
                "thumb": file_data["thumbnails"]["360x270"]
            }

# ================= DOWNLOAD VIDEO =================

async def download_video(url, filename):

    async with aiohttp.ClientSession() as session:

        async with session.get(url) as resp:

            with open(filename, "wb") as f:

                async for chunk in resp.content.iter_chunked(1024 * 1024):

                    if chunk:
                        f.write(chunk)

    return filename

# ================= DOWNLOAD THUMB =================

async def download_thumb(url):

    thumb_path = "thumb.jpg"

    async with aiohttp.ClientSession() as session:

        async with session.get(url) as resp:

            with open(thumb_path, "wb") as f:

                f.write(await resp.read())

    return thumb_path

# ================= DATA UPDATE =================

def update_data_json(a_link, c_msg_id):

    data = load_json()

    for key in data:

        if data[key]["A_MSG_LINK"] == a_link:
            data[key]["C_MSG_ID"] = c_msg_id

    save_json(data)

# ================= LINK DETECT =================

@userbot.on_message(filters.chat(A_CHAT))
async def detect_links(client, message: Message):

    try:

        text = message.text or message.caption

        if not text:
            return

        links = re.findall(LINK_REGEX, text)

        if not links:
            return

        data = load_json()

        msg_id = message.id

        for link in links:

            logger.info(f"Processing {link}")

            data[str(msg_id)] = {
                "A_MSG_ID": msg_id,
                "A_MSG_LINK": link,
                "C_MSG_ID": "",
                "D_CHAT_LINK": ""
            }

            save_json(data)

            # ===== API CALL =====
            info = await get_file_info(link)

            filename = info["name"]
            download_link = info["download_link"]
            thumb_url = info["thumb"]

            # ===== DOWNLOAD VIDEO =====
            video_path = await download_video(download_link, filename)

            # ===== DOWNLOAD THUMB =====
            thumb_path = await download_thumb(thumb_url)

            # ===== TELEGRAM UPLOAD =====
            sent = await bot.send_video(
                C_CHAT,
                video_path,
                caption=filename,
                supports_streaming=True,
                thumb=thumb_path
            )

            update_data_json(link, sent.id)

            # ===== CLEANUP =====
            if os.path.exists(video_path):
                os.remove(video_path)

            if os.path.exists(thumb_path):
                os.remove(thumb_path)

            logger.info("Upload complete")

    except Exception as e:

        logger.error(f"A_CHAT error: {e}")

# ================= BOT COMMANDS =================

@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):

    await message.reply_text("Bot running ✅")


@bot.on_message(filters.command("reset"))
async def reset_file(client, message: Message):

    if not os.path.exists(DATA_FILE):

        await message.reply_text("data.json not found")
        return

    with open(DATA_FILE, "w") as f:
        json.dump({}, f, indent=4)

    await message.reply_text("data.json reset complete")

# ================= RUN =================

async def main():

    await bot.start()
    await userbot.start()

    logger.info("Bot Started Successfully")

    await idle()

if __name__ == "__main__":

    bot.run(main())