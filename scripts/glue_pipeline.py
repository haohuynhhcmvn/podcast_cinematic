# ===scripts/glue_pipeline.py===

import logging
import sys
import os
from time import sleep
import random # Thư viện cần thiết cho jitter trong backoff

# --- Cấu hình Path (Đảm bảo các module script được import) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# --- Imports Module ---
from utils import setup_environment, get_path
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_short_script
from auto_music_sfx import auto_music_sfx
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video

# --- Imports tùy chọn (Sử dụng try/except để tránh lỗi Import) ---
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
#  UTILITIES & STATUS MANAGEMENT
# =========================================================
def safe_update_status(ws, row_idx, col_idx, status):
    """Cập nhật trạng thái vào Google Sheet an toàn."""
    try:
        if not ws: return
        if col_idx and isinstance(col_idx, int):
            ws.update_cell(row_idx, col_idx, status)
        else:
            header = ws.row_values(1)
            # Tìm cột "Status" hoặc dùng cột thứ 6 làm mặc định
            idx = header.index("Status") + 1 if "Status" in header else 6
            ws.update_cell(row_idx, idx, status)
        logger.info(f"Đã cập nhật row {row_idx} -> {status}")
    except Exception as e:
        logger.error(f"Lỗi update status: {e}")

def try_update_youtube_id(ws, row_idx, video_id):
    """Cập nhật YouTube ID vào Google Sheet an toàn."""
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

def cleanup_temp_files(eid, keep_ai_image=False):
    """ Xóa các file tạm thời, giữ lại ảnh AI nếu cần tái sử dụng. """
    temp_files = [
        get_path('assets', 'temp', "char_vignette_overlay.png"), # File tạm từ MoviePy/Pillow
    ]
    
    ai_image_path = get_path("assets", "temp", f"{eid}_raw_ai.png")
    
    if not keep_ai_image and os.path.exists(ai_image_path):
        temp_files.append(ai_image_path)
        
    for fpath in temp_files:
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                logger.debug(f"🗑️ Đã xóa file tạm: {os.path.basename(fpath)}")
            except Exception as e:
                logger.warning(f"Không thể xóa file tạm {fpath}: {e}")

