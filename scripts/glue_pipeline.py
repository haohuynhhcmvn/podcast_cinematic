# ============================================================
# scripts/glue_pipeline.py
# ============================================================

import logging
import sys
import os
from time import sleep
import textwrap

# --- PATH SETUP ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from utils import setup_environment, get_path, cleanup_temp_files
from fetch_content import fetch_content
from generate_script import generate_long_script
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video
from auto_music_sfx import auto_music_sfx

try:
    from generate_image import generate_character_image
    from create_thumbnail import add_text_to_thumbnail
except Exception:
    generate_character_image = None
    add_text_to_thumbnail = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PIPELINE")

# ============================================================
# 🧠 SHORT EXTRACTION LOGIC (CORE)
# ============================================================

def split_long_script_to_5_shorts(long_script_path):
    """
    Cắt Long Script thành 5 đoạn Shorts (~45–55s mỗi đoạn)
    KHÔNG gọi OpenAI → tiết kiệm token
    """
    with open(long_script_path, "r", encoding="utf-8") as f:
        text = f.read()

    words = text.split()
    total_words = len(words)

    # ~120–130 words = 45–55s
    chunk_size = max(120, total_words // 5)

    shorts = []
    for i in range(5):
        start = i * chunk_size
        end = start + chunk_size
        chunk = " ".join(words[start:end])

        # CTA bắt buộc (đúng chiến lược retention)
        chunk += "\n\nThe full story explains why this decision failed."
        shorts.append(chunk)

    return shorts


def save_short_script(text, episode_id, index):
    path = get_path("data", "episodes", f"{episode_id}_short_{index}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


# ============================================================
# 🎬 LONG VIDEO PIPELINE
# ============================================================

def process_long_video(data):
    eid = str(data["ID"])
    name = data["Name"]

    logger.info(f"🎬 LONG VIDEO START: {eid} – {name}")

    # 1. LONG SCRIPT
    long_result = generate_long_script(data)
    if not long_result:
        return None

    script_path = long_result["script_path"]
    meta = long_result["metadata"]
    title = meta["youtube_title"]

    # 2. IMAGE (CACHE)
    raw_img = get_path("assets", "temp", f"{eid}_raw_ai.png")
    if not os.path.exists(raw_img) and generate_character_image:
        logger.info("🎨 Generating character image...")
        raw_img = generate_character_image(name, raw_img)

    # 3. THUMBNAIL
    thumb_path = None
    if raw_img and add_text_to_thumbnail:
        thumb_path = get_path("outputs", "thumbnails", f"{eid}_thumb.jpg")
        add_text_to_thumbnail(raw_img, title.upper(), thumb_path)

    # 4. TTS
    tts_path = create_tts(script_path, eid, "long")
    if not tts_path:
        return None

    # 5. MUSIC
    mixed_audio = auto_music_sfx(tts_path, eid)
    if not mixed_audio:
        return None

    # 6. VIDEO
    video_path = create_video(
        mixed_audio,
        eid,
        custom_image_path=raw_img,
        title_text=title
    )

    if not video_path:
        return None

    # 7. UPLOAD
    upload_result = upload_video(
        video_path,
        {
            "Title": title,
            "Summary": meta["youtube_description"],
            "Tags": meta["youtube_tags"]
        },
        thumbnail_path=thumb_path
    )

    if upload_result == "FAILED":
        return None

    logger.info("✅ LONG VIDEO DONE")
    return {
        "script_path": script_path,
        "image_path": raw_img
    }


# ============================================================
# 📱 SHORTS PIPELINE (5 SHORTS FROM 1 LONG)
# ============================================================

def process_5_shorts(long_script_path, image_path, data):
    eid = str(data["ID"])
    name = data["Name"]

    logger.info("📱 GENERATING 5 SHORTS FROM LONG SCRIPT")

    shorts = split_long_script_to_5_shorts(long_script_path)

    base_bg = get_path("assets", "images", "default_background_shorts.png")

    for idx, short_text in enumerate(shorts, start=1):
        logger.info(f"▶️ SHORT {idx}/5")

        script_path = save_short_script(short_text, eid, idx)

        # TTS
        tts_path = create_tts(script_path, f"{eid}_{idx}", "short")
        if not tts_path:
            continue

        # HOOK TITLE = câu đầu tiên
        hook = short_text.split(".")[0][:70]

        # VIDEO
        video_path = create_shorts(
            tts_path,
            hook,
            f"{eid}_{idx}",
            name,
            script_path,
            custom_image_path=image_path,
            base_bg_path=base_bg
        )

        if not video_path:
            continue

        # UPLOAD
        upload_video(
            video_path,
            {
                "Title": f"{hook} | #Shorts",
                "Summary": f"Shorts about {name}",
                "Tags": ["shorts", "history", name.lower()]
            }
        )

        sleep(8)  # tránh rate limit

    logger.info("✅ ALL SHORTS DONE")


# ============================================================
# 🚀 MAIN
# ============================================================

def main():
    setup_environment()

    task = fetch_content()
    if not task:
        logger.info("No pending tasks.")
        return

    data = task["data"]
    episode_id = str(data["ID"])
    text_hash = data.get("text_hash")

    logger.info(f"🚀 PIPELINE START: {episode_id}")

    long_result = process_long_video(data)
    if not long_result:
        logger.error("❌ LONG FAILED – STOP")
        return

    process_5_shorts(
        long_result["script_path"],
        long_result["image_path"],
        data
    )

    cleanup_temp_files(episode_id, text_hash)
    logger.info("🎉 FULL PIPELINE SUCCESS")


if __name__ == "__main__":
    main()
