import os
import logging
from dotenv import load_dotenv
import json 

# --- IMPORT MODULES CẦN THIẾT ---
from read_sheet import get_episode_data # ĐÃ CẬP NHẬT IMPORT TỪ read_sheet
from generate_script import generate_script 
from generate_short_script import generate_short_script 
from create_tts import text_to_speech 
from finalize_audio import finalize_audio
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_youtube_video

# Thiết lập Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main_pipeline(episode_id: int):
    
    # --- BƯỚC 1: Tải data tập phim từ Google Sheet ---
    logging.info(f"Bắt đầu tải dữ liệu cho Episode ID {episode_id} từ Google Sheet...")
    # Gọi hàm từ module read_sheet
    episode_data = get_episode_data(episode_id)

    if not episode_data:
        logging.error("Pipeline bị hủy bỏ do không tải được dữ liệu tập phim.")
        return
    
    # --- BƯỚC 2: Tạo Kịch bản (dài) và Metadata ---
    logging.info("Bắt đầu tạo Kịch bản DÀI (Podcast) và Metadata YouTube...")
    long_script_data = generate_script(episode_data)
    if not long_script_data: return
    
    # --- 3. TẠO KỊCH BẢN NGẮN CHO SHORTS ---
    logging.info("Bắt đầu tạo Kịch bản NGẮN (Shorts)...")
    short_script_data = generate_short_script(episode_data)
    if not short_script_data: return

    # --- 4. Text-to-Speech (TTS) ---
    logging.info("Bắt đầu TTS cho Kịch bản DÀI...")
    long_raw_audio_path = text_to_speech(long_script_data['script_path'], episode_id, is_short=False)
    if not long_raw_audio_path: return
    
    logging.info("Bắt đầu TTS cho Kịch bản NGẮN (Shorts)...")
    short_raw_audio_path = text_to_speech(short_script_data['short_script_path'], episode_id, is_short=True)
    if not short_raw_audio_path: return
    
    # --- 5. Finalize Audio (Trộn nhạc nền) ---
    logging.info("Bắt đầu trộn nhạc nền cho Audio DÀI...")
    long_final_audio_path = finalize_audio(long_raw_audio_path, is_short=False)
    if not long_final_audio_path: return

    logging.info("Bắt đầu trộn nhạc nền cho Audio NGẮN (Shorts)...")
    short_final_audio_path = finalize_audio(short_raw_audio_path, is_short=True)
    if not short_final_audio_path: return

    # --- 6. Tạo Video ---
    logging.info("Bắt đầu tạo Video DÀI (16:9)...")
    long_video_path = create_video(long_final_audio_path, long_script_data['script_path'], episode_id)
    if not long_video_path: return
    
    logging.info("Bắt đầu tạo Video NGẮN (Shorts 9:16)...")
    short_video_path = create_shorts(short_final_audio_path, short_script_data['short_script_path'], episode_id)
    if not short_video_path: return

    # --- 7. Upload Video (Sử dụng metadata từ kịch bản dài) ---
    logging.info("Bắt đầu Upload Video DÀI...")
    upload_youtube_video(long_video_path, long_script_data)

    logging.info("Bắt đầu Upload Video NGẮN...")
    upload_youtube_video(short_video_path, long_script_data) 
    
    logging.info("Pipeline đã hoàn thành thành công cho cả Video DÀI và Video NGẮN!")

if __name__ == "__main__":
    load_dotenv()
    # Chạy pipeline cho Episode ID 1
    main_pipeline(episode_id=1)
