# scripts/glue_pipeline.py
import logging
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from utils import setup_environment
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_short_script
from create_tts import create_tts
from auto_music_sfx import auto_music_sfx
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


# ------------------------
# UPDATE STATUS HANDLER
# ------------------------
def update_status(ws, row_idx, status: str):
    try:
        ws.update_cell(row_idx, 6, status)
        logger.info(f"🔄 Sheet updated: Row {row_idx} → {status}")
    except Exception as e:
        logger.error(f"❌ Failed to update Google Sheet: {e}")


# ------------------------
# MAIN PIPELINE
# ------------------------
def main():
    setup_environment()

    # 1) Fetch data from Google Sheet
    task = fetch_content()
    if not task:
        logger.info("📭 No new tasks.")
        return

    data = task["data"]
    row_idx = task["row_idx"]
    ws = task["worksheet"]
    eid = data["ID"]

    logger.info(f"🚀 START PIPELINE FOR EPISODE {eid}")

    update_status(ws, row_idx, "PROCESSING")

    # ====================================================
    # 🔥 2) SHORT FORM CONTENT (25–30s)
    # ====================================================
    logger.info("🎬 Generating Short Script...")
    short_result = generate_short_script(data)

    if short_result:
        short_script_path, short_title_path = short_result

        # Load hook title
        try:
            with open(short_title_path, "r", encoding="utf-8") as f:
                hook_title = f.read().strip()
        except:
            hook_title = f"{data.get('Name')} Story"

        logger.info("🎤 Creating TTS for SHORTS...")
        tts_short_path = create_tts(short_script_path, eid, mode="short")

        if tts_short_path:
            logger.info("🎞️ Creating SHORT video (9:16)...")
            shorts_video_path = create_shorts(
                tts_short_path,
                hook_title,
                eid,
                data["Name"]
            )

            if shorts_video_path:
                upload_short_title = f"{hook_title} #Shorts"
                upload_short_desc = (
                    f"A dramatic short story about {data.get('Name')}.\n"
                    f"Theme: {data.get('Core Theme')}\n"
                    "#shorts #documentary #storytelling\n"
                )
                upload_short_tags = [
                    "shorts", "documentary", "viral", "story",
                    data.get("Name", ""), data.get("Core Theme", "")
                ]

                logger.info("📤 Uploading SHORT video...")
                upload_video(shorts_video_path, {
                    "Title": upload_short_title,
                    "Summary": upload_short_desc,
                    "Tags": upload_short_tags,
                })

    update_status(ws, row_idx, "DONE_SHORTS")
    logger.info("🎉 SHORTS PROCESS COMPLETED")

    # ====================================================
    # 🔥 3) LONG SCRIPT → TTS → AUDIO MIX → VIDEO
    # ====================================================
    logger.info("📝 Generating LONG script...")
    long_script_path = generate_long_script(data)

    if not long_script_path:
        update_status(ws, row_idx, "FAILED_LONG_SCRIPT")
        return

    logger.info("🎤 Generating LONG TTS...")
    tts_long_path = create_tts(long_script_path, eid, mode="lon_
