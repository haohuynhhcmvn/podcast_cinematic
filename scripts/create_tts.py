# scripts/create_tts.py
import logging
import os
import asyncio
import textwrap
from pydub import AudioSegment
import edge_tts  # Thư viện mới
from utils import get_path

logger = logging.getLogger(__name__)

# --- CẤU HÌNH EDGE TTS ---
# Giọng nam tính, phim tài liệu: en-US-ChristopherNeural
# Các giọng khác: en-US-GuyNeural, en-US-EricNeural
VOICE = "en-US-ChristopherNeural" 
SPEED_MULTIPLIER = 1.15  # Tăng tốc hậu kỳ bằng pydub (giữ nguyên logic cũ)

# Hàm lọc sạn kịch bản (GIỮ NGUYÊN)
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

# Hàm chạy Edge TTS (Bất đồng bộ)
async def _run_edge_tts(text, output_file):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def create_tts(script_path, episode_id, mode="long"):
    try:
        # 1. Đọc & Lọc kịch bản
        if not os.path.exists(script_path): return None
        with open(script_path, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()
            
        full_text = clean_and_validate_script(raw_text)
        if not full_text: return None

        # 2. Chunking (Chia nhỏ để tránh lỗi quá dài)
        # Edge TTS xử lý tốt đoạn dài, nhưng chia nhỏ vẫn an toàn hơn
        chunk_size = 2000
        chunks = textwrap.wrap(full_text, width=chunk_size, break_long_words=False)

        combined_audio = AudioSegment.empty()
        logger.info(f"🎙️ Tạo TTS FREE (Edge-TTS) - {mode} - {len(chunks)} chunks...")

        for i, chunk in enumerate(chunks):
            temp_path = get_path("assets", "temp", f"{episode_id}_chunk_{i}.mp3")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            try:
                # Gọi hàm async trong môi trường sync
                asyncio.run(_run_edge_tts(chunk, temp_path))
                
                # Nối audio
                segment = AudioSegment.from_file(temp_path)
                combined_audio += segment
                
                # Xóa file tạm
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"⚠️ Lỗi chunk {i}: {e}")
                continue

        if len(combined_audio) == 0: return None

        # 3. Tăng tốc (Logic cũ vẫn hoạt động tốt)
        if SPEED_MULTIPLIER != 1.0:
            original_rate = combined_audio.frame_rate
            new_rate = int(original_rate * SPEED_MULTIPLIER)
            combined_audio = combined_audio._spawn(combined_audio.raw_data, overrides={
                "frame_rate": new_rate
            })
            combined_audio = combined_audio.set_frame_rate(original_rate)
            logger.info(f"⚡ Đã tăng tốc độ audio: {SPEED_MULTIPLIER}x")

        # 4. Xuất file
        suffix = "long" if mode == "long" else "short"
        output_path = get_path("data", "audio", f"{episode_id}_{suffix}.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        combined_audio.export(output_path, format="mp3")
        logger.info(f"✅ TTS Hoàn tất (Free): {output_path}")
        
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Create TTS: {e}", exc_info=True)
        return None
