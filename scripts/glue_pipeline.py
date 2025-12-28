# === scripts/glue_pipeline.py ===

import logging
import sys
import os
from time import sleep
from datetime import datetime, timedelta, timezone

# ensure project scripts folder is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils import setup_environment, get_path, cleanup_temp_files 
from fetch_content import fetch_content
# ĐỔI generate_short_script THÀNH generate_5_short_scripts (Cần cập nhật file generate_script.py tương ứng)
from generate_script import generate_long_script, generate_5_short_scripts 
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

# ... (Giữ nguyên các hàm safe_update_status và try_update_youtube_id) ...

# =========================================================
#  SHORTS BATCH (TÁCH THÀNH 5 PHẦN)
# =========================================================
def process_shorts_batch(data, task_meta, long_script_text, long_video_id):
    """
    Xử lý tạo 5 Shorts từ kịch bản dài và đặt lịch đăng cách nhau 4 giờ.
    """
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')
    eid = str(data.get('ID'))
    name = data.get('Name')

    logger.info(f"---------------------------------------------------------")
    logger.info(f"🎬 BẮT ĐẦU [SHORTS BATCH]: Tách 5 phần cho ID={eid}")
    logger.info(f"---------------------------------------------------------")

    try:
        # 1. SCRIPT - Trích xuất 5 kịch bản
        # Cần truyền long_script_text để AI cắt nhỏ chính xác
        short_paths = generate_5_short_scripts(data, long_script_text)
        if not short_paths or len(short_paths) == 0:
            logger.error("❌ Lỗi tạo danh sách Shorts Script.")
            return False

        # Đặt lịch bắt đầu sau 2h, mỗi clip cách nhau 4h
        start_publish_time = datetime.now(timezone.utc) + timedelta(hours=2)
        success_count = 0

        for i, s_path in enumerate(short_paths, 1):
            logger.info(f"🚀 Đang xử lý Short {i}/5...")
            
            # 2. TTS cho từng phần (Thêm tham số short_index=i để tránh ghi đè file audio)
            # create_tts cần được cập nhật để nhận tham số này
            with open(s_path, "r", encoding="utf-8") as f:
                current_script_text = f.read()

            tts = create_tts(s_path, eid, "short", short_index=i) 
            if not tts: continue

            # 3. ẢNH AI (Dùng chung Cache từ video Long)
            dalle_char_path = get_path("assets", "temp", f"{eid}_raw_ai.png")
            base_bg_path = get_path('assets', 'images', 'default_background_shorts.png')

            # 4. RENDER SHORTS
            # Truyền thêm index i để tạo file ID_short_1.mp4, ID_short_2.mp4...
            shorts_video_path = create_shorts(
                tts, name, eid, 
                name, 
                s_path, 
                custom_image_path=dalle_char_path,
                base_bg_path=base_bg_path,
                short_index=i 
            )

            if not shorts_video_path: continue

            # 5. UPLOAD & SCHEDULE
            # Tính toán giờ đăng ISO chuẩn YouTube
            publish_at = (start_publish_time + timedelta(hours=(i-1)*4)).isoformat().replace('+00:00', 'Z')
            
            upload_data = {
                "Title": f"{name} Secrets | Part {i} #Shorts",
                "Summary": f"Watch full story: https://youtu.be/{long_video_id}",
                "Tags": ["shorts", "history", "mystery"]
            }
            
            # upload_video cần được cập nhật để nhận tham số publish_at
            res = upload_video(shorts_video_path, upload_data, publish_at=publish_at)
            
            if res and res != 'FAILED':
                success_count += 1
                # Dọn dẹp ngay file video/audio ngắn để tránh đầy ổ cứng
                if os.path.exists(shorts_video_path): os.remove(shorts_video_path)
                if os.path.exists(tts): os.remove(tts)

        if success_count > 0:
            safe_update_status(ws, row_idx, col_idx, f'UPLOADED_{success_count}_SHORTS')
            return True
        return False

    except Exception as e:
        logger.error(f"❌ ERROR SHORTS BATCH: {e}", exc_info=True)
        return False

# =========================================================
#  MAIN PIPELINE (ĐÃ CẬP NHẬT LUỒNG CHẠY)
# =========================================================
def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("Không có task pending.")
        return

    data = task["data"]
    task_meta = {"row_idx": task["row_idx"], "col_idx": task["col_idx"], "worksheet": task["worksheet"]}
    episode_id = str(data.get('ID')) 
    text_hash = data.get("text_hash") 

    logger.info(f"▶️ ĐANG XỬ LÝ TASK ID={episode_id} – {data.get('Name')}")
    
    # 1. Chạy Video Long như bình thường (Giữ nguyên)
    # Lấy thêm long_res để có text kịch bản dài
    long_res = generate_long_script(data) 
    if long_res:
        long_ok = process_long_video(data, task_meta) # Hàm này bạn đã có sẵn
        
        # 2. Sau khi Long Video xong, lấy ID và Script để làm 5 Shorts
        # Giả định upload_video trả về video_id trong dict
        long_video_id = "CHECK_CHANNEL" # Default
        
        # Tách 5 Shorts
        long_script_text = ""
        with open(long_res["script_path"], "r", encoding="utf-8") as f:
            long_script_text = f.read()

        # Chạy batch shorts thay vì 1 short đơn lẻ
        short_ok = process_shorts_batch(data, task_meta, long_script_text, long_video_id)

        # 3. Dọn dẹp
        if long_ok or short_ok: 
            cleanup_temp_files(episode_id, text_hash)
            
        if long_ok and short_ok: logger.info("🎉 FULL SUCCESS (1 LONG + 5 SHORTS)!")
    else:
        logger.error("❌ Không tạo được kịch bản gốc.")

if __name__ == "__main__":
    main()
