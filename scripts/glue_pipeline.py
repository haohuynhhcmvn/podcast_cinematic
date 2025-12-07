#=== scripts/glue_pipeline.py ===

import logging
import sys
import os
from time import sleep

# ensure project scripts folder is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils import setup_environment, get_path
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_short_script
from auto_music_sfx import auto_music_sfx
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video

try:
    from generate_image import generate_character_image
    from create_thumbnail import add_text_to_thumbnail
except ImportError:
    logging.warning("⚠️ Module tạo ảnh/thumbnail chưa có.")
    generate_character_image = None
    add_text_to_thumbnail = None


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =========================================================
#  SAFE UPDATE STATUS
# =========================================================
def safe_update_status(ws, row_idx, col_idx, status):
    try:
        if not ws: return
        if col_idx and isinstance(col_idx, int):
            ws.update_cell(row_idx, col_idx, status)
        else:
            header = ws.row_values(1)
            idx = header.index("Status") + 1 if "Status" in header else 6
            ws.update_cell(row_idx, idx, status)
        logger.info(f"Đã cập nhật row {row_idx} -> {status}")
    except Exception as e:
        logger.error(f"Lỗi update status: {e}")

def try_update_youtube_id(ws, row_idx, video_id):
    if not ws or not video_id: return
    try:
        header = ws.row_values(1)
        cols = ['YouTubeID', 'VideoID', 'youtube_id', 'video_id']
        for name in cols:
            if name in header:
                col = header.index(name) + 1
                ws.update_cell(row_idx, col, video_id)
                return
    except Exception: pass

