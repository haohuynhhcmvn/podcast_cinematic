import logging
import sys
import os

# Setup Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import setup_environment
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_short_script
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from auto_music_sfx import auto_music_sfx
from upload_youtube import upload_video

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    setup_environment()
    
    # 1. Fetch
    task = fetch_content()
    if not task: return
    data = task['data']
    eid = data['ID']

    # --- LUỒNG VIDEO DÀI ---
    logger.info("🎬 --- BẮT ĐẦU VIDEO DÀI ---")
    script_long = generate_long_script(data)
    if script_long:
        tts_long = create_tts(script_long, eid, "long")
        if tts_long:
            # Mix nhạc chỉ cho video dài
            audio_final = auto_music_sfx(tts_long, eid)
            if audio_final:
                vid_path = create_video(audio_final, eid)
                if vid_path:
                    upload_video(vid_path, data)

    # --- LUỒNG SHORTS ---
    logger.info("📱 --- BẮT ĐẦU SHORTS ---")
    script_short = generate_short_script(data)
    if script_short:
        tts_short = create_tts(script_short, eid, "short")
        if tts_short:
            create_shorts(tts_short, eid)

    # Update Sheet
    task['worksheet'].update_cell(task['row_idx'], task['col_idx'], 'COMPLETED')
    logger.info("🎉 DONE ALL TASKS")

if __name__ == "__main__":
    main()
