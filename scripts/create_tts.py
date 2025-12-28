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
# ⚙️ CẤU HÌNH GIỌNG ĐỌC
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
# 🧹 HÀM LÀM SẠCH VÀ CHUẨN HÓA KỊCH BẢN
# =========================================================
def clean_and_validate_script(text):
    if not text: return ""
    # Loại bỏ các tag kỹ thuật để TTS không đọc lên
    text = text.replace('**', '').replace('__', '')
    text = os.linesep.join([line for line in text.splitlines() if not line.strip().startswith(('[', 'Visual', 'Sound', 'Scene'))])
    return text.strip()

# =========================================================
# 🎙️ CORE TTS LOGIC (EDGE-TTS)
# =========================================================
async def generate_with_edge(chunks, episode_id):
    combined = AudioSegment.empty()
    voice = random.choice(EDGE_VOICES)
    
    for i, chunk in enumerate(chunks):
        temp_path = get_path("assets", "temp", f"{episode_id}_part_{i}.mp3")
        try:
            communicate = edge_tts.Communicate(chunk, voice)
            await communicate.save(temp_path)
            
            segment = AudioSegment.from_mp3(temp_path)
            combined += segment
            if os.path.exists(temp_path): os.remove(temp_path)
        except Exception as e:
            logger.error(f"⚠️ Lỗi Edge-TTS tại chunk {i}: {e}")
            return None
    return combined

# =========================================================
# 🚀 HÀM CHÍNH: CREATE TTS (CẬP NHẬT CHO 5 SHORTS)
# =========================================================
def create_tts(text, episode_id, mode="long", short_index=None):
    """
    Tạo giọng đọc cho Video Dài hoặc Video Shorts (Part 1-5).
    """
    if not text:
        logger.error("❌ Không có nội dung text để tạo TTS.")
        return None

    full_text = clean_and_validate_script(text)
    
    # Chia nhỏ text để tránh lỗi timeout API (750 ký tự/chunk)
    chunk_size = 750 
    chunks = textwrap.wrap(full_text, width=chunk_size, break_long_words=False)
    
    # Chạy loop async để tạo audio
    loop = asyncio.get_event_loop()
    combined_audio = loop.run_until_complete(generate_with_edge(chunks, episode_id))
    
    # Fallback sang OpenAI nếu Edge lỗi (nếu cấu hình cho phép)
    if combined_audio is None and USE_OPENAI_BACKUP:
        logger.warning("🔄 Đang thử dùng OpenAI Backup...")
        # (Giả định hàm generate_with_openai đã có sẵn trong dự án của bạn)
        # combined_audio = generate_with_openai(chunks, episode_id)

    if combined_audio is None:
        logger.error("❌ Thất bại trong việc tạo âm thanh.")
        return None

    # Tăng tốc độ giọng đọc theo SPEED_MULTIPLIER
    if SPEED_MULTIPLIER != 1.0:
        rate = combined_audio.frame_rate
        combined_audio = combined_audio._spawn(combined_audio.raw_data, overrides={
            "frame_rate": int(rate * SPEED_MULTIPLIER)
        }).set_frame_rate(rate)

    # ĐỊNH DANH FILE OUTPUT (QUAN TRỌNG: Tránh ghi đè)
    if mode == "short":
        suffix = f"short_{short_index}" if short_index else "short"
    else:
        suffix = "long"

    output_path = get_path("data", "audio", f"{episode_id}_{suffix}.mp3")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    combined_audio.export(output_path, format="mp3")
    logger.info(f"✅ Đã lưu Audio {mode.upper()}: {output_path}")
    
    return output_path
