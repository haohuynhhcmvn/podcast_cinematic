#./scripts/create_tts.py
import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Đảm bảo tên hàm là text_to_speech
def text_to_speech(script_path: str, is_short: bool = False):
    """
    Tạo audio TTS từ file kịch bản bằng OpenAI API.
    
    Args:
        script_path (str): Đường dẫn đến file kịch bản (.txt).
        is_short (bool): True nếu là kịch bản cho Shorts, False nếu là Video Dài.
    
    Returns:
        str: Đường dẫn đến file audio thô đã tạo.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logging.error("OPENAI_API_KEY không được tìm thấy trong .env.")
        return None

    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
    except Exception as e:
        logging.error(f"Lỗi khi đọc file kịch bản {script_path}: {e}")
        return None
    
    # ... (phần còn lại của code)
    # Logic tạo file audio và gọi OpenAI API
    # ...
    
    # Lấy episode_id từ tên file (Ví dụ: '01_script_long.txt' -> '01')
    try:
        episode_id = os.path.basename(script_path).split('_')[0]
    except IndexError:
        logging.error(f"Không thể trích xuất episode_id từ tên file: {script_path}")
        return None

    # 2. LOGIC TÁCH FILE OUTPUT CHO SHORTS VÀ LONG VIDEO
    if is_short:
        output_filename = f"{episode_id}_raw_audio_short.mp3"
    else:
        output_filename = f"{episode_id}_raw_audio_long.mp3"
    
    output_dir = os.path.join('outputs', 'audio')
    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, output_filename)

    TTS_MODEL = "tts-1"
    TTS_VOICE = "echo"

    try:
        client = OpenAI(api_key=api_key)
        response = client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=script_content,
            response_format="mp3"
        )
        
        response.stream_to_file(audio_path)
        
        logging.info(f"Audio TTS đã tạo thành công và lưu tại: {audio_path}")
        return audio_path

    except Exception as e:
        logging.error(f"Lỗi khi gọi API OpenAI để tạo TTS: {e}")
        return None
