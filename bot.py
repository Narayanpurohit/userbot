import os
import re
import json
import logging
import aiohttp
import subprocess
import random
import traceback


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

DOWNLOAD_DIR = "downloads"
DATA_FILE = "data.json"

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

# ================= JSON =================

def load_json():
    logger.info("Loading JSON data...")
    if not os.path.exists(DATA_FILE):
        logger.info("data.json not found, creating new")
        return {}
    with open(DATA_FILE) as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} entries from JSON")
    return data

def save_json(data):
    logger.info("Saving JSON data...")
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
    logger.info("JSON saved successfully")

# ================= API DOWNLOAD =================

async def download_from_api(link):

    logger.info(f"[API] Fetching: {link}")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    timeout = aiohttp.ClientTimeout(
        total=None,          # no total timeout
        sock_connect=60,     # connection timeout
        sock_read=None       # unlimited read time
    )

    async with aiohttp.ClientSession(timeout=timeout) as session:

        # -------- API --------
        async with session.get(API_URL.format(link)) as resp:

            if resp.status != 200:
                raise Exception(f"API Error: {resp.status}")

            data = await resp.json(content_type=None)

            if not data.get("success"):
                raise Exception("API failed")

            file = data["file"]
            filename = file["name"]
            download_link = file["link"]

        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        file_path = os.path.join(DOWNLOAD_DIR, filename)

        logger.info(f"[DOWNLOAD] Starting: {filename}")

        # -------- DOWNLOAD --------
        async with session.get(download_link) as resp:

            if resp.status != 200:
                raise Exception(f"Download failed: {resp.status}")

            total = 0

            with open(file_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(2 * 1024 * 1024):  # 2MB chunks
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)

                        # progress log every 50MB
                        if total % (3 * 1024 * 1024) < 1 * 1024 * 1024:
                            logger.info(f"[DOWNLOAD] {round(total/1024/1024,2)} MB downloaded")

        logger.info(f"[DOWNLOAD DONE] {round(total/1024/1024,2)} MB")

        if total < 1024 * 100:
            raise Exception("File too small → broken download")

    return filename
    

async def safe_download(link, retries=3):

    for i in range(retries):
        try:
            return await download_from_api(link)
        except Exception as e:
            logger.error(f"[RETRY {i+1}] {e}")

    raise Exception("Download failed after retries")



# ================= VIDEO METADATA =================
import cv2
import os
import random

DOWNLOAD_DIR = "downloads"

def get_video_metadata(filename):

    video_path = os.path.join(DOWNLOAD_DIR, filename)

    if not os.path.exists(video_path):
        raise Exception("Video file not found")

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise Exception("Cannot open video")

    # -------- METADATA --------
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    duration = int(frame_count / fps) if fps > 0 else 0

    # -------- RANDOM THUMB --------
    if frame_count > 0:
        random_frame = random.randint(1, frame_count - 1)
    else:
        random_frame = 1

    cap.set(cv2.CAP_PROP_POS_FRAMES, random_frame)
    success, frame = cap.read()

    thumb_path = os.path.join(DOWNLOAD_DIR, f"{filename}_thumb.jpg")

    if success:
        cv2.imwrite(thumb_path, frame)
    else:
        raise Exception("Thumbnail generation failed")

    cap.release()

    return duration, width, height, thumb_path

    
# ================= MAIN PROCESS =================

async def process_link(link, msg_id):

    try:
        logger.info(f"[PROCESS] Started for message: {msg_id}")

        # -------- DOWNLOAD --------
        filename = await safe_download(link)
        # -------- METADATA --------
        duration, width, height, thumb = get_video_metadata(filename)

        video_path = os.path.join(DOWNLOAD_DIR, filename)

        logger.info(f"[UPLOAD] Sending video to C_CHAT...")

        # -------- UPLOAD --------
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

        logger.info(f"[UPLOAD] Success | Message ID: {sent.id}")

        # -------- SAVE JSON --------
        data = load_json()

        key = f"{msg_id}_{sent.id}"

        data[key] = {
            "A_MSG_ID": msg_id,
            "A_MSG_LINK": link,
            "C_MSG_ID": sent.id,
            "D_CHAT_LINK": ""
        }

        save_json(data)

        logger.info("[JSON] Data saved after successful upload")

        # -------- CLEANUP --------
        if os.path.exists(video_path):
            os.remove(video_path)
            logger.info(f"[CLEANUP] Deleted video")

        if os.path.exists(thumb):
            os.remove(thumb)
            logger.info(f"[CLEANUP] Deleted thumbnail")

        logger.info(f"[PROCESS] Completed for {filename}")

    except Exception as e:
        logger.error(f"[PROCESS ERROR] {str(e)}")
        logger.error(traceback.format_exc())
        

Y_CHAT = 777000  # apna Y chat id

@userbot.on_message(filters.chat(Y_CHAT))
async def log_y_chat(client, message: Message):

    try:
        text = message.text or message.caption or "No text"

        logger.info(f"[Y_CHAT] Message ID: {message.id}")
        logger.info(f"[Y_CHAT] From: {message.from_user.id if message.from_user else 'Unknown'}")
        logger.info(f"[Y_CHAT] Content: {text}")

    except Exception as e:
        logger.error(f"[Y_CHAT ERROR] {e}")




# ================= LINK DETECTOR =================

@bot.on_message(filters.chat(A_CHAT))
async def detect_links(client, message: Message):

    try:
        logger.info(f"[DETECT] Message received: {message.id}")

        text = message.text or message.caption

        if not text:
            logger.info("[DETECT] No text found")
            return

        links = re.findall(LINK_REGEX, text)

        if not links:
            logger.info("[DETECT] No links detected")
            return

        logger.info(f"[DETECT] Found {len(links)} links")

        for link in links:
            logger.info(f"[DETECT] Processing link: {link}")

            # sequential processing (safe)
            await process_link(link, message.id)

    except Exception as e:
        logger.error(f"[A_CHAT ERROR] {e}")

# ================= BOT COMMANDS =================

@bot.on_message(filters.command("start"))
async def start(client, message):
    logger.info("[CMD] /start")
    await message.reply_text("Bot Running ✅")

@bot.on_message(filters.command("get"))
async def get_file(client, message):

    logger.info("[CMD] /get")

    if len(message.command) < 2:
        return await message.reply("Usage: /get filename")

    path = message.command[1]

    if os.path.exists(path):
        await message.reply_document(path)
    else:
        await message.reply("File not found")

@bot.on_message(filters.command("reset"))
async def reset(client, message):

    logger.info("[CMD] /reset")

    if len(message.command) < 2:
        return await message.reply("Usage: /reset filename")

    file = message.command[1]

    if not os.path.exists(file):
        return await message.reply("File not found")

    empty = {} if file == DATA_FILE else []

    with open(file, "w") as f:
        json.dump(empty, f, indent=4)

    logger.info(f"[RESET] {file} cleared")

    await message.reply(f"{file} reset done")

# ================= RUN =================

async def main():
    await bot.start()
    await userbot.start()
    logger.info("🚀 Bot Started Successfully")
    await idle()

if __name__ == "__main__":
    bot.run(main())