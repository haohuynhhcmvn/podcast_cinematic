# scripts/glue_pipeline.py
import os
import sys
import logging
from time import sleep
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed

# setup path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.append(PROJECT_ROOT)

from utils import setup_environment, cleanup_temp_files
from fetch_content import fetch_content
from generate_script import generate_long_script, split_long_to_5_shorts
from create_tts import create_tts
from auto_music_sfx import auto_music_sfx
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video
from generate_image import generate_character_image
from create_thumbnail import add_text_to_thumbnail

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def render_single_short(args):
    index, short_script, hook, eid, name, image_path = args
    logger.info(f"🎬 [SHORT {index}] Rendering started")

    tts = create_tts(short_script, f"{eid}_{index}", mode="short")
    video = create_shorts(
        tts,
        hook,
        f"{eid}_{index}",
        name,
        short_script,
        custom_image_path=image_path
    )

    logger.info(f"✅ [SHORT {index}] Render completed")
    return index, video


def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("🟢 No pending task")
        return

    data = task["data"]
    eid = str(data["ID"])
    name = data["Name"]

    logger.info("======================================")
    logger.info(f"🎬 START PIPELINE | ID={eid} | {name}")
    logger.info("======================================")

    base_publish_time = datetime.now() + timedelta(hours=2)

    # ===== LONG VIDEO =====
    logger.info("🧠 PHASE 1: Generate long script")
    long_data = generate_long_script(data)
    script_path = long_data["script_path"]
    meta = long_data["metadata"]

    logger.info("🖼️ PHASE 2: Generate character image")
    image_path = generate_character_image(name, f"assets/temp/{eid}_char.png")

    logger.info("🎙️ PHASE 3: TTS long")
    tts_long = create_tts(script_path, eid, mode="long")

    logger.info("🎵 PHASE 4: Audio mix")
    mixed_audio = auto_music_sfx(tts_long, eid)

    logger.info("🎥 PHASE 5: Render long video")
    long_video = create_video(
        mixed_audio,
        eid,
        custom_image_path=image_path,
        title_text=meta["youtube_title"]
    )

    logger.info("📤 PHASE 6: Upload long video")
    upload_video(
        long_video,
        {
            "Title": meta["youtube_title"],
            "Summary": meta["youtube_description"],
            "Tags": meta["youtube_tags"]
        },
        thumbnail_path=add_text_to_thumbnail(
            image_path,
            meta["youtube_title"],
            f"outputs/thumbnails/{eid}.jpg"
        ),
        publish_at=base_publish_time
    )

    # ===== SHORTS =====
    logger.info("📱 PHASE 7: Split long → 5 shorts")
    shorts_data = split_long_to_5_shorts(script_path)

    logger.info("⚡ PHASE 8: Render 5 shorts in parallel (x4 speed)")
    rendered_shorts = {}

    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                render_single_short,
                (i + 1, s["script"], s["hook"], eid, name, image_path)
            )
            for i, s in enumerate(shorts_data)
        ]

        for future in as_completed(futures):
            idx, path = future.result()
            rendered_shorts[idx] = path

    logger.info("📤 PHASE 9: Upload & schedule shorts")

    for i in range(1, 6):
        publish_time = base_publish_time + timedelta(hours=(i - 1) * 4)
        logger.info(f"📅 SHORT {i} scheduled at {publish_time}")

        upload_video(
            rendered_shorts[i],
            {
                "Title": f"{shorts_data[i-1]['hook']} – {name} | #Shorts",
                "Summary": f"Short about {name}",
                "Tags": ["shorts", "history", "legend"]
            },
            publish_at=publish_time
        )

    cleanup_temp_files(eid, data.get("text_hash"))

    logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY")
    logger.info("======================================")


if __name__ == "__main__":
    main()
