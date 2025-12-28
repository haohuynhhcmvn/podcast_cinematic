# === scripts/glue_pipeline.py ===
import logging
import sys
import os
from datetime import datetime, timedelta, timezone

from utils import setup_environment, get_path, cleanup_temp_files 
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_5_short_scripts
from create_tts import create_tts
from create_shorts import create_shorts
from upload_youtube import upload_video

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_shorts_batch(data, long_script_text, long_video_id):
    episode_id = str(data['ID'])
    short_paths = generate_5_short_scripts(data, long_script_text)
    start_time = datetime.now(timezone.utc) + timedelta(hours=2)

    for i, s_path in enumerate(short_paths, 1):
        try:
            with open(s_path, "r", encoding="utf-8") as f:
                s_text = f.read()
            
            s_audio = create_tts(s_text, episode_id, mode="short", short_index=i)
            # Giả định create_shorts tạo video ID_shorts.mp4, ta cần đổi tên để tránh ghi đè
            temp_video = create_shorts(s_audio, data['Name'], episode_id, s_path)
            final_video = temp_video.replace(".mp4", f"_{i}.mp4")
            if os.path.exists(temp_video): os.rename(temp_video, final_video)

            publish_time = (start_time + timedelta(hours=(i-1)*4)).isoformat().replace('+00:00', 'Z')
            
            meta = {
                "Title": f"Secret of {data['Name']} | Part {i} #Shorts",
                "Description": f"Full story: https://youtu.be/{long_video_id}",
                "Tags": ["history", "shorts"]
            }
            upload_video(final_video, meta, publish_at=publish_time)
            
            # Giải phóng RAM/Disk trên GitHub ngay lập tức
            if os.path.exists(s_audio): os.remove(s_audio)
            if os.path.exists(final_video): os.remove(final_video)
        except Exception as e:
            logger.error(f"❌ Error Short {i}: {e}")

def main():
    setup_environment()
    task = fetch_content()
    if not task: return

    data = task["data"]
    ws = task["worksheet"]
    row_idx, col_idx = task["row_idx"], task["col_idx"]
    episode_id = str(data['ID'])

    try:
        # FIX LỖI KEYERROR TẠI ĐÂY
        script_data = generate_long_script(data)
        if not script_data:
            ws.update_cell(row_idx, col_idx, 'FAILED_SCRIPT')
            return

        yt_meta = script_data["metadata"]      # ✅ Bây giờ đã có key này
        long_text = script_data["content"]     # ✅ Lấy nội dung để làm Shorts
        long_path = script_data["script_path"]

        # Các bước tạo video dài (giả định hàm create_video đã tồn tại)
        long_audio = create_tts(long_text, episode_id, mode="long")
        # long_video = create_video(...) 
        
        # Upload video dài
        # upload_res = upload_video(long_video, yt_meta)
        # long_id = upload_res.get('video_id')
        long_id = "temp_id_for_demo" # Thay bằng ID thật từ upload_video

        if long_id:
            process_shorts_batch(data, long_text, long_id)
            ws.update_cell(row_idx, col_idx, 'SUCCESS_ALL')

    except Exception as e:
        logger.error(f"❌ Pipeline Error: {e}")
        ws.update_cell(row_idx, col_idx, 'ERROR')
    finally:
        cleanup_temp_files(episode_id, data['text_hash'])

if __name__ == "__main__":
    main()
