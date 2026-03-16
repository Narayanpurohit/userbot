


import os
import re
import json
import logging
import aiohttp
import subprocess
import random

from pyrogram import Client, filters, idle
from pyrogram.types import Message

API_ID = 15191874
API_HASH = "3037d39233c6fad9b80d83bb8a339a07"

BOT_TOKEN = "7350676839:AAGlgApZke3RNYzS2ggLBdJjOiBmOq7Tq_U"
SESSION_STRING = "BQDnz0IAJzOoxRzgimGKUJn10SeMh23vIVn7VzZRkHqfHvzdAs7Tc2vKY_li_dv6oD5207CYf3SpXmmkKRjbM5LFYCxLs8KtHcMZ4dx99Lkw7SMZOprSGHh_-ZQ8P4Lrur7a0ro5JqMi3OD7K3o_JOuHJuUZ4_sZU2oPmOR2UA-U0ClMKeUbGsVF6xWZpAE0Q2u64nsq3u52yS2mKg761udlELDNKk-S_gdIvfP_vAu9SW0zoIpYxhuhxXjxh3TmzNYacwotTVfUT3gtuWiR-JareKyPXaW80d2c9U-74u3LrrcVaYnO2WJG1pUUDNsmkH14KybnXE0Jn0RjnvruAbsnQPCtZQAAAAGQaum1AA"


A_CHAT = -1002513087490
C_CHAT = -1002687789677

API_URL = "https://api.teamdev.sbs/v2/download?url={}&api=teamdev_qjic7fb1jz&json=1"

DATA_FILE = "data.json"

LINK_REGEX = r"(https?://\S+|t\.me/\S+)"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("TeraBoxBot")

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

    with open(DATA_FILE) as f:
        return json.load(f)


def save_json(data):

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ================= API =================

async def get_file_info(link):

    url = API_URL.format(link)

    async with aiohttp.ClientSession() as session:

        async with session.get(url) as resp:

            data = await resp.json()

            if not data.get("success"):
                raise Exception("API failed")

            file = data["file"]

            return file["name"], file["link"]


# ================= DOWNLOAD =================

async def download_video(url, filename):

    async with aiohttp.ClientSession() as session:

        async with session.get(url) as resp:

            with open(filename, "wb") as f:

                async for chunk in resp.content.iter_chunked(1024 * 1024):

                    if chunk:
                        f.write(chunk)

    return filename


# ================= VIDEO INFO =================

def get_video_info(video):

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    data = json.loads(result.stdout)

    video_stream = None

    for stream in data["streams"]:
        if stream["codec_type"] == "video":
            video_stream = stream
            break

    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)

    duration = int(float(video_stream.get("duration", 0)))

    return duration, width, height


# ================= THUMBNAIL =================

def generate_thumbnail(video):

    thumb = "thumb.jpg"

    time = random.randint(1, 10)

    cmd = [
        "ffmpeg",
        "-ss", str(time),
        "-i", video,
        "-frames:v", "1",
        "-q:v", "2",
        thumb,
        "-y"
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return thumb


# ================= MAIN PROCESS =================

async def process_link(link, msg_id):

    try:

        logger.info(f"Processing {link}")

        filename, download_link = await get_file_info(link)

        video_path = await download_video(download_link, filename)

        duration, width, height = get_video_info(video_path)

        thumb = generate_thumbnail(video_path)

        sent = await userbot.send_video(
            C_CHAT,
            video_path,
            caption=filename,
            duration=duration,
            width=width,
            height=height,
            supports_streaming=True,
            thumb=thumb
        )

        data = load_json()

        data[str(msg_id)]["C_MSG_ID"] = sent.id

        save_json(data)

        os.remove(video_path)

        if os.path.exists(thumb):
            os.remove(thumb)

        logger.info("Upload complete")

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

        data = load_json()

        for link in links:

            data[str(message.id)] = {
                "A_MSG_ID": message.id,
                "A_MSG_LINK": link,
                "C_MSG_ID": ""
            }

            save_json(data)

            await process_link(link, message.id)

    except Exception as e:

        logger.error(f"A_CHAT error: {e}")


# ================= BOT COMMANDS =================

@bot.on_message(filters.command("start"))
async def start(client, message):

    await message.reply_text("Bot Running ✅")


# ================= RUN =================

async def main():

    await bot.start()
    await userbot.start()

    logger.info("Bot Started Successfully")

    await idle()


if __name__ == "__main__":
    bot.run(main())