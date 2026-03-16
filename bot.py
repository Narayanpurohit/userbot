import os
import re
import json
import logging
import aiohttp
import asyncio
import subprocess
import random

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

API_URL = "https://api.teamdev.sbs/v2/download?url={}&api=teamdev_qjic7fb1jz"

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

# ================= DOWNLOAD =================

async def download_video(a_link):

    url = API_URL.format(a_link)

    file_name = f"video_{random.randint(1000,9999)}.mp4"

    async with aiohttp.ClientSession() as session:

        async with session.get(url, allow_redirects=True) as resp:

            with open(file_name, "wb") as f:

                while True:

                    chunk = await resp.content.read(1024 * 1024)

                    if not chunk:
                        break

                    f.write(chunk)

    return file_name

# ================= VIDEO INFO =================

def get_video_metadata(video_path):

    import cv2
    import random

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise Exception("Video file corrupted or incomplete")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    fps = cap.get(cv2.CAP_PROP_FPS) or 1
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    duration = int(frame_count / fps) if frame_count > 0 else 0

    thumb = "thumb.jpg"

    if frame_count > 10:

        random_frame = random.randint(1, frame_count - 1)

        cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame)

        success, frame = cap.read()

        if success:
            cv2.imwrite(thumb, frame)
        else:
            thumb = None
    else:
        thumb = None

    cap.release()

    return duration, width, height, thumb
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

            # download video
            video_path = await download_video(link)

            # get metadata
            duration, width, height, thumb = get_video_metadata(video_path)

            caption = os.path.basename(video_path)

            # upload to telegram
            sent = await userbot.send_video(
    C_CHAT,
    video_path,
    caption=caption,
    duration=duration,
    width=width,
    height=height,
    supports_streaming=True,
    thumb=thumb if thumb else None
)

            update_data_json(link, sent.id)

            # cleanup
            if os.path.exists(video_path):
                os.remove(video_path)

            if os.path.exists(thumb):
                os.remove(thumb)

            logger.info("Upload complete")

    except Exception as e:

        logger.error(f"A_CHAT error: {e}")

# ================= BOT COMMANDS =================

@bot.on_message(filters.command("start"))
async def start_command(client, message: Message):

    await message.reply_text(
        "Hello 👋\n\nCommands:\n/get filename\n/reset filename"
    )


@bot.on_message(filters.command("reset"))
async def reset_file(client, message: Message):

    try:

        if not os.path.exists(DATA_FILE):

            await message.reply_text("data.json not found")
            return

        with open(DATA_FILE, "w") as f:

            json.dump({}, f, indent=4)

        await message.reply_text("data.json reset")

    except Exception as e:

        logger.error(e)

# ================= RUN =================

async def main():

    await bot.start()
    await userbot.start()

    logger.info("Bot Started Successfully")

    await idle()

if __name__ == "__main__":

    bot.run(main())
