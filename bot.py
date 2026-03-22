import os
import re
import json
import logging
import aiohttp
import traceback
import cv2

from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo

# ================= CONFIG =================

API_ID = 15191874
API_HASH = "3037d39233c6fad9b80d83bb8a339a07"

BOT_TOKEN = "7350676839:AAFMEhALeArmgixnlAjNGHEDdmgV93Gy_KQ"
BOT_TOKEN2 = "7782443871:AAH9IxP3YaIxGTz8LyIB2WPjW5n6pKw6_Vg"


API_URL = "https://api.teamdev.sbs/v2/download?url={}&api=teamdev_kz1aeheb0l&json=1"

A_CHAT = -1002513087490
B_CHAT = -1002533830212  # Source channel
C_CHAT = -1002687789677

DATA_FILE = "data.json"
DOWNLOAD_DIR = "downloads"

LINK_REGEX = r"(https?://\S+|t\.me/\S+)"

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AutoUploader")

# ================= CLIENT =================

bot = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
bot2 = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN2)

# ================= JSON =================

def load_json():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE) as f:
        return json.load(f)

def save_json(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= DOWNLOAD =================

FORWARD_FILE = "forward.json"

def load_forward():
    if not os.path.exists(FORWARD_FILE):
        return None
    with open(FORWARD_FILE) as f:
        return json.load(f)

def save_forward(data):
    with open(FORWARD_FILE, "w") as f:
        json.dump(data, f, indent=4)


async def batch_forward_once():

    data = load_forward()

    if not data:
        logger.info("[BATCH] No data")
        return

    current = data.get("current")
    last = data.get("last")

    # Stop condition
    if current > last:
        logger.info("[BATCH] Completed")
        return

    try:
        # Fetch message
        msg = await bot2.get_messages(B_CHAT, ids=current)

        if not msg:
            logger.warning(f"[BATCH] Not found: {current}")
        else:
            # Forward as copy
            await bot2.send_message(
                A_CHAT,
                msg.message or "",
                file=msg.media
            )

            logger.info(f"[BATCH] Forwarded: {current}")

    except Exception:
        logger.error(traceback.format_exc())

    # Increment and save
    data["current"] = current + 1
    save_forward(data)
    




async def download_from_api(link):

    logger.info(f"[API] Request: {link}")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    async with aiohttp.ClientSession() as session:

        async with session.get(API_URL.format(link)) as resp:
            data = await resp.json(content_type=None)

            if not data.get("success"):
                raise Exception(f"API Failed: {data}")

            file = data.get("file")
            if not file:
                raise Exception("No file in response")

            filename = re.sub(r'[\\/*?:"<>|]', "", file.get("name"))
            download_link = file.get("link")

        path = os.path.join(DOWNLOAD_DIR, filename)

        async with session.get(download_link) as resp:
            if resp.status != 200:
                raise Exception(f"Download HTTP Error: {resp.status}")

            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(2 * 1024 * 1024):
                    f.write(chunk)

    logger.info(f"[DOWNLOAD] Completed: {filename}")
    return filename

# ================= SAFE DOWNLOAD =================

async def safe_download(link):
    try:
        return await download_from_api(link)
    except Exception as e:
        logger.error(f"[DOWNLOAD ERROR] {e}")
        logger.error(traceback.format_exc())
        return None

# ================= METADATA =================

def get_video_metadata(filename):

    path = os.path.join(DOWNLOAD_DIR, filename)
    cap = cv2.VideoCapture(path)

    width = int(cap.get(3))
    height = int(cap.get(4))
    fps = cap.get(5)
    frames = int(cap.get(7))

    duration = int(frames / fps) if fps > 0 else 1

    frame_no = 1 if frames <= 1 else int(frames / 2)
    cap.set(1, frame_no)
    success, frame = cap.read()

    thumb = os.path.join(DOWNLOAD_DIR, f"{filename}_thumb.jpg")

    if success:
        cv2.imwrite(thumb, frame)

    cap.release()

    return duration, width, height, thumb

# ================= MAIN PROCESS =================

async def process_link(link, msg_id):

    logger.info(f"[PROCESS] Start | MsgID: {msg_id}")

    try:
        # Download
        filename = await safe_download(link)
        if not filename:
            return

        # Metadata
        duration, width, height, thumb = get_video_metadata(filename)

        path = os.path.join(DOWNLOAD_DIR, filename)

        # Upload with correct metadata
        sent = await bot.send_file(
            C_CHAT,
            path,
            caption=filename,
            supports_streaming=True,
            attributes=[
                DocumentAttributeVideo(
                    duration=int(duration),
                    w=int(width),
                    h=int(height),
                    supports_streaming=True
                )
            ],
            thumb=thumb if os.path.exists(thumb) else None
        )

        logger.info(f"[UPLOAD] Done: {sent.id}")

        # Save data
        data = load_json()

        key = f"{msg_id}_{sent.id}"

        data[key] = {
            "A_MSG_ID": msg_id,
            "A_MSG_LINK": link,
            "C_MSG_ID": sent.id
        }

        save_json(data)

        # Cleanup
        os.remove(path)
        if os.path.exists(thumb):
            os.remove(thumb)
        

    except Exception:
        logger.error(traceback.format_exc())

# ================= DETECTOR =================

@bot.on(events.NewMessage(chats=A_CHAT))
async def detect_links(event):

    text = event.message.message
    if not text:
        return

    links = re.findall(LINK_REGEX, text)

    for link in links:
        await process_link(link, event.message.id)
    await batch_forward_once()

# ================= COMMANDS =================

@bot.on(events.NewMessage(pattern=r'^/get (.+)'))
async def get_file(event):
    filename = event.pattern_match.group(1).strip()

    if not os.path.exists(filename):
        await event.reply(f"❌ File not found: {filename}")
        return

    await bot.send_file(
        event.chat_id,
        filename,
        caption=f"📁 {filename}"
    )

@bot.on(events.NewMessage(pattern=r'^/reset (.+)'))
async def reset_file(event):
    filename = event.pattern_match.group(1).strip()

    if not os.path.exists(filename):
        await event.reply(f"❌ File not found: {filename}")
        return

    with open(filename, "w") as f:
        f.write("")

    await event.reply(f"✅ Reset done: {filename}")



@bot.on(events.NewMessage(pattern=r'^/batch (\d+) (\d+)'))
async def batch_command(event):

    current = int(event.pattern_match.group(1))
    last = int(event.pattern_match.group(2))

    data = {
        "current": current,
        "last": last
    }

    save_forward(data)

    await event.reply(f"✅ Batch set\nFrom: {current}\nTo: {last}")

    # Run only once
    await batch_forward_once()
# ================= RUN =================

def main():
    logger.info("🚀 BOT STARTED (Telethon)")
    bot.run_until_disconnected()

if __name__ == "__main__":
    main()