# === scripts/glue_pipeline.py ===
import logging
import sys
import os
from time import sleep
from datetime import datetime, timedelta, timezone

# Đảm bảo project root nằm trong path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils import setup_environment, get_path, cleanup_temp_files 
from fetch_content import fetch_content
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

# =========================================================
#  HÀM XỬ LÝ VIDEO DÀI (LONG VIDEO)
# =========================================================
def process_long_video(data, task_meta):
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')
    eid = str(data.get('ID'))
    name = data.get('Name')

    try:
        logger.info(f"🎬 BẮT ĐẦU XỬ LÝ VIDEO DÀI: {name}")
        
        # 1. Tạo Script & Meta
        script_res = generate_long_script(data)
        if not script_res: return None, None

        script_path = script_res["script_path"]
        long_text = script_res["content"]
        meta = script_res["metadata"]

        # 2. Ảnh AI & Thumbnail
        raw_img = get_path("assets", "temp", f"{eid}_raw_ai.png")
        if generate_character_image and not os.path.exists(raw_img):
            generate_character_image(name, raw_img)
        
        thumb_path = None
        if add_text_to_thumbnail and os.path.exists(raw_img):
            thumb_out = get_path("outputs", "thumbnails", f"{eid}_thumb.jpg")
            thumb_path = add_text_to_thumbnail(raw_img, meta.get("Title", name), thumb_out)

        # 3. TTS & Render
        tts_path = create_tts(long_text, eid, mode="long")
        # Giả định create_video sử dụng ảnh AI làm nền
        video_path = create_video(tts_path, name, eid, script_path, custom_image_path=raw_img)

        # 4. Upload
        upload_res = upload_video(video_path, meta, thumbnail_path=thumb_path)
        long_id = upload_res.get('video_id') if isinstance(upload_res, dict) else None
        
        return long_id, long_text

    except Exception as e:
        logger.error(f"❌ Lỗi process_long_video: {e}")
        return None, None

# =========================================================
#  HÀM XỬ LÝ 5 SHORTS (BATCH)
# =========================================================
def process_shorts_batch(data, long_script_text, long_video_id):
    eid = str(data.get('ID'))
    name = data.get('Name')
    
    # 1. Tách 5 kịch bản
    short_paths = generate_5_short_scripts(data, long_script_text)
    if not short_paths: return False

    # Hẹn giờ: bắt đầu sau 2h, mỗi clip cách nhau 4h
    start_time = datetime.now(timezone.utc) + timedelta(hours=2)

    for i, s_path in enumerate(short_paths, 1):
        try:
            logger.info(f"🎬 Xử lý Short {i}/5...")
            with open(s_path, "r", encoding="utf-8") as f:
                s_text = f.read()

            s_audio = create_tts(s_text, eid, mode="short", short_index=i)
            s_video = create_shorts(s_audio, name, eid, s_path, short_index=i)

            publish_at = (start_time + timedelta(hours=(i-1)*4)).isoformat().replace('+00:00', 'Z')
            
            meta = {
                "Title": f"{name} Secrets | Part {i} #Shorts",
                "Description": f"Xem bản đầy đủ tại: https://youtu.be/{long_video_id}",
                "Tags": ["history", "shorts"]
            }
            upload_video(s_video, meta, publish_at=publish_at)
            
            # Cleanup từng phần để tiết kiệm RAM/Disk
            if os.path.exists(s_audio): os.remove(s_audio)
            if os.path.exists(s_video): os.remove(s_video)
        except Exception as e:
            logger.error(f"❌ Lỗi tại Short {i}: {e}")
    return True

# =========================================================
#  MAIN EXECUTION
# =========================================================
def main():
    setup_environment()
    task = fetch_content()
    if not task: return

    data = task["data"]
    task_meta = {"row_idx": task["row_idx"], "col_idx": task["col_idx"], "worksheet": task["worksheet"]}
    episode_id = str(data.get('ID'))
    text_hash = data.get("text_hash")

    logger.info(f"▶️ ĐANG XỬ LÝ TASK ID={episode_id} – {data.get('Name')}")

    # 1. Xử lý Video Dài
    long_video_id, long_text = process_long_video(data, task_meta)

    # 2. Xử lý Shorts (Chỉ chạy nếu Video dài upload thành công)
    if long_video_id and long_text:
        process_shorts_batch(data, long_text, long_video_id)
        # Cập nhật trạng thái thành công cuối cùng
        if task_meta['worksheet']:
            task_meta['worksheet'].update_cell(task_meta['row_idx'], task_meta['col_idx'], 'SUCCESS_ALL')
    else:
        if task_meta['worksheet']:
            task_meta['worksheet'].update_cell(task_meta['row_idx'], task_meta['col_idx'], 'FAILED')

    # 3. Dọn dẹp
    cleanup_temp_files(episode_id, text_hash)

if __name__ == "__main__":
    main()
