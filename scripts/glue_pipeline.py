import logging
import sys
import os
from time import sleep
from concurrent.futures import ThreadPoolExecutor

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from utils import setup_environment, cleanup_temp_files
from fetch_content import fetch_content
from generate_script import generate_long_script, split_long_script_to_5_shorts
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_one_short(short_cfg, data, image_path):
    idx = short_cfg["index"]
    logger.info(f"▶️ SHORT {idx}/5 START")

    script = short_cfg["script"]
    title = open(short_cfg["title"], encoding="utf-8").read().strip()

    tts = create_tts(script, data["ID"], f"short_{idx}")
    video = create_shorts(
        tts,
        title,
        f"{data['ID']}_{idx}",
        data["Name"],
        script,
        custom_image_path=image_path
    )

    upload_video(video, {
        "Title": f"{title} | #Shorts",
        "Summary": title,
        "Tags": ["shorts", "history"]
    })

    logger.info(f"✅ SHORT {idx} DONE")


def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("No task.")
        return

    data = task["data"]
    eid = str(data["ID"])

    logger.info("🎬 START LONG VIDEO")
    long_res = generate_long_script(data)
    video = create_video(long_res["script_path"], eid)
    upload_video(video, long_res["metadata"])
    logger.info("✅ LONG VIDEO DONE")

    logger.info("📱 GENERATING 5 SHORTS FROM LONG SCRIPT")
    shorts = split_long_script_to_5_shorts(data, long_res["script_path"])

    image_path = f"assets/temp/{eid}_raw_ai.png"

    with ThreadPoolExecutor(max_workers=4) as pool:
        for s in shorts:
            pool.submit(process_one_short, s, data, image_path)

    cleanup_temp_files(eid)
    logger.info("🎉 PIPELINE FINISHED")


if __name__ == "__main__":
    main()
