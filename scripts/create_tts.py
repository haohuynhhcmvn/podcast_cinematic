# ./scripts/create_tts.py
import os
import logging
from openai import OpenAI
from utils import get_path 

logger = logging.getLogger(__name__)

# Cấu hình OpenAI TTS
OPENAI_TTS_MODEL = "tts-1"
OPENAI_TTS_VOICE = "alloy"     # Giọng nam kể chuyện
TTS_SPEED = 1.25               # ⚡ TỐC ĐỘ ĐỌC 1.25X


def create_tts(script_path: str, episode_id, mode="long"):
    """
    Tạo giọng đọc (TTS) bằng API OpenAI với tốc độ 1.25x.
    """
    if not os.path.exists(script_path):
        logger.error(f"❌ Lỗi TTS: Không tìm thấy file kịch bản tại {script_path}")
        return None
        
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Thiếu OPENAI_API_KEY. Không thể gọi OpenAI TTS.")
            return None
            
        client = OpenAI(api_key=api_key)
        
        with open(script_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
            
        if not text:
            logger.error("❌ Lỗi TTS: Nội dung kịch bản RỖNG.")
            return None
            
        filename = f"{episode_id}_tts_{mode}.mp3"
        out_path = get_path('assets', 'audio', filename)

        logger.info(f"📞 Đang gọi OpenAI TTS (Voice: {OPENAI_TTS_VOICE}, mode={mode}, speed={TTS_SPEED})...")

        # ✨ Thêm speed = 1.25
        response = client.audio.speech.create(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            input=text,
            response_format="mp3",
            speed=TTS_SPEED  
        )

        response.stream_to_file(out_path)
        
        logger.info(f"🗣️ TTS OpenAI xong (speed={TTS_SPEED}): {out_path}")
        return out_path
        
    except Exception as e:
        logger.error(f"❌ Lỗi TTS OpenAI: {e}")
        return None
