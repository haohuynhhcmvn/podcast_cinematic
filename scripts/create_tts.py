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
# Danh sách giọng nam Edge-TTS để xoay vòng nếu bị chặn
EDGE_VOICES = [
    "en-US-ChristopherNeural", # Ưu tiên 1: Giọng trầm (Tài liệu)
    "en-US-EricNeural",        # Ưu tiên 2: Giọng chắc (Tin tức)
    "en-US-GuyNeural",         # Ưu tiên 3: Giọng thường
    "en-US-RogerNeural"        # Ưu tiên 4
]

# 🚨 KILL SWITCH: Đặt là False để KHÔNG BAO GIỜ dùng OpenAI (Tiết kiệm tuyệt đối)
# Nếu Edge lỗi, quy trình sẽ dừng lại (Failed) thay vì trừ tiền thẻ của bạn.
# Đặt là True nếu bạn chấp nhận tốn tiền để cứu video bằng mọi giá. (False: Ngắt OpenAI)
USE_OPENAI_BACKUP = True

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
# 🎙️ ENGINE 1: EDGE TTS (HARDCORE RETRY)
# =========================================================
async def _run_edge_tts_with_retry(text, output_file):
    """
    Thử tạo TTS với cơ chế xoay vòng giọng và thử lại nhiều lần.
    """
    last_error = None
    
    # Thử từng giọng trong danh sách
    for voice in EDGE_VOICES:
        # Với mỗi giọng, thử lại 3 lần (Retry)
        for attempt in range(3):
            try:
                # Thêm delay ngẫu nhiên để tránh bị server chặn IP
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_file)
                
                # Kiểm tra xem file có tạo ra thật không và có dung lượng > 0 không
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
                    return True # Thành công
                
            except Exception as e:
                last_error = e
                logger.warning(f"   ⚠️ Thất bại giọng {voice} (Lần {attempt+1}): {e}")
                
                # THÊM DELAY NGẮN SAU KHI THẤT BẠI
                if attempt < 2: 
                    await asyncio.sleep(2) # Nghỉ 2 giây trước khi thử lại
                
    # Nếu thử hết mọi cách mà vẫn lỗi
    logger.error(f"❌ Edge TTS thất bại hoàn toàn. Lỗi cuối: {last_error}")
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
                logger.info(f"   ✅ Chunk {i+1} OK.")
            except Exception as e:
                logger.error(f"   ❌ File lỗi định dạng chunk {i}: {e}")
                return None
        else:
            logger.error(f"💀 Chunk {i} không thể tạo được bằng Edge TTS.")
            return None # Thất bại để kích hoạt backup (hoặc dừng)
            
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

        # Chia nhỏ text (Giảm xuống 750 ký tự cho an toàn hơn)
        chunk_size = 750 # <--- ĐÃ SỬA: 1500 -> 750
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
