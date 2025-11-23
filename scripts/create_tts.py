import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
from utils import load_template_file

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_tts(script_path: str, episode_id: int):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return None

    script_content = load_template_file(script_path)
    if not script_content: return None

    TTS_MODEL = "tts-1"
    TTS_VOICE = "echo"  # Giọng nam trầm phù hợp (có thể thử 'onyx')

    try:
        client = OpenAI(api_key=api_key)
        logging.info(f"Bắt đầu tạo TTS với giọng: {TTS_VOICE}")

        response = client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=script_content,
            response_format="mp3"
        )

        output_dir = os.path.join('outputs', 'audio')
        audio_filename = f"{episode_id}_raw_audio.mp3"
        audio_path = os.path.join(output_dir, audio_filename)
        
        response.stream_to_file(audio_path)
        
        logging.info(f"Audio TTS đã tạo thành công và lưu tại: {audio_path}")
        return audio_path

    except Exception as e:
        logging.error(f"Lỗi khi gọi API OpenAI để tạo TTS: {e}")
        return None
