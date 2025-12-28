# scripts/glue_pipeline.py
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

# Setup path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path: sys.path.append(project_root)

from utils import setup_environment, get_path, cleanup_temp_files 
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_multi_short_scripts
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video
from generate_image import generate_character_image
from create_thumbnail import add_text_to_thumbnail

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    setup_environment()
    task = fetch_content()
    if not task: return

    data = task["data"]
    episode_id = str(data.get('ID')) # Đảm bảo ID là chuỗi
    name = data.get('Name')
    now = datetime.now(timezone.utc)

    # 1. ẢNH AI (DÙNG CHUNG)
    char_img = get_path("assets", "temp", f"{episode_id}_raw_ai.png")
    if not os.path.exists(char_img):
        char_img = generate_character_image(name, char_img)

    # 2. XỬ LÝ VIDEO DÀI (Công chiếu sau 2h)
    long_video_id = None
    long_res = generate_long_script(data)
    
    if long_res and isinstance(long_res, dict):
        script_path = long_res["script_path"]
        meta = long_res["metadata"]
        
        tts = create_tts(script_path, episode_id, mode="long")
        if tts:
            # Gán tiêu đề tự sinh vào video
            video = create_video(tts, episode_id, custom_image_path=char_img, title_text=meta["Title"])
            
            if video:
                thumb = get_path("outputs", "thumbnails", f"{episode_id}_thumb.jpg")
                add_text_to_thumbnail(char_img, meta["Title"].upper(), thumb)
                
                # Hẹn giờ T+2h
                sched_long = (now + timedelta(hours=2)).isoformat()
                up_res = upload_video(video, meta, thumbnail_path=thumb, scheduled_time=sched_long)
                
                if isinstance(up_res, dict):
                    long_video_id = up_res.get('video_id')

    # 3. XỬ LÝ 5 SHORTS (Cách nhau 4h)
    
    long_txt = get_path("data", "episodes", f"{episode_id}_long_en.txt")
    if os.path.exists(long_txt):
        short_tasks = generate_multi_short_scripts(data, long_txt)
        related_url = f"https://youtu.be/{long_video_id}" if long_video_id else ""

        for i, t in enumerate(short_tasks):
            s_id = f"{episode_id}_s{t['index']}"
            s_tts = create_tts(t['script_path'], s_id, mode="short")
            
            if s_tts:
                with open(t['title_path'], "r", encoding="utf-8") as f: s_title = f.read().strip()
                s_video = create_shorts(s_id, char_img, t['script_path'], s_tts, hook_title=s_title)
                
                if s_video:
                    delay = 2 + (i * 4)
                    sched_s = (now + timedelta(hours=delay)).isoformat()
                    s_meta = {
                        "Title": f"{s_title} #Shorts",
                        "Summary": f"Xem bản đầy đủ tại: {related_url}",
                        "Tags": ["shorts", "history"]
                    }
                    upload_video(s_video, s_meta, scheduled_time=sched_s)

    cleanup_temp_files(episode_id, data.get('text_hash'))
    logger.info("✅ HỆ THỐNG ĐÃ PHỤC HỒI!")

if __name__ == "__main__":
    main()
