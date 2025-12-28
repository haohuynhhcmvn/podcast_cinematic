# scripts/glue_pipeline.py
import logging
import os
from datetime import datetime, timedelta, timezone
from utils import setup_environment, get_path, cleanup_temp_files
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_5_short_scripts
from create_tts import create_tts
from create_shorts import create_shorts
from upload_youtube import upload_video

logger = logging.getLogger(__name__)

def process_shorts_batch(data, long_script_text, long_video_id, ws, row_idx, col_idx):
    episode_id = str(data['ID'])
    # Tạo 5 kịch bản short từ kịch bản dài
    short_script_paths = generate_5_short_scripts(data, long_script_text)
    
    # Thời điểm bắt đầu đăng short đầu tiên (cách hiện tại 2h để an toàn)
    start_time = datetime.now(timezone.utc) + timedelta(hours=2)

    for i, s_path in enumerate(short_script_paths, 1):
        try:
            logger.info(f"--- Xử lý Short {i}/5 ---")
            with open(s_path, "r", encoding="utf-8") as f:
                s_text = f.read()
            
            # 1. Tạo Audio cho từng short
            s_audio = create_tts(s_text, episode_id, mode="short", short_index=i)
            
            # 2. Tạo Video (Truyền ĐỦ 5 tham số)
            shorts_video_path = create_shorts(
                audio_path=s_audio,
                hook_title=data['Name'],
                episode_id=episode_id,
                script_path=s_path,      # Sửa lỗi missing argument
                short_index=i           # Để lưu file _1.mp4, _2.mp4...
            )

            if shorts_video_path and os.path.exists(shorts_video_path):
                # 3. Tính toán thời gian đăng (cách nhau 4h)
                scheduled_time = start_time + timedelta(hours=(i-1) * 4)
                publish_at = scheduled_time.isoformat().replace('+00:00', 'Z')

                # 4. Upload
                meta = {
                    "Title": f"{data['Name']} Mystery | Part {i} #Shorts",
                    "Description": f"Watch full story here: https://youtu.be/{long_video_id}",
                    "Tags": ["history", "shorts", data['Name']]
                }
                upload_video(shorts_video_path, meta, publish_at=publish_at)
                
                # Xóa file video sau khi upload thành công để nhẹ máy
                os.remove(shorts_video_path)
                if os.path.exists(s_audio): os.remove(s_audio)
                
        except Exception as e:
            logger.error(f"❌ Thất bại tại Short {i}: {e}")

def main():
    setup_environment()
    task = fetch_content()
    if not task: return

    data = task["data"]
    ws, row_idx, col_idx = task["worksheet"], task["row_idx"], task["col_idx"]
    episode_id = str(data['ID'])

    try:
        # Bước 1: Tạo kịch bản dài & Metadata
        script_data = generate_long_script(data)
        if not script_data: return

        long_text = script_data["content"]
        yt_meta = script_data["metadata"]

        # Bước 2: Xử lý Video dài (Giả sử bạn đã có hàm create_video)
        # long_video = create_video(...)
        # res = upload_video(long_video, yt_meta)
        # long_id = res.get('video_id', 'CHECK_CHANNEL')
        long_id = "VIDEO_DAI_ID" # Tạm thời

        # Bước 3: CHẠY BATCH 5 SHORTS
        process_shorts_batch(data, long_text, long_id, ws, row_idx, col_idx)
        
        ws.update_cell(row_idx, col_idx, 'SUCCESS_ALL')

    except Exception as e:
        logger.error(f"❌ Pipeline Error: {e}")
        ws.update_cell(row_idx, col_idx, 'ERROR')
    finally:
        cleanup_temp_files(episode_id, data.get('text_hash'))

if __name__ == "__main__":
    main()
