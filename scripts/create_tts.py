# scripts/create_tts.py
import logging
import os
from openai import OpenAI
from pydub import AudioSegment
from utils import get_path

logger = logging.getLogger(__name__)

TTS_MODEL = "tts-1"
VOICE = "onyx"
SPEED_MULTIPLIER = 1.15 # <--- THAM SỐ TỐC ĐỘ MỚI (1.15x)

def create_tts(script_path, episode_id, mode="long"):
    """
    Chuyển đổi Text sang Speech.
    Hỗ trợ cắt nhỏ (Chunking) và điều chỉnh tốc độ phát lại.
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # 1. Đọc nội dung kịch bản
        if not os.path.exists(script_path):
            logger.error(f"Script not found: {script_path}")
            return None
            
        with open(script_path, "r", encoding="utf-8") as f:
            full_text = f.read().strip()

        if not full_text:
            return None

        # 2. Xử lý logic cắt nhỏ (Chunking)
        chunk_size = 3000
        chunks = []
        
        if len(full_text) <= chunk_size:
            chunks.append(full_text)
        else:
            start = 0
            while start < len(full_text):
                end = start + chunk_size
                if end >= len(full_text):
                    end = len(full_text)
                else:
                    last_period = full_text.rfind('.', start, end)
                    if last_period != -1 and last_period > start + 2000:
                         end = last_period + 1
                
                chunk = full_text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                start = end

        logger.info(f"🎙️ Đang tạo giọng đọc cho {episode_id} ({len(chunks)} phần)...")
        
        # 3. Gọi API và ghép Audio
        combined_audio = AudioSegment.empty()
        
        # Tạo thư mục tạm nếu chưa có
        temp_chunk_path = get_path("assets", "temp", "temp_chunk.mp3")
        os.makedirs(os.path.dirname(temp_chunk_path), exist_ok=True)

        for i, text_chunk in enumerate(chunks):
            try:
                response = client.audio.speech.create(
                    model=TTS_MODEL,
                    voice=VOICE,
                    input=text_chunk
                )
                
                response.stream_to_file(temp_chunk_path)
                segment = AudioSegment.from_file(temp_chunk_path)
                combined_audio += segment
                logger.info(f"   ✅ Xong phần {i+1}/{len(chunks)}")
            except Exception as chunk_error:
                logger.error(f"⚠️ Lỗi tạo chunk {i+1}: {chunk_error}")
                continue

        # 4. ĐIỀU CHỈNH TỐC ĐỘ PHÁT LẠI (1.15x)
        if SPEED_MULTIPLIER != 1.0:
            original_rate = combined_audio.frame_rate
            
            # 1. Thay đổi frame rate để tạo hiệu ứng âm thanh nhanh hơn
            # int() là cần thiết vì frame_rate phải là số nguyên
            faster_segment = combined_audio.set_frame_rate(int(original_rate * SPEED_MULTIPLIER))
            
            # 2. Đưa frame rate về lại ban đầu (Đây là trick để giữ pitch và tăng tempo)
            combined_audio = faster_segment.set_frame_rate(original_rate)
            logger.info(f"⏱️ Đã tăng tốc độ audio lên {SPEED_MULTIPLIER}x.")


        # 5. Xuất file audio cuối cùng
        suffix = "long" if mode == "long" else "short"
        output_path = get_path("data", "audio", f"{episode_id}_{suffix}.mp3")
        
        # Tự động tạo thư mục cha nếu chưa có
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        combined_audio.export(output_path, format="mp3")
        logger.info(f"🎧 TTS Hoàn tất: {output_path}")
        
        # Dọn dẹp file tạm
        if os.path.exists(temp_chunk_path):
            os.remove(temp_chunk_path)

        return output_path

    except Exception as e:
        logger.error(f"❌ TTS Error: {e}", exc_info=True)
        return None
