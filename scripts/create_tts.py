# scripts/create_tts.py
import logging
import os
import asyncio
import textwrap
import random
import time
from pydub import AudioSegment
import edge_tts
from utils import get_path

logger = logging.getLogger(__name__)

# =========================================================
# ⚙️ CẤU HÌNH
# =========================================================
EDGE_VOICES = [
    "en-US-ChristopherNeural", 
    "en-US-EricNeural",       
    "en-US-GuyNeural",         
    "en-US-RogerNeural"        
]

# Tốc độ đọc
SPEED_MULTIPLIER = 1.15

# =========================================================
# 🛠️ HÀM HỖ TRỢ
# =========================================================
async def run_edge_tts(text, voice, output_file):
    """Chạy Edge TTS (Async)"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def generate_with_edge(chunks, episode_id, attempt=0):
    """
    Tạo audio từ danh sách chunks văn bản bằng Edge-TTS.
    """
    temp_files = []
    
    # Chọn giọng ngẫu nhiên để tránh bị lặp/chặn
    voice = random.choice(EDGE_VOICES)
    
    try:
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            
            temp_path = get_path("assets", "temp", f"{episode_id}_part_{i}_{attempt}.mp3")
            
            # Gọi hàm async trong môi trường sync
            asyncio.run(run_edge_tts(chunk, voice, temp_path))
            
            if os.path.exists(temp_path):
                temp_files.append(temp_path)
            else:
                logger.error(f"❌ Edge-TTS thất bại ở chunk {i}")
                return None
        
        # Ghép các file lại
        combined = AudioSegment.empty()
        for f in temp_files:
            combined += AudioSegment.from_file(f)
            # Thêm khoảng nghỉ ngắn giữa các đoạn (300ms)
            combined += AudioSegment.silent(duration=300) 
            
        return combined

    except Exception as e:
        logger.error(f"❌ Lỗi Edge-TTS: {e}")
        return None

# =========================================================
# 🚀 MAIN FUNCTION
# =========================================================
def create_tts(episode_id, name, mode="long"):
    """
    Main function để tạo giọng đọc.
    mode: "long" hoặc "short"
    """
    logger.info(f"🎤 Đang tạo giọng đọc ({mode.upper()}) cho: {name}")
    
    try:
        # 1. XÁC ĐỊNH ĐÚNG FILE KỊCH BẢN (QUAN TRỌNG)
        # Tìm file có đuôi _en.txt trước
        input_filename = f"{episode_id}_{mode}_en.txt"
        script_path = get_path("data", "episodes", input_filename)
        
        # Fallback: Nếu không thấy _en, tìm file thường
        if not os.path.exists(script_path):
            script_path = get_path("data", "episodes", f"{episode_id}_{mode}.txt")

        if not os.path.exists(script_path):
            logger.error(f"❌ KHÔNG TÌM THẤY FILE KỊCH BẢN: {script_path}")
            return None

        # 2. Đọc nội dung
        with open(script_path, "r", encoding="utf-8") as f:
            full_text = f.read().strip()
            
        if not full_text:
            logger.error("❌ File kịch bản rỗng!")
            return None

        # 3. Chia nhỏ văn bản (Chunking) để tránh giới hạn API
        # Edge-TTS ổn định nhất với đoạn dưới 2000 ký tự
        chunk_size = 1500 
        chunks = textwrap.wrap(full_text, width=chunk_size, break_long_words=False)
        
        logger.info(f"🔹 Chia văn bản thành {len(chunks)} đoạn để xử lý.")

        # 4. Tạo Audio
        combined_audio = generate_with_edge(chunks, episode_id)
        
        if combined_audio is None:
            logger.error("❌ Không tạo được audio (Edge-TTS trả về None)")
            return None

        # 5. Tăng tốc độ đọc (Speed up)
        if SPEED_MULTIPLIER != 1.0:
            logger.info(f"⏩ Đang tăng tốc độ đọc x{SPEED_MULTIPLIER}...")
            # Pydub speedup trick (thay đổi frame rate)
            new_rate = int(combined_audio.frame_rate * SPEED_MULTIPLIER)
            combined_audio = combined_audio._spawn(combined_audio.raw_data, overrides={
                "frame_rate": new_rate
            }).set_frame_rate(combined_audio.frame_rate)

        # 6. Xuất file cuối cùng
        # Tên file output cũng nên khớp với quy chuẩn
        output_filename = f"{episode_id}_{mode}.mp3"
        output_path = get_path("outputs", "audio", output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        combined_audio.export(output_path, format="mp3")
        
        logger.info(f"✅ TTS Hoàn tất: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng trong create_tts: {e}", exc_info=True)
        return None
