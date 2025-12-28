# scripts/glue_pipeline.py

import logging
import sys
import os
from time import sleep

# Đảm bảo python tìm thấy các module trong thư mục scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import các module vệ tinh
from utils import setup_environment, get_path, cleanup_temp_files
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_short_script
from auto_music_sfx import auto_music_sfx
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video

# Import module hình ảnh (xử lý trường hợp thiếu thư viện)
try:
    from generate_image import generate_character_image
    from create_thumbnail import add_text_to_thumbnail
except ImportError:
    logging.warning("⚠️ Module tạo ảnh/thumbnail chưa có hoặc lỗi.")
    generate_character_image = None
    add_text_to_thumbnail = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =========================================================
#  HÀM HỖ TRỢ UPDATE TRẠNG THÁI GOOGLE SHEET
# =========================================================
def safe_update_status(ws, row_idx, col_idx, status):
    try:
        if not ws: return
        if col_idx and isinstance(col_idx, int):
            ws.update_cell(row_idx, col_idx, status)
    except Exception as e:
        logger.error(f"⚠️ Không update được status '{status}': {e}")

# =========================================================
#  MAIN PIPELINE
# =========================================================
def main():
    setup_environment()
    
    # 1. Lấy dữ liệu từ Sheet
    task = fetch_content()
    if not task:
        logger.info("💤 Không có task 'pending'. Hệ thống nghỉ.")
        return

    data = task["data"]
    task_meta = {"row_idx": task["row_idx"], "col_idx": task["col_idx"], "worksheet": task["worksheet"]}
    ws = task_meta["worksheet"]
    row_idx = task_meta["row_idx"]
    col_idx = task_meta["col_idx"]
    
    # Chuẩn hóa ID
    episode_id = str(data.get('ID'))
    text_hash = data.get("text_hash")

    logger.info(f"▶️ BẮT ĐẦU XỬ LÝ: {episode_id} – {data.get('Name')}")
    
    try:
        # -------------------------------------------------------------------
        # BƯỚC 1: TẠO KỊCH BẢN (SCRIPT) & HÌNH ẢNH
        # -------------------------------------------------------------------
        # 1.1 Long Script
        if not generate_long_script(data):
            safe_update_status(ws, row_idx, col_idx, 'FAILED_SCRIPT')
            return

        # 1.2 Short Script
        generate_short_script(data) # Không return False nếu lỗi, chỉ log

        # 1.3 Tạo ảnh nhân vật (DALL-E 3)
        image_path = get_path("assets", "images", f"{episode_id}.png")
        if generate_character_image:
            if not os.path.exists(image_path):
                img_res = generate_character_image(data.get('Name'), image_path)
                if not img_res:
                    # Fallback: Nếu không tạo được ảnh, dùng ảnh mặc định hoặc báo lỗi
                    logger.warning("⚠️ Không tạo được ảnh AI. Sẽ dùng ảnh cũ nếu có.")
            else:
                logger.info("✅ Ảnh nhân vật đã có sẵn.")
        
        # -------------------------------------------------------------------
        # BƯỚC 2: TẠO GIỌNG ĐỌC (TTS) & ÂM THANH (SFX)
        # -------------------------------------------------------------------
        # 2.1 TTS Long
        tts_long_path = create_tts(episode_id, data.get('Name'), mode="long")
        if not tts_long_path:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_TTS')
            return
            
        # 2.2 Mix nhạc nền (Auto Ducking + Intro/Outro)
        audio_mixed_path = auto_music_sfx(episode_id, tts_long_path)
        if not audio_mixed_path:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_AUDIO_MIX')
            return

        # -------------------------------------------------------------------
        # BƯỚC 3: TẠO THUMBNAIL
        # -------------------------------------------------------------------
        thumb_path = get_path("outputs", "thumbnails", f"{episode_id}_thumb.jpg")
        if add_text_to_thumbnail and os.path.exists(image_path):
            # Tạo text cho thumbnail (Lấy 4-5 từ đầu của tên hoặc Title ngắn gọn)
            thumb_text = data.get('Name', 'New Episode')
            add_text_to_thumbnail(image_path, thumb_text, thumb_path)
        
        # -------------------------------------------------------------------
        # BƯỚC 4: DỰNG VIDEO (LONG FORM)
        # -------------------------------------------------------------------
        # [CẬP NHẬT] Lấy đường dẫn file script để tạo phụ đề
        long_script_path = get_path("data", "episodes", f"{episode_id}_long_en.txt")
        
        video_path = create_video(
            episode_id, 
            audio_mixed_path, 
            image_path, 
            data.get('Name'),
            script_path=long_script_path # <--- ĐÃ TRUYỀN SCRIPT VÀO ĐÂY
        )
        
        if not video_path:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_VIDEO_RENDER')
            return

        # -------------------------------------------------------------------
        # BƯỚC 5: UPLOAD YOUTUBE (LONG)
        # -------------------------------------------------------------------
        upload_data = {
            "Title": f"{data.get('Name')} - Full Biography | Documentary",
            "Summary": f"Amazing life story of {data.get('Name')}. Watch now! #history #{data.get('Name')}",
            "Tags": ["history", "biography", "documentary", data.get('Name')]
        }
        
        # Upload kèm Thumbnail
        res = upload_video(video_path, upload_data, thumbnail_path=thumb_path)
        
        if not res or res == 'FAILED':
            safe_update_status(ws, row_idx, col_idx, 'FAILED_UPLOAD')
            # Lưu ý: Vẫn tiếp tục chạy Shorts dù Long lỗi upload (tuỳ chọn)
        else:
            safe_update_status(ws, row_idx, col_idx, 'UPLOADED_LONG')

        # -------------------------------------------------------------------
        # BƯỚC 6: XỬ LÝ SHORTS (TÙY CHỌN)
        # -------------------------------------------------------------------
        # Kiểm tra xem có script shorts không
        short_script_path = get_path("data", "episodes", f"{episode_id}_short_en.txt")
        if os.path.exists(short_script_path):
            logger.info("📱 Đang xử lý Shorts...")
            
            # 6.1 TTS Shorts
            tts_short_path = create_tts(episode_id, data.get('Name'), mode="short")
            
            if tts_short_path:
                # 6.2 Dựng Shorts (Kèm Subtitles Hormozi & Hook Title)
                # Lấy Title ngắn cho Shorts (nếu có file riêng)
                short_title_file = get_path("data", "episodes", f"{episode_id}_short_title.txt")
                hook_title = data.get('Name')
                if os.path.exists(short_title_file):
                    with open(short_title_file, 'r', encoding='utf-8') as f:
                        hook_title = f.read().strip()

                shorts_path = create_shorts(
                    episode_id, 
                    tts_short_path, 
                    script_path=short_script_path, 
                    image_path=image_path,
                    hook_title=hook_title
                )
                
                # 6.3 Upload Shorts
                if shorts_path:
                    shorts_meta = {
                        "Title": f"{hook_title} #Shorts",
                        "Summary": f"Shorts about {data.get('Name')}",
                        "Tags": ["shorts", "history", data.get('Name')]
                    }
                    upload_video(shorts_path, shorts_meta) # Không cần thumbnail cho shorts
                    logger.info("✅ Shorts đã hoàn thành!")

        # -------------------------------------------------------------------
        # BƯỚC 7: DỌN DẸP
        # -------------------------------------------------------------------
        logger.info("🧹 Dọn dẹp file tạm...")
        cleanup_temp_files(episode_id, text_hash)
        
        logger.info(f"🎉 HOÀN TẤT TOÀN BỘ QUY TRÌNH CHO: {data.get('Name')}")

    except Exception as e:
        logger.error(f"❌ LỖI KHÔNG XÁC ĐỊNH (CRITICAL): {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'CRASHED')

if __name__ == "__main__":
    main()
