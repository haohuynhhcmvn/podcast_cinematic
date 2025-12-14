# === scripts/glue_pipeline.py ===

import logging
import sys
import os
from time import sleep

# ensure project scripts folder is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Đã THÊM cleanup_temp_files
from utils import setup_environment, get_path, cleanup_temp_files 
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
# ... (Giữ nguyên các hàm safe_update_status và try_update_youtube_id) ...
def safe_update_status(ws, row_idx, col_idx, status):
    try:
        if not ws: return
        if col_idx and isinstance(col_idx, int):
            ws.update_cell(row_idx, col_idx, status)
        else:
            header = ws.row_values(1)
            idx = header.index("Status") + 1 if "Status" in header else 6
            ws.update_cell(row_idx, idx, status)
        logger.info(f"STATUS_UPDATE: Row {row_idx} -> {status}")
    except Exception as e:
        logger.error(f"❌ Lỗi update status: {e}")

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

    logger.info(f"=========================================================")
    logger.info(f"🎬 BẮT ĐẦU [LONG]: ID={eid} – {name}")
    logger.info(f"=========================================================")

    try:
        # 1. SCRIPT
        logger.info("PHASE 1/6: Đang gọi AI tạo Long Script & Metadata...")
        long_res = generate_long_script(data)
        if not long_res:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_GEN_LONG')
            return False

        script_path = long_res["script_path"]
        meta = long_res.get("metadata", {})
        youtube_title = meta.get("youtube_title", f"{name} – The Untold Story")
        
        # 2. ẢNH AI & THUMBNAIL (SMART CACHE)
        logger.info("PHASE 2/6: Xử lý ảnh AI (Smart Cache) và Thumbnail...")
        dalle_char_path = None
        final_thumbnail_path = None
        
        base_bg_path = get_path('assets', 'images', 'default_background.png')
        raw_img_path = get_path("assets", "temp", f"{eid}_raw_ai.png")
        
        if os.path.exists(raw_img_path):
             logger.info(f"   (CACHE HIT): Dùng lại ảnh {raw_img_path} (Tiết kiệm tiền).")
             dalle_char_path = raw_img_path
        else:
             if generate_character_image:
                try:
                    logger.info(f"   (CACHE MISS): Gọi DALL-E tạo mới: {name}...")
                    dalle_char_path = generate_character_image(name, raw_img_path) 
                except Exception as e:
                    logger.error(f"⚠️ Lỗi tạo ảnh AI: {e}")

        if dalle_char_path and add_text_to_thumbnail:
            thumb_text = youtube_title.upper() 
            thumb_out = get_path("outputs", "thumbnails", f"{eid}_thumb.jpg")
            final_thumbnail_path = add_text_to_thumbnail(dalle_char_path, thumb_text, thumb_out)

        # 3. TTS
        logger.info("PHASE 3/6: Đang tạo giọng đọc (Edge-TTS Hard Retry)...")
        tts = None
        for i in range(3):
            tts = create_tts(script_path, eid, "long")
            if tts: break
            sleep(2)
        if not tts:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_TTS_LONG')
            return False

        # 4. AUDIO MIX
        logger.info("PHASE 4/6: Đang trộn nhạc nền (Auto Music SFX)...")
        mixed = auto_music_sfx(tts, eid)
        if not mixed:
             logger.error("❌ Lỗi trộn Audio Mix.")
             return False

        # 5. RENDER VIDEO
        logger.info("PHASE 5/6: Đang Render Video Long-form (Video Nền Động)...")
        video_path = create_video(
            mixed, 
            eid, 
            custom_image_path=dalle_char_path,
            title_text=youtube_title
        )
        
        if not video_path:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_RENDER_LONG')
            return False

        # 6. UPLOAD
        logger.info("PHASE 6/6: Đang Upload lên YouTube...")
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
        logger.info(f"✅ LONG VIDEO SUCCESS: {upload_result.get('video_id')}")
        return True

    except Exception as e:
        logger.error(f"❌ ERROR LONG VIDEO TỔNG: {e}", exc_info=True)
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
    
    logger.info(f"---------------------------------------------------------")
    logger.info(f"🎬 BẮT ĐẦU [SHORTS]: ID={eid}")
    logger.info(f"---------------------------------------------------------")


    try:
        # 1. SCRIPT
        logger.info("PHASE 1/5: Đang gọi AI tạo Short Script...")
        script_path, title_path = generate_short_script(data)
        if not title_path or not os.path.exists(title_path):
             logger.error("❌ Lỗi tạo Script Shorts.")
             return False
             
        with open(title_path, "r", encoding="utf-8") as f: hook_title = f.read().strip()

        # 2. TTS
        logger.info("PHASE 2/5: Đang tạo giọng đọc Shorts (Edge-TTS)...")
        tts = None
        for i in range(3):
            tts = create_tts(script_path, eid, "short")
            if tts: break
            sleep(2)
        if not tts:
             logger.error("❌ Lỗi TTS Shorts.")
             return False

        # 3. ẢNH AI (Smart Cache)
        logger.info("PHASE 3/5: Kiểm tra ảnh AI cho Shorts...")
        dalle_char_path = get_path("assets", "temp", f"{eid}_raw_ai.png")
        
        if os.path.exists(dalle_char_path):
            logger.info(f"   (CACHE HIT): Dùng lại ảnh có sẵn.")
        else:
            logger.warning(f"⚠️ Ảnh chưa có. Đang gọi DALL-E tạo backup cho Shorts: {name}...")
            if generate_character_image:
                try:
                    dalle_char_path = generate_character_image(name, dalle_char_path)
                except Exception:
                    dalle_char_path = None
            else:
                dalle_char_path = None
                
        base_bg_path = get_path('assets', 'images', 'default_background_shorts.png')

        # 4. RENDER SHORTS
        logger.info("PHASE 4/5: Đang Render Shorts (Nhân vật ở Giữa)...")
        shorts_path = create_shorts(
            tts, hook_title, eid, 
            name, 
            script_path, 
            custom_image_path=dalle_char_path,
            base_bg_path=base_bg_path
        )
        
        if not shorts_path:
             logger.error("❌ Lỗi Render Shorts.")
             return False

        # 5. UPLOAD
        logger.info("PHASE 5/5: Đang Upload Shorts...")
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
        logger.info(f"✅ SHORTS SUCCESS!")
        return True

    except Exception as e:
        logger.error(f"❌ ERROR SHORTS TỔNG: {e}", exc_info=True)
        return False


def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("Không có task pending.")
        return

    data = task["data"]
    task_meta = {"row_idx": task["row_idx"], "col_idx": task["col_idx"], "worksheet": task["worksheet"]}
    
    # Lấy text_hash để dọn dẹp
    text_hash = data.get("text_hash") 

    logger.info(f"▶️ ĐANG XỬ LÝ TASK ID={data.get('ID')} – {data.get('Name')}")
    
    long_ok = process_long_video(data, task_meta)
    sleep(10)
    short_ok = process_shorts(data, task_meta)

    # ⚠️ BƯỚC MỚI: DỌN DẸP
    if long_ok or short_ok: # Chỉ dọn dẹp nếu ít nhất 1 video được tạo thành công
        cleanup_temp_files(data.get('ID'), text_hash)
        
    if long_ok and short_ok: logger.info("🎉 FULL SUCCESS!")

if __name__ == "__main__":
    main()
