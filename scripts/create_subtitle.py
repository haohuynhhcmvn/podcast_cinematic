import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_subtitle(audio_path: str, script_path: str, episode_id: int):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return None

    try:
        client = OpenAI(api_key=api_key)
        logging.info("Bắt đầu phiên âm audio và tạo phụ đề bằng Whisper...")

        with open(audio_path, "rb") as audio_file:
            # Gọi API phiên âm với response format là SRT để có timestamp
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file, 
                response_format="srt"
            )
        
        output_dir = os.path.join('outputs', 'subtitle')
        subtitle_filename = f"{episode_id}_subtitle.srt"
        subtitle_path = os.path.join(output_dir, subtitle_filename)
        
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        logging.info(f"Phụ đề SRT đã tạo thành công và lưu tại: {subtitle_path}")
        return subtitle_path

    except Exception as e:
        logging.error(f"Lỗi khi gọi API Whisper để tạo phụ đề: {e}")
        return None
