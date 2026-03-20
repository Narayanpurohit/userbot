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


A_CHAT = -1002513087490
C_CHAT = -1002687789677
D_CHAT = 7607289349

PENDING_FILE = "pending_c.json"
CURRENT_FILE = "c.json"
DATA_FILE = "data.json"
FORWARD_FILE = "forward.json"

DOWNLOAD_DIR = "downloads"

LINK_REGEX = r"(https?://\S+|t\.me/\S+)"

# ================= ADVANCED LOGGING =================

LOG_FILE = "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
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

def load_forward():
    if not os.path.exists(FORWARD_FILE):
        return None
    with open(FORWARD_FILE) as f:
        return json.load(f)

def save_forward(data):
    with open(FORWARD_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= BATCH PROCESS =================

async def process_forward_batch():

    logger.info("🚀 [BATCH] Started")

    try:
        data = load_forward()
        if not data:
            logger.warning("[BATCH] No data")
            return

        chat_id = data["chat_id"]
        current_id = data["current_id"]
        end_id = data["end_id"]

        while True:
            current_id += 1

            if current_id > end_id:
                logger.info("✅ [BATCH] Completed")
                return

            logger.info(f"[BATCH] Checking: {current_id}")

            try:
                msg = await userbot.get_messages(chat_id, current_id)
            except Exception as e:
                logger.warning(f"[BATCH] Fetch fail {current_id}")
                continue

            if not msg:
                continue

            text = msg.caption or msg.text or ""

            if "1024terabox.com" in text:

                logger.info(f"[BATCH] Found valid: {current_id}")

                await bot.copy_message(
                    A_CHAT,
                    chat_id,
                    current_id
                )

                data["current_id"] = current_id
                save_forward(data)

                return

    except Exception as e:
        logger.error(traceback.format_exc())

# ================= DOWNLOAD =================

async def download_from_api(link):

    logger.info(f"[API] Requesting: {link}")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    async with aiohttp.ClientSession() as session:

        async with session.get(API_URL.format(link)) as resp:

            if resp.status != 200:
                raise Exception(f"API HTTP Error: {resp.status}")

            data = await resp.json(content_type=None)

            logger.info(f"[API RESPONSE] {data}")

            # -------- VALIDATION --------
            if not data.get("success"):
                raise Exception(f"API Failed: {data}")

            if "file" not in data:
                raise Exception(f"No file key in API response: {data}")

            file = data["file"]

            filename = file.get("name")
            download_link = file.get("link")

            if not filename or not download_link:
                raise Exception(f"Invalid file data: {file}")

        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        path = os.path.join(DOWNLOAD_DIR, filename)

        logger.info(f"[DOWNLOAD] Starting: {filename}")

        async with session.get(download_link) as resp:

            if resp.status != 200:
                raise Exception(f"Download HTTP Error: {resp.status}")

            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(2 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)

        logger.info(f"[DOWNLOAD DONE] {filename}")

    return filename


async def safe_download(link, retries=3):

    for i in range(retries):
        try:
            return await download_from_api(link)

        except Exception as e:
            logger.error(f"[RETRY {i+1}] {e}")

            # optional delay
            await asyncio.sleep(2)

    raise Exception("Download failed after retries")
# ================= METADATA =================

def get_video_metadata(filename):

    path = os.path.join(DOWNLOAD_DIR, filename)
    cap = cv2.VideoCapture(path)

    width = int(cap.get(3))
    height = int(cap.get(4))
    fps = cap.get(5)
    frames = int(cap.get(7))

    duration = int(frames / fps) if fps > 0 else 0

    frame_no = random.randint(1, frames - 1) if frames > 0 else 1
    cap.set(1, frame_no)
    success, frame = cap.read()

    thumb = os.path.join(DOWNLOAD_DIR, f"{filename}_thumb.jpg")

    if success:
        cv2.imwrite(thumb, frame)

    cap.release()

    return duration, width, height, thumb

# ================= QUEUE =================

async def process_pending_c():

    logger.info("⚙️ [QUEUE] Running")

    try:
        pending = load_list(PENDING_FILE)

        if not pending:
            return

        msg_id = pending[0]

        save_list(CURRENT_FILE, {"current": msg_id})

        await userbot.send_message(D_CHAT, "/genlink")
        await asyncio.sleep(2)

        await userbot.forward_messages(D_CHAT, C_CHAT, msg_id)

        pending.pop(0)
        save_list(PENDING_FILE, pending)

    except Exception as e:
        logger.error(traceback.format_exc())

def is_c_busy():

    if not os.path.exists(CURRENT_FILE):
        return False

    try:
        with open(CURRENT_FILE) as f:
            return bool(json.load(f).get("current"))
    except:
        return False

# ================= MAIN =================

async def process_link(link, msg_id):

    logger.info(f"[PROCESS] Start {msg_id}")

    try:
        filename = await safe_download(link)

        duration, width, height, thumb = get_video_metadata(filename)

        path = os.path.join(DOWNLOAD_DIR, filename)

        sent = await bot.send_video(
            C_CHAT,
            path,
            caption=filename,
            duration=duration,
            width=width,
            height=height,
            supports_streaming=True,
            thumb=thumb
        )

        logger.info(f"[UPLOAD] {sent.id}")

        await process_forward_batch()

        data = load_json()

        key = f"{msg_id}_{sent.id}"

        data[key] = {
            "A_MSG_ID": msg_id,
            "A_MSG_LINK": link,
            "C_MSG_ID": sent.id,
            "D_CHAT_LINK": ""
        }

        save_json(data)

        pending = load_list(PENDING_FILE)

        if sent.id not in pending:
            pending.append(sent.id)
            save_list(PENDING_FILE, pending)

        if not is_c_busy():
            await process_pending_c()

        os.remove(path)
        os.remove(thumb)

    except Exception as e:
        logger.error(traceback.format_exc())

# ================= D CHAT =================

@userbot.on_message(filters.chat(D_CHAT))
async def handle_d_chat(client, message: Message):

    try:
        text = message.text or message.caption or ""
        links = re.findall(LINK_REGEX, text)

        if not links or not is_c_busy():
            return

        new_link = links[0]

        with open(CURRENT_FILE) as f:
            current_id = json.load(f).get("current")

        data = load_json()

        for key, val in data.items():

            if val["C_MSG_ID"] == current_id:

                val["D_CHAT_LINK"] = new_link
                save_json(data)

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

        await process_pending_c()

    except Exception as e:
        logger.error(traceback.format_exc())

# ================= LINK DETECTOR =================

@bot.on_message(filters.chat(A_CHAT))
async def detect_links(client, message: Message):

    text = message.text or message.caption

    if not text:
        return

    links = re.findall(LINK_REGEX, text)

    for link in links:
        await process_link(link, message.id)

# ================= BATCH COMMAND =================

def extract_ids(link):
    m = re.search(r"/c/(\d+)/(\d+)", link)
    if not m:
        return None, None
    return int("-100" + m.group(1)), int(m.group(2))

@bot.on_message(filters.command("batch"))
async def batch(client, message):

    try:
        f, l = message.command[1], message.command[2]

        c1, s = extract_ids(f)
        c2, e = extract_ids(l)

        data = {
            "chat_id": c1,
            "start_id": s,
            "current_id": s - 1,
            "end_id": e
        }

        save_forward(data)

        await message.reply("Batch Started 🚀")

        await process_forward_batch()

    except:
        await message.reply("Error")

# ================= RUN =================

async def main():
    await bot.start()
    await userbot.start()
    logger.info("🚀 Bot Started")
    await idle()

if __name__ == "__main__":
    bot.run(main())