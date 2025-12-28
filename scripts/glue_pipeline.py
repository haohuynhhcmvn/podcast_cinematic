# scripts/glue_pipeline.py
import logging
import os
import sys
from time import sleep

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils import setup_environment, cleanup_temp_files
from fetch_content import fetch_content
from generate_script import (
    generate_long_script,
    split_long_script_to_5_shorts,
    generate_5_short_titles
)
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    setup_environment()

    task = fetch_content()
    if not task:
        logger.info("No pending task.")
        return

    data = task["data"]
    episode_id = str(data.get("ID"))

    # ================= LONG VIDEO =================
    logger.info("🎬 GENERATING LONG VIDEO...")
    long_res = generate_long_script(data)
    if not long_res:
        return

    long_script = long_res["script_path"]
    tts_long = create_tts(long_script, episode_id, "long")
    if not tts_long:
        return

    long_video = create_video(tts_long, episode_id)
    upload_video(long_video, long_res["metadata"])

    sleep(5)

    # ================= SHORTS =================
    logger.info("🎬 GENERATING SHORTS...")
    short_scripts = split_long_script_to_5_shorts(long_script, data)
    short_titles = generate_5_short_titles(short_scripts, data)

    for i in range(5):
        tts = create_tts(short_scripts[i], f"{episode_id}_{i+1}", "short")
        if not tts:
            continue

        shorts_video = create_shorts(
            tts,
            open(short_titles[i]).read(),
            f"{episode_id}_{i+1}",
            data.get("Name"),
            short_scripts[i]
        )

        upload_video(shorts_video, {
            "Title": open(short_titles[i]).read(),
            "Summary": f"Short about {data.get('Name')}",
            "Tags": ["shorts", "history"]
        })

        sleep(3)

    cleanup_temp_files(episode_id, data.get("text_hash"))
    logger.info("🎉 ALL DONE!")


if __name__ == "__main__":
    main()
