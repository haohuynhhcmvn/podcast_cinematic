# scripts/glue_pipeline.py
import logging
import os
import sys
from time import sleep
from datetime import datetime, timedelta, timezone

# Project Path Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils import setup_environment, get_path, cleanup_temp_files 
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_multi_short_scripts
from auto_music_sfx import auto_music_sfx
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
    if not task:
        logger.info("ℹ️ Không có task pending.")
        return

    data = task["data"]
    ws, row_idx = task["worksheet"], task["row_idx"]
    episode_id = str(data.get('ID'))
    name = data.get('Name')
    now = datetime.now(timezone.utc)

    logger.info(f"▶️ BẮT ĐẦU PIPELINE: {name} (ID: {episode_id})")

    # 1. TẠO ẢNH NHÂN VẬT (DÙNG CHUNG)
    char_img = get_path("assets", "temp", f"{episode_id}_raw_ai.png")
    if not os.path.exists(char_img):
        char_img = generate_character_image(name, char_img)

    # 2. XỬ LÝ VIDEO DÀI (Công chiếu sau 2 giờ)
    long_video_id = None
    long_res = generate_long_script(data)
    if long_res:
        script_path = long_res["script_path"]
        yt_title = long_res["metadata"].get("youtube_title", f"{name} Story")
        
        tts = create_tts(script_path, episode_id, mode="long")
        if tts:
            audio = auto_music_sfx(tts, episode_id)
            video = create_video(audio, episode_id, custom_image_path=char_img, title_text=yt_title)
            
            if video:
                thumb = get_path("outputs", "thumbnails", f"{episode_id}_thumb.jpg")
                add_text_to_thumbnail(char_img, yt_title.upper(), thumb)
                
                # Hẹn giờ T+2h
                long_schedule = (now + timedelta(hours=2)).isoformat()
                up_res = upload_video(video, long_res["metadata"], thumbnail_path=thumb, scheduled_time=long_schedule)
                
                if isinstance(up_res, dict):
                    long_video_id = up_res.get('video_id')

    # 3. XỬ LÝ 5 SHORTS (T+2h, T+6h, T+10h, T+14h, T+18h)
    shorts_count = 0
    related_link = f"https://youtu.be/{long_video_id}" if long_video_id else ""
    
    # Lấy kịch bản từ file long vừa tạo
    long_txt = get_path("data", "episodes", f"{episode_id}_long_en.txt")
    short_tasks = generate_multi_short_scripts(data, long_txt)

    for i, t in enumerate(short_tasks):
        s_id = f"{episode_id}_s{t['index']}"
        s_tts = create_tts(t['script_path'], s_id, mode="short")
        
        if s_tts:
            with open(t['title_path'], "r", encoding="utf-8") as f: s_title = f.read().strip()
            
            s_video = create_shorts(s_id, char_img, t['script_path'], s_tts, hook_title=s_title)
            
            if s_video:
                # Tính giờ hẹn
                delay = 2 + (i * 4)
                s_schedule = (now + timedelta(hours=delay)).isoformat()
                
                # Metadata kèm link video liên quan
                s_meta = {
                    "Title": f"{s_title} #Shorts",
                    "Summary": f"Watch full story: {related_link}\n\nHistorical tale of {name}.",
                    "Tags": ["shorts", "history", "legend"]
                }
                
                if upload_video(s_video, s_meta, scheduled_time=s_schedule) != "FAILED":
                    shorts_count += 1

    # 4. HOÀN TẤT
    status = f"DONE_LONG_{'OK' if long_video_id else 'FAIL'}_SHORTS_{shorts_count}"
    try:
        header = ws.row_values(1)
        st_col = header.index("Status") + 1 if "Status" in header else 6
        ws.update_cell(row_idx, st_col, status)
    except: pass
    
    cleanup_temp_files(episode_id, data.get('text_hash'))
    logger.info(f"🏁 KẾT THÚC: {status}")

if __name__ == "__main__":
    main()
