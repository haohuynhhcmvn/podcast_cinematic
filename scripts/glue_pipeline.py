import os
import logging
from dotenv import load_dotenv
import json # Cần thiết cho việc đọc data

# Import các hàm từ các module khác
from .generate_script import generate_script 
from .generate_short_script import generate_short_script # BƯỚC MỚI
from .text_to_speech import text_to_speech
from .finalize_audio import finalize_audio
from .create_video import create_video
from .create_shorts import create_shorts
from .youtube_uploader import upload_youtube_video

# Thiết lập Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main_pipeline(episode_id: int):
    # Tải data tập phim
    data_path = os.path.join('data', 'episodes', f'{episode_id}_data.json')
    if not os.path.exists(data_path):
        logging.error(f"Không tìm thấy file data cho Episode ID {episode_id}")
        return

    with open(data_path, 'r', encoding='utf-8') as f:
        episode_data = json.load(f)

    # --- 1. Tạo Kịch bản (dài) và Metadata ---
    logging.info("Bắt đầu tạo Kịch bản DÀI (Podcast) và Metadata YouTube...")
    long_script_data = generate_script(episode_data)
    if not long_script_data: return
    
    # --- 2. TẠO KỊCH BẢN NGẮN CHO SHORTS (BƯỚC MỚI) ---
    logging.info("Bắt đầu tạo Kịch bản NGẮN (Shorts)...")
    short_script_data = generate_short_script(episode_data)
    if not short_script_data: return

    # --- 3. Text-to-Speech (TTS) ---
    # 3a. TTS cho Kịch bản DÀI
    logging.info("Bắt đầu TTS cho Kịch bản DÀI...")
    long_raw_audio_path = text_to_speech(long_script_data['script_path'], is_short=False)
    if not long_raw_audio_path: return
    
    # 3b. TTS cho Kịch bản NGẮN
    logging.info("Bắt đầu TTS cho Kịch bản NGẮN (Shorts)...")
    short_raw_audio_path = text_to_speech(short_script_data['short_script_path'], is_short=True)
    if not short_raw_audio_path: return
    
    # --- 4. Finalize Audio (Trộn nhạc nền) ---
    # 4a. Finalize Audio DÀI
    logging.info("Bắt đầu trộn nhạc nền cho Audio DÀI...")
    long_final_audio_path = finalize_audio(long_raw_audio_path, is_short=False)
    if not long_final_audio_path: return

    # 4b. Finalize Audio NGẮN
    logging.info("Bắt đầu trộn nhạc nền cho Audio NGẮN (Shorts)...")
    short_final_audio_path = finalize_audio(short_raw_audio_path, is_short=True)
    if not short_final_audio_path: return

    # --- 5. Tạo Video ---
    # 5a. Tạo Video DÀI (sử dụng audio dài)
    logging.info("Bắt đầu tạo Video DÀI (16:9)...")
    long_video_path = create_video(long_final_audio_path, long_script_data['script_path'], episode_id)
    if not long_video_path: return
    
    # 5b. Tạo Video NGẮN (sử dụng audio ngắn)
    logging.info("Bắt đầu tạo Video NGẮN (Shorts 9:16)...")
    short_video_path = create_shorts(short_final_audio_path, long_script_data['script_path'], episode_id)
    if not short_video_path: return

    # --- 6. Upload Video (Sử dụng metadata từ kịch bản dài) ---
    logging.info("Bắt đầu Upload Video DÀI...")
    upload_youtube_video(long_video_path, long_script_data)

    logging.info("Bắt đầu Upload Video NGẮN...")
    # Thường nên tạo metadata riêng cho shorts, nhưng tạm dùng metadata dài để hoàn thành flow
    upload_youtube_video(short_video_path, long_script_data) 
    
    logging.info("Pipeline đã hoàn thành thành công cho cả Video DÀI và Video NGẮN!")

if __name__ == "__main__":
    load_dotenv()
    # Ví dụ chạy với Episode ID 1 (Sửa lại ID nếu cần)
    main_pipeline(episode_id=1)
