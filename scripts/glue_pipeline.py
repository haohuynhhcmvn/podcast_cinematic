# scripts/glue_pipeline.py
import logging
import sys
import os
from time import sleep

# Đảm bảo project root nằm trong sys.path
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

def safe_update_status(ws, row_idx, col_idx, status):
    try:
        if not ws: return
        header = ws.row_values(1)
        idx = header.index("Status") + 1 if "Status" in header else 6
        ws.update_cell(row_idx, idx, status)
        logger.info(f"STATUS_UPDATE: Row {row_idx} -> {status}")
    except Exception as e:
        logger.error(f"❌ Lỗi update status: {e}")

def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("ℹ️ Không có task pending.")
        return

    data = task["data"]
    task_meta = {"row_idx": task["row_idx"], "col_idx": task["col_idx"], "worksheet": task["worksheet"]}
    ws, row_idx, col_idx = task["worksheet"], task["row_idx"], task["col_idx"]
    episode_id = str(data.get('ID'))
    name = data.get('Name')

    logger.info(f"▶️ BẮT ĐẦU PIPELINE CHO: {name} (ID: {episode_id})")

    # =========================================================
    # PHASE 1: TẠO ẢNH NHÂN VẬT (CHỈ 1 LẦN - TIẾT KIỆM $)
    # =========================================================
    char_img_path = get_path("assets", "temp", f"{episode_id}_raw_ai.png")
    if not os.path.exists(char_img_path):
        logger.info(f"🎨 Đang tạo ảnh nhân vật cho {name}...")
        char_img_path = generate_character_image(name, char_img_path)

    # =========================================================
    # PHASE 2: XỬ LÝ VIDEO DÀI (LONG-FORM)
    # =========================================================
    logger.info("📺 --- ĐANG XỬ LÝ VIDEO DÀI ---")
    long_res = generate_long_script(data)
    long_ok = False
    
    if long_res:
        script_path = long_res["script_path"]
        meta = long_res.get("metadata", {})
        yt_title = meta.get("youtube_title", f"{name} Untold Story")
        
        # Tạo Audio & Render
        tts_path = create_tts(script_path, episode_id, mode="long")
        if tts_path:
            mixed_audio = auto_music_sfx(tts_path, episode_id)
            video_path = create_video(mixed_audio, episode_id, custom_image_path=char_img_path, title_text=yt_title)
            
            if video_path:
                # Thumbnail & Upload
                thumb_path = get_path("outputs", "thumbnails", f"{episode_id}_thumb.jpg")
                add_text_to_thumbnail(char_img_path, yt_title.upper(), thumb_path)
                
                upload_res = upload_video(video_path, {"Title": yt_title, "Summary": meta.get("youtube_description", "")}, thumbnail_path=thumb_path)
                if upload_res != "FAILED":
                    long_ok = True
                    logger.info("✅ Upload Video Dài thành công!")

    # =========================================================
    # PHASE 3: XỬ LÝ 05 VIDEO SHORTS (VÒNG LẶP)
    # =========================================================
    
    logger.info("🎬 --- ĐANG XỬ LÝ 05 VIDEO SHORTS ---")
    long_script_file = get_path("data", "episodes", f"{episode_id}_long_en.txt")
    short_tasks = generate_multi_short_scripts(data, long_script_file)
    
    shorts_success_count = 0
    for t in short_tasks:
        idx = t['index']
        short_id = f"{episode_id}_s{idx}"
        logger.info(f"🚀 Đang xử lý Shorts #{idx}/5 (ID: {short_id})")

        # TTS cho từng Short
        s_audio = create_tts(t['script_path'], short_id, mode="short")
        
        if s_audio:
            with open(t['title_path'], "r", encoding="utf-8") as f: s_title = f.read().strip()
            
            # Render Shorts
            s_video = create_shorts(short_id, char_img_path, t['script_path'], s_audio, hook_title=s_title)
            
            if s_video:
                # Upload Shorts
                s_meta = {"Title": f"{s_title} #Shorts", "Summary": f"Story of {name}"}
                if upload_video(s_video, s_meta) != "FAILED":
                    shorts_success_count += 1
                    logger.info(f"✅ Đã upload Short {idx}")

    # =========================================================
    # PHASE 4: DỌN DẸP & CẬP NHẬT
    # =========================================================
    final_status = f"DONE_LONG_{'OK' if long_ok else 'FAIL'}_SHORTS_{shorts_success_count}"
    safe_update_status(ws, row_idx, col_idx, final_status)
    
    cleanup_temp_files(episode_id, data.get('text_hash'))
    logger.info(f"🏁 PIPELINE HOÀN TẤT: {final_status}")

if __name__ == "__main__":
    main()
