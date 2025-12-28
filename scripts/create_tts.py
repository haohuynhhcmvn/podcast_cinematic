# scripts/create_tts.py
import logging
import os
import asyncio
import textwrap
import random
import time
from openai import OpenAI
from pydub import AudioSegment
import edge_tts
from utils import get_path

logger = logging.getLogger(__name__)

# =========================================================
# ⚙️ CẤU HÌNH TIẾT KIỆM TIỀN (GIỮ NGUYÊN)
# =========================================================
EDGE_VOICES = [
    "en-US-ChristopherNeural", 
    "en-US-EricNeural",        
    "en-US-GuyNeural",         
    "en-US-RogerNeural"        
]

USE_OPENAI_BACKUP = True
SPEED_MULTIPLIER = 1.15

# =========================================================
# 🧹 HÀM LỌC KỊCH BẢN (KHÔI PHỤC NGUYÊN BẢN CỦA BẠN)
# =========================================================
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
        if i < 5:
            lower = clean_line.lower()
            if any(kw in lower for kw in garbage_keywords): continue
            if len(clean_line.split()) < 6 and not clean_line.endswith(('.', '!', '?')): continue
        cleaned_lines.append(clean_line)
    return "\n".join(cleaned_lines)

# =========================================================
# 🎙️ ENGINE 1: EDGE TTS (HARDCORE RETRY)
# =========================================================
async def _run_edge_tts_with_retry(text, output_file):
    last_error = None
    for voice in EDGE_VOICES:
        for attempt in range(3):
            try:
                await asyncio.sleep(random.uniform(0.5, 2.0))
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_file)
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
                    return True 
            except Exception as e:
                last_error = e
                logger.warning(f"   ⚠️ Thất bại giọng {voice} (Lần {attempt+1}): {e}")
                if attempt < 2: await asyncio.sleep(2) 
    logger.error(f"❌ Edge TTS thất bại hoàn toàn. Lỗi cuối: {last_error}")
    return False

def generate_with_edge(chunks, episode_id):
    combined_audio = AudioSegment.empty()
    logger.info(f"🎙️ [Edge-TTS] Đang xử lý {len(chunks)} chunks...")
    
    for i, chunk in enumerate(chunks):
        temp_path = get_path("assets", "temp", f"{episode_id}_edge_{i}.mp3")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        success = asyncio.run(_run_edge_tts_with_retry(chunk, temp_path))
        if success:
            try:
                segment = AudioSegment.from_file(temp_path)
                combined_audio += segment
                if os.path.exists(temp_path): os.remove(temp_path)
            except Exception as e:
                logger.error(f"   ❌ File lỗi định dạng chunk {i}: {e}")
                return None
        else:
            return None
    return combined_audio

# =========================================================
# 💎 ENGINE 2: OPENAI TTS (BACKUP)
# =========================================================
def generate_with_openai(chunks, episode_id):
    if not USE_OPENAI_BACKUP:
        logger.error("🛑 DỪNG LẠI: Bạn đã TẮT chế độ OpenAI Backup.")
        return None

    logger.warning("💸 Đang dùng OpenAI TTS để cứu video...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return None
    client = OpenAI(api_key=api_key)
    
    combined_audio = AudioSegment.empty()
    for i, chunk in enumerate(chunks):
        try:
            response = client.audio.speech.create(model="tts-1", voice="onyx", input=chunk)
            temp_path = get_path("assets", "temp", f"{episode_id}_openai_{i}.mp3")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            response.stream_to_file(temp_path)
            combined_audio += AudioSegment.from_file(temp_path)
            if os.path.exists(temp_path): os.remove(temp_path)
        except Exception: return None
    return combined_audio

# =========================================================
# 🎧 MAIN FUNCTION (ĐÃ FIX LOGIC ĐẶT TÊN FILE CHO 5 SHORTS)
# =========================================================
def create_tts(full_text_or_path, episode_id, mode="long"):
    """
    Chấp nhận cả đường dẫn file script hoặc văn bản trực tiếp.
    """
    try:
        # 1. Lấy nội dung văn bản
        if os.path.exists(str(full_text_or_path)):
            with open(full_text_or_path, "r", encoding="utf-8") as f:
                raw_text = f.read()
        else:
            raw_text = str(full_text_or_path)

        full_text = clean_and_validate_script(raw_text.strip())
        if not full_text: return None

        # 2. Chia nhỏ text
        chunk_size = 750 
        chunks = textwrap.wrap(full_text, width=chunk_size, break_long_words=False)
        
        # 3. Chạy TTS (Edge -> OpenAI)
        combined_audio = generate_with_edge(chunks, episode_id)
        if combined_audio is None:
            combined_audio = generate_with_openai(chunks, episode_id)

        if combined_audio is None or len(combined_audio) == 0: return None

        # 4. Tăng tốc
        if SPEED_MULTIPLIER != 1.0:
            rate = combined_audio.frame_rate
            combined_audio = combined_audio._spawn(combined_audio.raw_data, overrides={
                "frame_rate": int(rate * SPEED_MULTIPLIER)
            }).set_frame_rate(rate)

        # 5. XÁC ĐỊNH TÊN FILE (FIX LỖI GHI ĐÈ)
        if mode == "long":
            file_name = f"{episode_id}_long.mp3"
        else:
            # Nếu episode_id là "101_s1" thì dùng luôn "101_s1.mp3"
            file_name = f"{episode_id}.mp3" if "_s" in str(episode_id) else f"{episode_id}_short.mp3"

        output_path = get_path("assets", "audio", file_name)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        combined_audio.export(output_path, format="mp3")
        
        logger.info(f"✅ TTS Success: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Create TTS Tổng: {e}")
        return None
