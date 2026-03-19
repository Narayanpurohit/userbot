
# ================= CONFIG =================



import os
import re
import json
import logging
import aiohttp
import asyncio
import random
import traceback
import cv2

from pyrogram import Client, filters, idle
from pyrogram.types import Message

# ================= CONFIG =================

API_ID = 15191874
API_HASH = "3037d39233c6fad9b80d83bb8a339a07"

BOT_TOKEN = "7350676839:AAGlgApZke3RNYzS2ggLBdJjOiBmOq7Tq_U"
SESSION_STRING = "BQDnz0IAJzOoxRzgimGKUJn10SeMh23vIVn7VzZRkHqfHvzdAs7Tc2vKY_li_dv6oD5207CYf3SpXmmkKRjbM5LFYCxLs8KtHcMZ4dx99Lkw7SMZOprSGHh_-ZQ8P4Lrur7a0ro5JqMi3OD7K3o_JOuHJuUZ4_sZU2oPmOR2UA-U0ClMKeUbGsVF6xWZpAE0Q2u64nsq3u52yS2mKg761udlELDNKk-S_gdIvfP_vAu9SW0zoIpYxhuhxXjxh3TmzNYacwotTVfUT3gtuWiR-JareKyPXaW80d2c9U-74u3LrrcVaYnO2WJG1pUUDNsmkH14KybnXE0Jn0RjnvruAbsnQPCtZQAAAAGQaum1AA"


API_URL = "https://api.teamdev.sbs/v2/download?url={}&api=teamdev_kz1aeheb0l&json=1"

A_CHAT = -1002513087490   # Source chat (links aate hain)
C_CHAT = -1002687789677   # Upload chat
D_CHAT = -100xxxxxxxxxx   # Genlink chat

PENDING_FILE = "pending_c.json"   # Queue list
CURRENT_FILE = "c.json"           # Currently processing
DATA_FILE = "data.json"

DOWNLOAD_DIR = "downloads"

LINK_REGEX = r"(https?://\S+|t\.me/\S+)"

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("AutoUploader")

# ================= CLIENTS =================

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ================= JSON HELPERS =================

def load_list(file):
    if not os.path.exists(file):
        return []
    with open(file) as f:
        return json.load(f)

def save_list(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def load_json():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_json(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= DOWNLOAD =================

async def download_from_api(link):

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    async with aiohttp.ClientSession() as session:

        # ---- API CALL ----
        async with session.get(API_URL.format(link)) as resp:

            data = await resp.json(content_type=None)

            file = data["file"]
            filename = re.sub(r'[\\/*?:"<>|]', "", file["name"])
            download_link = file["link"]

        file_path = os.path.join(DOWNLOAD_DIR, filename)

        # ---- DOWNLOAD FILE ----
        async with session.get(download_link) as resp:
            with open(file_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(2 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)

    return filename


async def safe_download(link, retries=3):

    for i in range(retries):
        try:
            return await download_from_api(link)
        except Exception as e:
            logger.error(f"[RETRY {i+1}] {e}")

    raise Exception("Download failed")

# ================= VIDEO METADATA =================

def get_video_metadata(filename):

    path = os.path.join(DOWNLOAD_DIR, filename)

    cap = cv2.VideoCapture(path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    duration = int(frames / fps) if fps > 0 else 0

    # ---- RANDOM THUMB ----
    frame_no = random.randint(1, frames - 1) if frames > 0 else 1
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    success, frame = cap.read()

    thumb = os.path.join(DOWNLOAD_DIR, f"{filename}_thumb.jpg")

    if success:
        cv2.imwrite(thumb, frame)

    cap.release()

    return duration, width, height, thumb

# ================= QUEUE PROCESS =================

async def process_pending_c():

    try:
        pending = load_list(PENDING_FILE)

        if not pending:
            return

        msg_id = pending[0]

        # ---- SET CURRENT ----
        save_list(CURRENT_FILE, {"current": msg_id})

        # ---- SEND COMMAND ----
        await userbot.send_message(D_CHAT, "/genlink")

        await asyncio.sleep(2)

        # ---- FORWARD ----
        await userbot.forward_messages(
            chat_id=D_CHAT,
            from_chat_id=C_CHAT,
            message_ids=msg_id
        )

        # ---- REMOVE FROM QUEUE ----
        pending.pop(0)
        save_list(PENDING_FILE, pending)

    except Exception as e:
        logger.error(e)

# ================= BUSY CHECK =================

def is_c_busy():

    if not os.path.exists(CURRENT_FILE):
        return False

    try:
        with open(CURRENT_FILE) as f:
            data = json.load(f)

        return bool(data.get("current"))

    except:
        return False

# ================= MAIN PROCESS =================

async def process_link(link, msg_id):

    try:
        # ---- DOWNLOAD ----
        filename = await safe_download(link)

        # ---- METADATA ----
        duration, width, height, thumb = get_video_metadata(filename)

        video_path = os.path.join(DOWNLOAD_DIR, filename)

        # ---- UPLOAD ----
        sent = await bot.send_video(
            C_CHAT,
            video_path,
            caption=filename,
            duration=duration,
            width=width,
            height=height,
            supports_streaming=True,
            thumb=thumb
        )

        # ---- SAVE JSON ----
        data = load_json()

        key = f"{msg_id}_{sent.id}"

        data[key] = {
            "A_MSG_ID": msg_id,
            "A_MSG_LINK": link,
            "C_MSG_ID": sent.id,
            "D_CHAT_LINK": ""
        }

        save_json(data)

        # ================= QUEUE SYSTEM =================

        pending = load_list(PENDING_FILE)

        if sent.id not in pending:
            pending.append(sent.id)
            save_list(PENDING_FILE, pending)

        # ---- TRIGGER QUEUE ----
        if not is_c_busy():
            await process_pending_c()

        # ---- CLEANUP ----
        os.remove(video_path)
        os.remove(thumb)

    except Exception as e:
        logger.error(e)

# ================= D CHAT HANDLER =================

@userbot.on_message(filters.chat(D_CHAT))
async def handle_d_chat(client, message: Message):

    try:
        text = message.text or message.caption or ""

        links = re.findall(LINK_REGEX, text)

        if not links:
            return

        new_link = links[0]

        if not is_c_busy():
            return

        # ---- GET CURRENT ----
        with open(CURRENT_FILE) as f:
            current_id = json.load(f).get("current")

        data = load_json()

        # ---- FIND ENTRY ----
        for key, val in data.items():

            if val["C_MSG_ID"] == current_id:

                val["D_CHAT_LINK"] = new_link
                save_json(data)

                # ---- EDIT CAPTION ----
                msg = await bot.get_messages(A_CHAT, val["A_MSG_ID"])

                caption = msg.caption or ""

                if val["A_MSG_LINK"] in caption:

                    new_caption = caption.replace(val["A_MSG_LINK"], new_link)

                    await bot.edit_message_caption(
                        A_CHAT,
                        val["A_MSG_ID"],
                        new_caption
                    )

                break

        # ---- NEXT QUEUE ----
        await process_pending_c()

    except Exception as e:
        logger.error(e)

# ================= LINK DETECTOR =================

@bot.on_message(filters.chat(A_CHAT))
async def detect_links(client, message: Message):

    text = message.text or message.caption

    if not text:
        return

    links = re.findall(LINK_REGEX, text)

    for link in links:
        await process_link(link, message.id)

# ================= RUN =================

async def main():
    await bot.start()
    await userbot.start()
    print("Bot Started 🚀")
    await idle()

if __name__ == "__main__":
    bot.run(main())