# =========================================================
#  FULL VIDEO PROCESSING (LONG)
# =========================================================
def process_long_video(data, task_meta):
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')

    eid = data.get('ID')
    name = data.get('Name')

    logger.info(f"🎬 BẮT ĐẦU VIDEO DÀI: {eid} – {name}")

    try:
        # 1. Script
        long_res = generate_long_script(data)
        if not long_res:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_GEN_LONG')
            return False

        script_path = long_res["script_path"]
        meta = long_res.get("metadata", {})
        youtube_title = meta.get("youtube_title", f"{name} – The Untold Story")
        
        # 2. Ảnh AI & Thumbnail (SMART CACHE)
        dalle_char_path = None
        final_thumbnail_path = None
        
        base_bg_path = get_path('assets', 'images', 'default_background.png')
        raw_img_path = get_path("assets", "temp", f"{eid}_raw_ai.png")
        
        # [SMART CHECK] Kiểm tra xem ảnh đã tồn tại chưa
        if os.path.exists(raw_img_path):
             logger.info(f"💰 Đã tìm thấy ảnh nhân vật cũ ({raw_img_path}). Dùng lại để tiết kiệm $0.04.")
             dalle_char_path = raw_img_path
        else:
             # Chỉ tạo mới khi chưa có
             if generate_character_image:
                try:
                    logger.info(f"🎨 Ảnh chưa có. Gọi DALL-E tạo mới: {name}...")
                    dalle_char_path = generate_character_image(name, raw_img_path) 
                except Exception as e:
                    logger.error(f"⚠️ Lỗi tạo ảnh AI: {e}")

        # Tạo Thumbnail (Luôn tạo lại vì tiêu đề có thể đổi)
        if dalle_char_path and add_text_to_thumbnail:
            thumb_text = youtube_title.upper() 
            thumb_out = get_path("outputs", "thumbnails", f"{eid}_thumb.jpg")
            final_thumbnail_path = add_text_to_thumbnail(dalle_char_path, thumb_text, thumb_out)

        # 3. TTS
        tts = None
        for i in range(3):
            tts = create_tts(script_path, eid, "long")
            if tts: break
            sleep(2)
        if not tts:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_TTS_LONG')
            return False

        # 4. Audio Mix
        mixed = auto_music_sfx(tts, eid)
        if not mixed: return False

        # 5. Render Video (Hybrid)
        video_path = create_video(
            mixed, 
            eid, 
            custom_image_path=dalle_char_path,
            base_bg_path=base_bg_path, 
            title_text=youtube_title
        )
        
        if not video_path:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_RENDER_LONG')
            return False

        # 6. Upload
        upload_payload = {
            "Title": youtube_title,
            "Summary": meta.get("youtube_description", ""),
            "Tags": meta.get("youtube_tags", [])
        }
        upload_result = upload_video(video_path, upload_payload, thumbnail_path=final_thumbnail_path)
        
        if not upload_result or upload_result == "FAILED":
            safe_update_status(ws, row_idx, col_idx, 'FAILED_UPLOAD_LONG')
            return False

        if isinstance(upload_result, dict):
            try_update_youtube_id(ws, row_idx, upload_result.get("video_id"))

        safe_update_status(ws, row_idx, col_idx, 'UPLOADED_LONG')
        return True

    except Exception as e:
        logger.error(f"ERROR LONG VIDEO: {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'ERROR_LONG')
        return False


# =========================================================
#  SHORTS
# =========================================================
def process_shorts(data, task_meta):
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')

    eid = data.get('ID')
    name = data.get('Name')
    logger.info(f"🎬 BẮT ĐẦU SHORTS: {eid}")

    try:
        script_path, title_path = generate_short_script(data)
        if not title_path or not os.path.exists(title_path):
             return False
             
        with open(title_path, "r", encoding="utf-8") as f: hook_title = f.read().strip()

        # TTS
        tts = None
        for i in range(3):
            tts = create_tts(script_path, eid, "short")
            if tts: break
            sleep(2)
        if not tts: return False

        # --- [SMART CHECK] KIỂM TRA ẢNH TỒN TẠI ---
        dalle_char_path = get_path("assets", "temp", f"{eid}_raw_ai.png")
        
        if os.path.exists(dalle_char_path):
            logger.info(f"💰 Đã tìm thấy ảnh nhân vật cũ ({dalle_char_path}). Shorts sẽ dùng lại.")
        else:
            # Chỉ tạo khi chưa có
            logger.warning(f"⚠️ Ảnh chưa có. Shorts gọi DALL-E tạo mới: {name}...")
            if generate_character_image:
                try:
                    dalle_char_path = generate_character_image(name, dalle_char_path)
                except Exception:
                    dalle_char_path = None
            else:
                dalle_char_path = None
        # ------------------------------------------

        # Lấy nền Shorts cố định
        base_bg_path = get_path('assets', 'images', 'default_background_shorts.png')
        if not os.path.exists(base_bg_path):
             logger.warning("⚠️ Thiếu background Shorts")
             base_bg_path = None

        # Render Shorts
        shorts_path = create_shorts(
            tts, hook_title, eid, 
            name, 
            script_path, 
            custom_image_path=dalle_char_path,
            base_bg_path=base_bg_path
        )
        
        if not shorts_path: return False

        # Upload
        upload_data = {
            "Title": f"{hook_title} – {name} | #Shorts",
            "Summary": f"Shorts about {name}",
            "Tags": ["shorts", "history"]
        }
        upload_result = upload_video(shorts_path, upload_data)
        
        if not upload_result or upload_result == 'FAILED':
            safe_update_status(ws, row_idx, col_idx, 'FAILED_UPLOAD_SHORTS')
            return False

        safe_update_status(ws, row_idx, col_idx, 'UPLOADED_SHORTS')
        return True

    except Exception as e:
        logger.error(f"ERROR SHORTS: {e}", exc_info=True)
        return False


def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("Không có task pending.")
        return

    data = task["data"]
    task_meta = {"row_idx": task["row_idx"], "col_idx": task["col_idx"], "worksheet": task["worksheet"]}

    logger.info(f"▶️ ĐANG XỬ LÝ TASK ID={data.get('ID')} – {data.get('Name')}")
    
    long_ok = process_long_video(data, task_meta)
    sleep(10)
    short_ok = process_shorts(data, task_meta)

    if long_ok and short_ok: logger.info("🎉 FULL SUCCESS!")

if __name__ == "__main__":
    main()