# =========================================================
#  FULL VIDEO PROCESSING (LONG)
# =========================================================
def process_long_video(data, task_meta):
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')
    eid = data.get('ID')
    name = data.get('Name')
    long_success = False 

    logger.info(f"🎬 BẮT ĐẦU VIDEO DÀI: {eid} – {name}")

    try:
        # 1. Generate Script
        long_res = generate_long_script(data)
        if not long_res:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_GEN_LONG')
            return False

        script_path = long_res["script_path"]
        meta = long_res.get("metadata", {})
        youtube_title = meta.get("youtube_title", f"{name} – The Untold Story")
        
        # 2. AI Image & Thumbnail
        dalle_char_path = None
        final_thumbnail_path = None
        raw_img_path = get_path("assets", "temp", f"{eid}_raw_ai.png")
        
        # SMART CACHE: Tái sử dụng ảnh AI nếu đã có
        if os.path.exists(raw_img_path):
            logger.info(f"💰 Đã tìm thấy ảnh nhân vật cũ. Dùng lại.")
            dalle_char_path = raw_img_path
        elif generate_character_image:
            try:
                logger.info(f"🎨 Ảnh chưa có. Gọi DALL-E tạo mới: {name}...")
                dalle_char_path = generate_character_image(name, raw_img_path) 
            except Exception as e:
                logger.error(f"⚠️ Lỗi tạo ảnh AI: {e}")

        # Tạo Thumbnail
        if dalle_char_path and add_text_to_thumbnail:
            thumb_text = youtube_title.upper() 
            thumb_out = get_path("outputs", "thumbnails", f"{eid}_thumb.jpg")
            final_thumbnail_path = add_text_to_thumbnail(dalle_char_path, thumb_text, thumb_out)

        # 3. TTS (Text-to-Speech)
        tts = None
        for i in range(1, 4): # Thử tối đa 3 lần
            tts = create_tts(script_path, eid, "long")
            if tts: break
            # Exponential Backoff + Jitter
            wait_time = (2 ** i) + random.uniform(0, 1) 
            logger.warning(f"TTS lần {i} thất bại. Đang chờ {wait_time:.2f}s để thử lại...")
            sleep(wait_time)
            
        if not tts:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_TTS_LONG')
            return False

        # 4. Audio Mix (Nhạc nền + TTS)
        mixed = auto_music_sfx(tts, eid)
        if not mixed: return False

        # 5. Render Video (Dùng VIDEO NỀN ĐỘNG)
        # Hàm create_video đã được cập nhật để TỰ ĐỘNG tìm assets/video/long_background.mp4
        video_path = create_video(
            mixed, 
            eid, 
            custom_image_path=dalle_char_path,
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
        long_success = True
        return True

    except Exception as e:
        logger.error(f"ERROR LONG VIDEO: {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'ERROR_LONG')
        return False
        
    finally:
        # Dọn dẹp: Giữ lại ảnh AI nếu Long Video thành công (dùng cho Shorts)
        cleanup_temp_files(eid, keep_ai_image=long_success) 


# =========================================================
#  SHORTS PROCESSING
# =========================================================
def process_shorts(data, task_meta):
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')

    eid = data.get('ID')
    name = data.get('Name')
    logger.info(f"🎬 BẮT ĐẦU SHORTS: {eid}")

    try:
        # 1. Script
        script_path, title_path = generate_short_script(data)
        if not title_path or not os.path.exists(title_path):
            return False
            
        with open(title_path, "r", encoding="utf-8") as f: hook_title = f.read().strip()

        # 2. TTS (Tái sử dụng backoff)
        tts = None
        for i in range(1, 4):
            tts = create_tts(script_path, eid, "short")
            if tts: break
            wait_time = (2 ** i) + random.uniform(0, 1) 
            sleep(wait_time)
        if not tts: 
            safe_update_status(ws, row_idx, col_idx, 'FAILED_TTS_SHORTS')
            return False

        # 3. Lấy ảnh AI (Thường đã được tạo từ Long Video và nằm trong /assets/temp)
        dalle_char_path = get_path("assets", "temp", f"{eid}_raw_ai.png")
        
        if not os.path.exists(dalle_char_path):
            logger.warning(f"⚠️ Ảnh chưa có. Thử tạo mới cho Shorts.")
            if generate_character_image:
                try:
                    dalle_char_path = generate_character_image(name, dalle_char_path)
                except Exception:
                    dalle_char_path = None
            else:
                dalle_char_path = None

        # 4. Lấy nền Shorts cố định (Tĩnh)
        base_bg_path = get_path('assets', 'images', 'default_background_shorts.png')
        if not os.path.exists(base_bg_path):
            logger.warning("⚠️ Thiếu background Shorts. Sử dụng nền màu mặc định.")
            base_bg_path = None

        # 5. Render Shorts
        shorts_path = create_shorts(
            tts, hook_title, eid, 
            name, 
            script_path, 
            custom_image_path=dalle_char_path,
            base_bg_path=base_bg_path
        )
        
        if not shorts_path: 
            safe_update_status(ws, row_idx, col_idx, 'FAILED_RENDER_SHORTS')
            return False

        # 6. Upload
        upload_data = {
            "Title": f"{hook_title} – {name} | #Shorts",
            "Summary": f"Shorts about {name}",
            "Tags": ["shorts", "history", "legend"]
        }
        upload_result = upload_video(shorts_path, upload_data)
        
        if not upload_result or upload_result == 'FAILED':
            safe_update_status(ws, row_idx, col_idx, 'FAILED_UPLOAD_SHORTS')
            return False

        safe_update_status(ws, row_idx, col_idx, 'UPLOADED_SHORTS')
        return True

    except Exception as e:
        logger.error(f"ERROR SHORTS: {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'ERROR_SHORTS')
        return False
    
    # Không cần cleanup ở đây vì ảnh AI được xử lý ở Long Video


def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("Không có task pending.")
        return

    data = task["data"]
    task_meta = {"row_idx": task["row_idx"], "col_idx": task["col_idx"], "worksheet": task["worksheet"]}

    logger.info(f"▶️ ĐANG XỬ LÝ TASK ID={data.get('ID')} – {data.get('Name')}")
    
    # 1. Xử lý Long Video
    long_ok = process_long_video(data, task_meta)
    
    # 2. Xử lý Shorts (Chạy độc lập sau 1 khoảng nghỉ)
    sleep(10) 
    short_ok = process_shorts(data, task_meta)

    if long_ok and short_ok: logger.info("🎉 FULL SUCCESS!")

if __name__ == "__main__":
    main()
