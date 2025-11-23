import os
import logging
from dotenv import load_dotenv

# Import TẤT CẢ các hàm
from fetch_content import fetch_content
from generate_script import generate_script
from create_tts import create_tts
from auto_music_sfx import auto_music_sfx
from create_subtitle import create_subtitle
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_youtube
from utils import setup_environment

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main_pipeline():
    logging.info("--- BẮT ĐẦU QUY TRÌNH TẠO PODCAST TỰ ĐỘNG ---")

    load_dotenv()
    setup_environment() 

    try:
        episode_data = fetch_content()
        if not episode_data:
            logging.info("Không có tập mới nào trong Google Sheet để xử lý. Kết thúc.")
            return

        episode_id = episode_data['ID']
        logging.info(f"Đã lấy nội dung cho tập: {episode_id}")
        
        # 1. Tạo kịch bản
        script_path = generate_script(episode_data)
        if not script_path: return

        # 2. Tạo giọng đọc TTS
        raw_audio_path = create_tts(script_path, episode_id) 
        if not raw_audio_path: return

        # 3. Trộn nhạc nền & SFX
        final_audio_path = auto_music_sfx(raw_audio_path, episode_id)
        if not final_audio_path: return

        # 4. Tạo phụ đề SRT
        subtitle_path = create_subtitle(final_audio_path, script_path, episode_id)
        if not subtitle_path: return

        # 5. Tạo video 16:9
        video_169_path = create_video(final_audio_path, subtitle_path, episode_id)
        if not video_169_path: return

        # 6. Tạo video Shorts 9:16
        video_916_path = create_shorts(final_audio_path, subtitle_path, episode_id)
        if not video_916_path: return

        # 7. Upload lên YouTube
        upload_status = upload_youtube(video_169_path, episode_data)
        logging.info(f"Trạng thái Upload lên YouTube: {upload_status}")
        
        # Kế tiếp: Cần thêm bước cập nhật trạng thái 'COMPLETED' trở lại Google Sheet
        # (Sử dụng 'Status_Row' lấy từ fetch_content.py)

    except Exception as e:
        logging.error(f"QUY TRÌNH GẶP LỖI: {e}", exc_info=True)
    finally:
        logging.info("--- KẾT THÚC QUY TRÌNH TẠO PODCAST TỰ ĐỘNG ---")


if __name__ == '__main__':
    main_pipeline()
