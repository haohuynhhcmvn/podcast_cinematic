# scripts/create_tts.py
import logging
import os
import asyncio
import textwrap
from openai import OpenAI
from pydub import AudioSegment
import edge_tts
from utils import get_path

logger = logging.getLogger(__name__)

# --- CẤU HÌNH ---
# 1. Edge TTS (Free)
EDGE_VOICE = "en-US-ChristopherNeural"
# 2. OpenAI TTS (Paid Fallback)
OPENAI_MODEL = "tts-1"
OPENAI_VOICE = "onyx"

SPEED_MULTIPLIER = 1.15

# =========================================================
# 🧹 HÀM LỌC KỊCH BẢN
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
# 🎙️ ENGINE 1: EDGE TTS (MIỄN PHÍ)
# =========================================================
async def _run_edge_tts(text, output_file):
    """Hàm bất đồng bộ gọi Edge TTS"""
    communicate = edge_tts.Communicate(text, EDGE_VOICE)
    await communicate.save(output_file)

def generate_with_edge(chunks, episode_id):
    """Thử tạo audio bằng Edge TTS."""
    combined_audio = AudioSegment.empty()
    logger.info(f"🎙️ [Thử] Tạo TTS FREE (Edge-TTS) - {len(chunks)} chunks...")
    
    for i, chunk in enumerate(chunks):
        temp_path = get_path("assets", "temp", f"{episode_id}_edge_{i}.mp3")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        try:
            asyncio.run(_run_edge_tts(chunk, temp_path))
            segment = AudioSegment.from_file(temp_path)
            combined_audio += segment
            os.remove(temp_path)
        except Exception as e:
            logger.error(f"⚠️ Edge TTS thất bại ở chunk {i}: {e}")
            # Nếu lỗi bất kỳ chunk nào, coi như thất bại toàn bộ để chuyển sang backup
            return None
            
    return combined_audio

# =========================================================
# 💎 ENGINE 2: OPENAI TTS (TRẢ PHÍ - DỰ PHÒNG)
# =========================================================
def generate_with_openai(chunks, episode_id):
    """Fallback: Tạo audio bằng OpenAI TTS khi bản Free lỗi."""
    logger.warning("🚨 Edge TTS bị lỗi! Chuyển sang OpenAI TTS (Trả phí) để cứu video...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ Không có API Key để chạy Backup OpenAI.")
        return None
        
    client = OpenAI(api_key=api_key)
    combined_audio = AudioSegment.empty()

    for i, chunk in enumerate(chunks):
        try:
            response = client.audio.speech.create(
                model=OPENAI_MODEL,
                voice=OPENAI_VOICE,
                input=chunk
            )
            temp_path = get_path("assets", "temp", f"{episode_id}_openai_{i}.mp3")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            response.stream_to_file(temp_path)
            segment = AudioSegment.from_file(temp_path)
            combined_audio += segment
            os.remove(temp_path)
        except Exception as e:
            logger.error(f"❌ OpenAI TTS cũng lỗi ở chunk {i}: {e}")
            return None
            
    return combined_audio

# =========================================================
# 🎧 HÀM ĐIỀU PHỐI CHÍNH
# =========================================================
def create_tts(script_path, episode_id, mode="long"):
    try:
        # 1. Chuẩn bị Script
        if not os.path.exists(script_path): return None
        with open(script_path, "r", encoding="utf-8") as f:
            full_text = clean_and_validate_script(f.read().strip())
        if not full_text: return None

        # Chia nhỏ text
        chunk_size = 2000
        chunks = textwrap.wrap(full_text, width=chunk_size, break_long_words=False)
        
        # 2. [CHIẾN LƯỢC] Thử Free trước, nếu chết thì dùng Paid
        combined_audio = generate_with_edge(chunks, episode_id)
        
        if combined_audio is None:
            # Kích hoạt Backup
            combined_audio = generate_with_openai(chunks, episode_id)

        if combined_audio is None or len(combined_audio) == 0:
            logger.error("❌ THẤT BẠI: Cả Edge và OpenAI đều không tạo được giọng đọc.")
            return None

        # 3. Tăng tốc độ (Hậu kỳ)
        if SPEED_MULTIPLIER != 1.0:
            rate = combined_audio.frame_rate
            combined_audio = combined_audio._spawn(combined_audio.raw_data, overrides={
                "frame_rate": int(rate * SPEED_MULTIPLIER)
            }).set_frame_rate(rate)
            logger.info(f"⚡ Đã tăng tốc audio: {SPEED_MULTIPLIER}x")

        # 4. Xuất file
        suffix = "long" if mode == "long" else "short"
        output_path = get_path("data", "audio", f"{episode_id}_{suffix}.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        combined_audio.export(output_path, format="mp3")
        logger.info(f"✅ TTS Hoàn tất: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Create TTS Tổng: {e}", exc_info=True)
        return None
