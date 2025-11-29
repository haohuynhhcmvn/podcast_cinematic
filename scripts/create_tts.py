from gtts import gTTS
from utils import get_path
import logging

logger = logging.getLogger(__name__)

def create_tts(script_path, episode_id, mode="long"):
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        filename = f"{episode_id}_tts_{mode}.mp3"
        out_path = get_path('assets', 'audio', filename)
        
        tts = gTTS(text=text, lang='vi')
        tts.save(out_path)
        logger.info(f"🗣️ TTS ({mode}) xong: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"❌ Lỗi TTS: {e}")
        return None
