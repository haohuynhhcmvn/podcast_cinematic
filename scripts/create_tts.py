#./scripts/create_tts.py
import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def text_to_speech(script_path: str, episode_id: int, is_short: bool = False):
    """
    Chuyển văn bản từ file kịch bản thành file audio MP3 bằng OpenAI TTS API.
    
    Args:
        script_path (str): Đường dẫn đến file kịch bản (.txt).
        episode_id (int): ID của tập phim để đặt tên file đầu ra.
        is_short (bool): True nếu là kịch bản Shorts (dài), False nếu là kịch bản dài.
        
    Returns:
        str | None: Đường dẫn đến file audio MP3 đã tạo, hoặc None nếu thất bại.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("Thiếu OPENAI_API_KEY. Vui lòng kiểm tra file .env")
        return None

    if not os.path.exists(script_path):
        logging.error(f"Không tìm thấy file kịch bản tại: {script_path}")
        return None

    # Đọc nội dung kịch bản
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_text = f.read()
    except Exception as e:
        logging.error(f"Lỗi khi đọc file kịch bản: {e}")
        return None

    # Thiết lập mô hình và giọng nói
    TTS_MODEL = "tts-1"
    # Giọng nam Tiếng Anh, trầm, rõ ràng, phù hợp cho podcast cinematic
    # Tùy chọn khác: 'alloy' (ấm áp), 'nova' (nữ)
    TTS_VOICE = "echo" 

    try:
        client = OpenAI(api_key=api_key)
        
        # Định nghĩa đường dẫn file audio đầu ra
        file_prefix = "short" if is_short else "long"
        output_dir = os.path.join('outputs', 'audio')
        os.makedirs(output_dir, exist_ok=True)
        audio_filename = f"{episode_id}_tts_{file_prefix}.mp3"
        audio_path = os.path.join(output_dir, audio_filename)
        
        logging.info(f"Bắt đầu chuyển văn bản thành giọng nói (TTS) cho script {file_prefix} bằng giọng '{TTS_VOICE}'...")

        # Gọi API OpenAI
        response = client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=script_text
        )

        # Lưu file audio
        # Ghi nội dung response dưới dạng stream vào file
        response.stream_to_file(audio_path)
        
        logging.info(f"Đã tạo file TTS thành công. File lưu tại: {audio_path}")
        return audio_path

    except Exception as e:
        logging.error(f"Lỗi khi gọi OpenAI TTS API: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # Ví dụ về cách sử dụng cục bộ (cần tạo file kịch bản giả trong thư mục data/episodes)
    logging.info("Module text_to_speech đã được định nghĩa.")
