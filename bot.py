import os
import re
import json
import logging
import aiohttp
import subprocess
import random

from pyrogram import Client, filters, idle
from pyrogram.types import Message

# ================= CONFIG =================

API_ID = 15191874
API_HASH = "3037d39233c6fad9b80d83bb8a339a07"

BOT_TOKEN = "7350676839:AAGlgApZke3RNYzS2ggLBdJjOiBmOq7Tq_U"
SESSION_STRING = "BQDnz0IAJzOoxRzgimGKUJn10SeMh23vIVn7VzZRkHqfHvzdAs7Tc2vKY_li_dv6oD5207CYf3SpXmmkKRjbM5LFYCxLs8KtHcMZ4dx99Lkw7SMZOprSGHh_-ZQ8P4Lrur7a0ro5JqMi3OD7K3o_JOuHJuUZ4_sZU2oPmOR2UA-U0ClMKeUbGsVF6xWZpAE0Q2u64nsq3u52yS2mKg761udlELDNKk-S_gdIvfP_vAu9SW0zoIpYxhuhxXjxh3TmzNYacwotTVfUT3gtuWiR-JareKyPXaW80d2c9U-74u3LrrcVaYnO2WJG1pUUDNsmkH14KybnXE0Jn0RjnvruAbsnQPCtZQAAAAGQaum1AA"


API_URL = "https://api.teamdev.sbs/v2/download?url={}&api=teamdev_sgovr3nf4x&json=1"

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

    logger.info(f"[API] Requesting API for link: {link}")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    async with aiohttp.ClientSession() as session:

        # -------- API CALL --------
        async with session.get(API_URL.format(link), timeout=60) as resp:

            logger.info(f"[API] Status Code: {resp.status}")

            if resp.status != 200:
                raise Exception(f"API HTTP Error: {resp.status}")

            data = await resp.json(content_type=None)

            if not data.get("success"):
                raise Exception("API returned success=False")

            file = data.get("file")
            if not file:
                raise Exception("No file data")

            filename = file.get("name")
            download_link = file.get("link")

            logger.info(f"[API] Filename: {filename}")
            logger.info(f"[API] Download link received")

        # sanitize filename
        filename = re.sub(r'[\\/*?:"<>|]', "", filename)
        file_path = os.path.join(DOWNLOAD_DIR, filename)

        logger.info(f"[DOWNLOAD] Starting download: {filename}")

        # -------- DOWNLOAD --------
        async with session.get(download_link) as resp:

            if resp.status != 200:
                raise Exception(f"Download failed: {resp.status}")

            with open(file_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    if chunk:
                        f.write(chunk)

        logger.info(f"[DOWNLOAD] Completed: {file_path}")

    return filename

# ================= VIDEO METADATA =================

def get_video_metadata(filename):

    logger.info(f"[META] Extracting metadata for: {filename}")

    video_path = os.path.join(DOWNLOAD_DIR, filename)

    if not os.path.exists(video_path):
        raise Exception("Video file not found")

    # -------- ffprobe --------
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", video_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)

    video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)

    if not video_stream:
        raise Exception("No video stream found")

    width = video_stream.get("width", 0)
    height = video_stream.get("height", 0)
    duration = int(float(video_stream.get("duration", 1)))

    logger.info(f"[META] Duration: {duration}s | {width}x{height}")

    # -------- THUMB --------
    thumb_path = os.path.join(DOWNLOAD_DIR, f"{filename}_thumb.jpg")

    sec = random.randint(1, max(2, duration - 1))

    logger.info(f"[THUMB] Generating at {sec}s")

    subprocess.run([
        "ffmpeg", "-ss", str(sec), "-i", video_path,
        "-frames:v", "1", "-q:v", "2", thumb_path, "-y"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    logger.info(f"[THUMB] Created: {thumb_path}")

    return duration, width, height, thumb_path

# ================= MAIN PROCESS =================

async def process_link(link, msg_id):

    try:
        logger.info(f"[PROCESS] Started for message: {msg_id}")

        # -------- DOWNLOAD --------
        filename = await download_from_api(link)

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
        logger.error(f"[PROCESS ERROR] {e}")

# ================= LINK DETECTOR =================

@userbot.on_message(filters.chat(A_CHAT))
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