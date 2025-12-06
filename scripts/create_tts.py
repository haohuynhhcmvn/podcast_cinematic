# scripts/create_tts.py
import logging
import os
import textwrap
from openai import OpenAI
from pydub import AudioSegment
from utils import get_path

logger = logging.getLogger(__name__)

TTS_MODEL = "tts-1"
VOICE = "onyx"
SPEED_MULTIPLIER = 1.15 

# --- HÀM LỌC RÁC MỚI ---
def clean_and_validate_script(text):
    if not text: return ""
    lines = text.split('\n')
    cleaned_lines = []
    
    garbage_keywords = [
        "script", "biography", "title:", "host:", "narrator:", 
        "intro:", "outro:", "music:", "visual:", "scene:"
    ]
    
    for i, line in enumerate(lines):
        clean_line = line.strip()
        if not clean_line: continue
            
        # Kiểm tra 5 dòng đầu
        if i < 5:
            lower = clean_line.lower()
            # Xóa nếu chứa từ khóa rác hoặc quá ngắn (tiêu đề)
            if any(kw in lower for kw in garbage_keywords):
                continue
            if len(clean_line.split()) < 6 and not clean_line.endswith(('.', '!', '?')):
                 continue
                 
        cleaned_lines.append(clean_line)
    return "\n".join(cleaned_lines)

def create_tts(script_path, episode_id, mode="long"):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: return None
        client = OpenAI(api_key=api_key)

        if not os.path.exists(script_path): return None
        with open(script_path, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()

        # [FIX] Lọc sạn trước khi đọc
        full_text = clean_and_validate_script(raw_text)
        if not full_text: return None

        # Chunking
        chunk_size = 3000
        chunks = textwrap.wrap(full_text, width=chunk_size, break_long_words=False)

        combined_audio = AudioSegment.empty()
        
        logger.info(f"🎙️ Tạo TTS ({len(chunks)} phần) - {mode}...")
        
        for i, chunk in enumerate(chunks):
            try:
                response = client.audio.speech.create(model=TTS_MODEL, voice=VOICE, input=chunk)
                temp_path = get_path("assets", "temp", f"chunk_{i}.mp3")
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                response.stream_to_file(temp_path)
                combined_audio += AudioSegment.from_file(temp_path)
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"⚠️ Lỗi chunk {i}: {e}")

        # Tăng tốc
        if SPEED_MULTIPLIER != 1.0:
            rate = combined_audio.frame_rate
            combined_audio = combined_audio._spawn(combined_audio.raw_data, overrides={
                "frame_rate": int(rate * SPEED_MULTIPLIER)
            }).set_frame_rate(rate)

        suffix = "long" if mode == "long" else "short"
        out_path = get_path("data", "audio", f"{episode_id}_{suffix}.mp3")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        combined_audio.export(out_path, format="mp3")
        
        return out_path

    except Exception as e:
        logger.error(f"❌ TTS Error: {e}", exc_info=True)
        return None
