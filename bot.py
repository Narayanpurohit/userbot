
import os
import re
import json
import logging

from pyrogram import Client, filters, idle
from pyrogram.types import Message
import aiohttp

API_URL = "https://api.teamdev.sbs/v2/download?url={}&api=teamdev_sgovr3nf4x&json=1"



API_ID = 15191874
API_HASH = "3037d39233c6fad9b80d83bb8a339a07"

BOT_TOKEN = "7350676839:AAGlgApZke3RNYzS2ggLBdJjOiBmOq7Tq_U"
SESSION_STRING = "BQDnz0IAJzOoxRzgimGKUJn10SeMh23vIVn7VzZRkHqfHvzdAs7Tc2vKY_li_dv6oD5207CYf3SpXmmkKRjbM5LFYCxLs8KtHcMZ4dx99Lkw7SMZOprSGHh_-ZQ8P4Lrur7a0ro5JqMi3OD7K3o_JOuHJuUZ4_sZU2oPmOR2UA-U0ClMKeUbGsVF6xWZpAE0Q2u64nsq3u52yS2mKg761udlELDNKk-S_gdIvfP_vAu9SW0zoIpYxhuhxXjxh3TmzNYacwotTVfUT3gtuWiR-JareKyPXaW80d2c9U-74u3LrrcVaYnO2WJG1pUUDNsmkH14KybnXE0Jn0RjnvruAbsnQPCtZQAAAAGQaum1AA"

A_CHAT = -1002513087490
FILES_DIR = "."
DOWNLOAD_DIR = "downloads"

DATA_FILE = "data.json"


LINK_REGEX = r"(https?://\S+|t\.me/\S+)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("LinkSaverBot")

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


async def download_from_api(a_link):

    # create folder if not exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    api_url = API_URL.format(a_link)

    async with aiohttp.ClientSession() as session:

        # ---------- API REQUEST ----------
        async with session.get(api_url, timeout=60) as resp:

            if resp.status != 200:
                raise Exception(f"API HTTP Error: {resp.status}")

            data = await resp.json(content_type=None)

            if not data.get("success"):
                raise Exception("API returned success=False")

            file_data = data.get("file")

            if not file_data:
                raise Exception("No file data in API")

            filename = file_data.get("name")
            download_link = file_data.get("link")

            if not filename or not download_link:
                raise Exception("Missing filename or link")

        # ---------- DOWNLOAD FILE ----------
        file_path = os.path.join(DOWNLOAD_DIR, filename)

        async with session.get(download_link) as resp:

            if resp.status != 200:
                raise Exception(f"Download failed: {resp.status}")

            with open(file_path, "wb") as f:

                async for chunk in resp.content.iter_chunked(1024 * 1024):

                    if chunk:
                        f.write(chunk)

    return filename

import os
import subprocess
import json
import random

DOWNLOAD_DIR = "downloads"


def get_video_metadata(filename):

    video_path = os.path.join(DOWNLOAD_DIR, filename)

    if not os.path.exists(video_path):
        raise Exception("File not found")

    # ----------- GET VIDEO INFO -----------
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    data = json.loads(result.stdout)

    video_stream = None

    for stream in data["streams"]:
        if stream["codec_type"] == "video":
            video_stream = stream
            break

    if not video_stream:
        raise Exception("No video stream found")

    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)

    duration = int(float(video_stream.get("duration", 0)))

    # ----------- GENERATE RANDOM THUMB -----------
    thumb_name = f"{filename}_thumb.jpg"
    thumb_path = os.path.join(DOWNLOAD_DIR, thumb_name)

    # random second (avoid 0)
    rand_sec = random.randint(1, max(2, duration - 1))

    cmd = [
        "ffmpeg",
        "-ss", str(rand_sec),
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        thumb_path,
        "-y"
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return duration, width, height, thumb_path
    
    
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

        data = load_json()

        for link in links:

            data[str(message.id)] = {
                "A_MSG_ID": message.id,
                "A_MSG_LINK": link,
                "C_MSG_ID": "",
                "D_CHAT_LINK": ""
            }

            logger.info(f"Saved link: {link}")

        save_json(data)

    except Exception as e:

        logger.error(f"A_CHAT error: {e}")


# ================= BOT COMMANDS =================

@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):

    await message.reply_text(
        "Hello 👋\n\nCommands:\n"
        "/get filename\n"
        "/reset filename"
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

        logger.error(f"File sending error: {e}")
        await message.reply_text("Error while sending file.")


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

        if filename == DATA_FILE:
            empty_data = {}
        else:
            empty_data = []

        with open(filename, "w") as f:
            json.dump(empty_data, f, indent=4)

        logger.info(f"{filename} reset by {message.from_user.id}")

        await message.reply_text(f"{filename} has been reset successfully.")

    except Exception as e:

        logger.error(f"Reset error: {e}")
        await message.reply_text("Error resetting file.")


# ================= RUN =================

async def main():

    await bot.start()
    await userbot.start()

    logger.info("Bot Started Successfully")

    await idle()


if __name__ == "__main__":
    bot.run(main())