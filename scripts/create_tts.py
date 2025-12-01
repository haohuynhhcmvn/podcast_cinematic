# ./scripts/create_tts.py
import os
import logging
from openai import OpenAI
from utils import get_path 

logger = logging.getLogger(__name__)

OPENAI_TTS_MODEL = "tts-1"
OPENAI_TTS_VOICE = "alloy"

# ⭐ Giảm speed từ 1.25 → 1.10 (fix ngắn TTS)
TTS_SPEED = 1.10   

def create_tts(script_path: str, episode_id, mode="long"):
    if not os.path.exists(script_path):
        logger.error(f"❌ Không tìm thấy script: {script_path}")
        return None
        
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Thiếu OPENAI_API_KEY.")
            return None
            
        client = OpenAI(api_key=api_key)
        
        with open(script_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
            
        if not text:
            logger.error("❌ Script rỗng.")
            return None
            
        filename = f"{episode_id}_tts_{mode}.mp3"
        out_path = get_path('assets', 'audio', filename)

        logger.info(f"📢 TTS speed={TTS_SPEED}, voice={OPENAI_TTS_VOICE}")

        response = client.audio.speech.create(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            input=text,
            response_format="mp3",
            speed=TTS_SPEED  
        )

        response.stream_to_file(out_path)
        return out_path
        
    except Exception as e:
        logger.error(f"❌ TTS lỗi: {e}")
        return None
