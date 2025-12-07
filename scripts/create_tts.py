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
# ⚙️ CẤU HÌNH TIẾT KIỆM TIỀN (QUAN TRỌNG)
# =========================================================
# Danh sách giọng nam Edge-TTS để xoay vòng
EDGE_VOICES = [
    "en-US-ChristopherNeural", # Ưu tiên 1
    "en-US-EricNeural",        # Ưu tiên 2
    "en-US-GuyNeural",         # Ưu tiên 3
    "en-US-RogerNeural"        # Ưu tiên 4
]

# Số lần lặp lại toàn bộ danh sách giọng trước khi bỏ cuộc
MAX_MASTER_LOOPS = 5 

# 🚨 KILL SWITCH: Đặt là False để KHÔNG BAO GIỜ dùng OpenAI
USE_OPENAI_BACKUP = False 

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
# 🎙️ ENGINE 1: EDGE TTS (MASTER LOOP RETRY)
# =========================================================
async def _run_edge_tts_with_retry(text, output_file):
    """
    Thử tạo TTS với cơ chế xoay vòng giọng và lặp lại danh sách nhiều lần.
    """
    last_error = None
    
    # [CHIẾN THUẬT VÒNG LẶP] Lặp lại danh sách giọng 5 lần
    for loop_index in range(MAX_MASTER_LOOPS):
        logger.info(f"🔄 Đang thử tìm giọng Edge-TTS (Vòng lặp danh sách {loop_index + 1}/{MAX_MASTER_LOOPS})...")
        
        # Thử từng giọng trong danh sách
        for voice in EDGE_VOICES:
            try:
                # Thêm delay ngẫu nhiên để tránh bị server chặn IP (tăng dần theo số vòng lặp)
                wait_time = random.uniform(1.0, 3.0) + (loop_index * 0.5)
                await asyncio.sleep(wait_time)
                
                logger.info(f"   👉 Thử giọng: {voice}")
                
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_file)
                
                # Kiểm tra kết quả
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
                    logger.info(f"   ✅ Thành công với giọng: {voice}")
                    return True # Thoát ngay khi thành công
                
            except Exception as e:
                last_error = e
                logger.warning(f"   ⚠️ Lỗi giọng {voice}: {e}")
                
        # Nếu hết danh sách mà chưa được, nghỉ lâu hơn một chút trước khi sang vòng lặp tiếp theo
        logger.warning(f"⏳ Hết vòng {loop_index + 1}, nghỉ 5 giây trước khi thử lại danh sách...")
        await asyncio.sleep(5)

    # Nếu thử hết 5 vòng (tổng cộng 20 lần thử) mà vẫn lỗi
    logger.error(f"❌ Edge TTS thất bại hoàn toàn sau {MAX_MASTER_LOOPS} vòng lặp. Lỗi cuối: {last_error}")
    return False

def generate_with_edge(chunks, episode_id):
    """Quản lý việc tạo audio từng phần."""
    combined_audio = AudioSegment.empty()
    logger.info(f"🎙️ [Chiến thuật Tiết Kiệm] Đang chạy Edge-TTS ({len(chunks)} chunks)...")
    
    for i, chunk in enumerate(chunks):
        temp_path = get_path("assets", "temp", f"{episode_id}_edge_{i}.mp3")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        # Gọi hàm retry cứng đầu
        success = asyncio.run(_run_edge_tts_with_retry(chunk, temp_path))
        
        if success:
            try:
                segment = AudioSegment.from_file(temp_path)
                combined_audio += segment
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"   ❌ File lỗi định dạng chunk {i}: {e}")
                return None
        else:
            logger.error(f"💀 Chunk {i} không thể tạo được bằng Edge TTS.")
            return None 
            
    return combined_audio

# =========================================================
# 💎 ENGINE 2: OPENAI TTS (CHỈ KHI ĐƯỢC PHÉP)
# =========================================================
def generate_with_openai(chunks, episode_id):
    if not USE_OPENAI_BACKUP:
        logger.error("🛑 DỪNG LẠI: Edge TTS lỗi và bạn đã TẮT chế độ OpenAI Backup.")
        return None

    logger.warning("💸 Đang dùng OpenAI TTS (Tốn tiền) để cứu video...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return None
    client = OpenAI(api_key=api_key)
    
    combined_audio = AudioSegment.empty()
    for i, chunk in enumerate(chunks):
        try:
            response = client.audio.speech.create(
                model="tts-1", voice="onyx", input=chunk
            )
            temp_path = get_path("assets", "temp", f"{episode_id}_openai_{i}.mp3")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            response.stream_to_file(temp_path)
            combined_audio += AudioSegment.from_file(temp_path)
            os.remove(temp_path)
        except Exception: return None
    return combined_audio

# =========================================================
# 🎧 MAIN FUNCTION
# =========================================================
def create_tts(script_path, episode_id, mode="long"):
    try:
        if not os.path.exists(script_path): return None
        with open(script_path, "r", encoding="utf-8") as f:
            full_text = clean_and_validate_script(f.read().strip())
        if not full_text: return None

        # Chia nhỏ text
        chunk_size = 1500
        chunks = textwrap.wrap(full_text, width=chunk_size, break_long_words=False)
        
        # 1. Thử Edge (Miễn phí)
        combined_audio = generate_with_edge(chunks, episode_id)
        
        # 2. Nếu thất bại, check xem có cho dùng OpenAI không
        if combined_audio is None:
            if USE_OPENAI_BACKUP:
                combined_audio = generate_with_openai(chunks, episode_id)
            else:
                logger.error("❌ HỦY TASK: Không tạo được giọng đọc Free.")
                return None

        if combined_audio is None or len(combined_audio) == 0: return None

        # 3. Tăng tốc
        if SPEED_MULTIPLIER != 1.0:
            rate = combined_audio.frame_rate
            combined_audio = combined_audio._spawn(combined_audio.raw_data, overrides={
                "frame_rate": int(rate * SPEED_MULTIPLIER)
            }).set_frame_rate(rate)

        # Xuất file
        suffix = "long" if mode == "long" else "short"
        output_path = get_path("data", "audio", f"{episode_id}_{suffix}.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        combined_audio.export(output_path, format="mp3")
        
        logger.info(f"✅ TTS Success: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Create TTS Tổng: {e}", exc_info=True)
        return None
