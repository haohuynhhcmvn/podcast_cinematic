# === scripts/glue_pipeline.py ===

import logging
import sys
import os
from time import sleep
from datetime import datetime, timedelta, timezone

# Đảm bảo các thư mục script nằm trong path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils import setup_environment, get_path, cleanup_temp_files 
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_5_short_scripts # Đã cập nhật hàm mới
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
#  HÀM XỬ LÝ CHU TRÌNH SHORTS BATCH (5 VIDEO)
# =========================================================
def process_shorts_batch(data, long_script_text, long_video_id, ws, row_idx, col_idx):
    """
    Tạo và upload 5 Shorts dựa trên kịch bản dài, có hẹn giờ.
    """
    episode_id = str(data.get('ID'))
    name = data.get('Name')
    
    # 1. Trích xuất 5 kịch bản Shorts từ kịch bản dài
    short_script_paths = generate_5_short_scripts(data, long_script_text)
    if not short_script_paths:
        logger.error("❌ Không thể trích xuất kịch bản Shorts.")
        return False

    # 2. Thiết lập thời gian hẹn giờ (Bắt đầu sau 2h, mỗi clip cách nhau 4h)
    start_time = datetime.now(timezone.utc) + timedelta(hours=2)

    for i, s_path in enumerate(short_script_paths, 1):
        try:
            logger.info(f"🎬 ĐANG XỬ LÝ SHORT {i}/5 CHO: {name}")
            
            # Đọc nội dung script short
            with open(s_path, "r", encoding="utf-8") as f:
                s_text = f.read()

            # Tạo Audio cho Short (mode="short", tích hợp short_index)
            s_audio = create_tts(s_text, episode_id, mode="short", short_index=i)
            
            # Tạo Video Short (Sửa create_shorts để không ghi đè file)
            # Lưu ý: Cần đảm bảo hàm create_shorts của bạn lưu theo index hoặc đổi tên sau khi tạo
            shorts_path = create_shorts(s_audio, name, episode_id, s_path)
            final_s_path = shorts_path.replace(".mp4", f"_{i}.mp4")
            if os.path.exists(shorts_path):
                os.rename(shorts_path, final_s_path)

            # Tính toán thời gian hẹn giờ ISO 8601
            publish_time = (start_time + timedelta(hours=(i-1)*4)).isoformat().replace('+00:00', 'Z')

            # Metadata cho Short (Có gắn link video dài)
            short_upload_data = {
                "Title": f"{name} Secrets | Part {i} #Shorts",
                "Description": f"Xem bản đầy đủ tại: https://youtu.be/{long_video_id}\n\n#history #legend",
                "Tags": ["shorts", "history", "legend"]
            }

            # Upload với tham số publish_at
            upload_video(final_s_path, short_upload_data, publish_at=publish_time)
            
            # DỌN DẸP NGAY để giải phóng RAM/Disk trên GitHub
            if os.path.exists(s_audio): os.remove(s_audio)
            if os.path.exists(final_s_path): os.remove(final_s_path)
            
        except Exception as e:
            logger.error(f"❌ Lỗi tại Short {i}: {e}")
            continue

    return True

# =========================================================
#  SAFE UPDATE STATUS
# =========================================================
def safe_update_status(ws, row_idx, col_idx, status):
    try:
        if not ws: return
        ws.update_cell(row_idx, col_idx, status)
    except Exception as e:
        logger.error(f"⚠️ Không thể cập nhật status: {e}")

# =========================================================
#  MAIN PIPELINE
# =========================================================
def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("ℹ️ Không có task pending.")
        return

    data = task["data"]
    row_idx = task["row_idx"]
    col_idx = task["col_idx"]
    ws = task["worksheet"]
    episode_id = str(data.get('ID'))
    text_hash = data.get("text_hash")

    logger.info(f"▶️ BẮT ĐẦU: {data.get('Name')} (ID: {episode_id})")

    try:
        # 1. TẠO KỊCH BẢN DÀI
        script_data = generate_long_script(data)
        if not script_data:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_SCRIPT')
            return

        long_script_path = script_data["script_path"]
        long_script_text = script_data["content"] # Lấy text để làm đầu vào cho Shorts
        yt_meta = script_data["metadata"]

        # 2. TẠO TTS VIDEO DÀI
        with open(long_script_path, "r", encoding="utf-8") as f:
            full_text = f.read()
        long_audio_path = create_tts(full_text, episode_id, mode="long")

        # 3. TẠO VIDEO DÀI
        # (Giả định bạn có hàm create_video xử lý tạo video dài từ script)
        long_video_path = create_video(long_audio_path, data.get('Name'), episode_id, long_script_path)

        # 4. UPLOAD VIDEO DÀI (Lấy ID để kéo view)
        upload_res = upload_video(long_video_path, yt_meta)
        long_video_id = upload_res.get('video_id')

        if not long_video_id:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_LONG_UPLOAD')
            return

        # 5. XỬ LÝ BATCH 5 SHORTS (Hẹn giờ rải rác)
        shorts_success = process_shorts_batch(data, long_script_text, long_video_id, ws, row_idx, col_idx)

        if shorts_success:
            safe_update_status(ws, row_idx, col_idx, 'SUCCESS_FULL_CYCLE')
            logger.info("✅ HOÀN THÀNH TOÀN BỘ CHU TRÌNH (1 LONG + 5 SHORTS)")
        else:
            safe_update_status(ws, row_idx, col_idx, 'PARTIAL_SUCCESS_LONG_ONLY')

    except Exception as e:
        logger.error(f"❌ THẤT BẠI TỔNG THỂ: {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'ERROR_PIPELINE')
    finally:
        # LUÔN DỌN DẸP SAU KHI KẾT THÚC
        cleanup_temp_files(episode_id, text_hash)

if __name__ == "__main__":
    main()
