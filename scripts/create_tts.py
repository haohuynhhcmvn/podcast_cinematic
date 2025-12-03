# scripts/create_tts.py
import logging
import os
from openai import OpenAI
from pydub import AudioSegment  # Cần thư viện này để ghép file audio
from utils import get_path

logger = logging.getLogger(__name__)

# Mô hình TTS (Giữ nguyên tts-1 cho rẻ và nhanh, tts-1-hd đắt hơn)
TTS_MODEL = "tts-1"
VOICE = "onyx"  # Giọng nam trầm, kể chuyện tốt

def create_tts(script_path, episode_id, mode="long"):
    """
    Chuyển đổi Text sang Speech.
    Hỗ trợ kịch bản siêu dài bằng cách cắt nhỏ (Chunking) để vượt qua giới hạn 4096 ký tự của OpenAI.
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
        # OpenAI giới hạn 4096 chars. Ta cắt an toàn ở mức 3000 để tránh lỗi ngắt câu.
        chunk_size = 3000
        chunks = []
        
        # Nếu text ngắn thì chỉ có 1 chunk
        if len(full_text) <= chunk_size:
            chunks.append(full_text)
        else:
            # Cắt thông minh theo dấu chấm câu để giọng đọc không bị đứt quãng vô duyên
            # (Logic đơn giản: Cứ cắt thô, nhưng tốt nhất là split theo paragraph nếu có thể)
            # Ở đây dùng cách cắt theo độ dài và tìm dấu chấm gần nhất.
            start = 0
            while start < len(full_text):
                end = start + chunk_size
                if end >= len(full_text):
                    end = len(full_text)
                else:
                    # Tìm dấu chấm gần nhất để ngắt
                    last_period = full_text.rfind('.', start, end)
                    if last_period != -1 and last_period > start + 2000:
                         end = last_period + 1
                
                chunk = full_text[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                start = end

        logger.info(f"🎙️ Đang tạo giọng đọc cho {episode_id} ({len(chunks)} phần)...")
        
        # 3. Gọi API cho từng phần và ghép lại
        combined_audio = AudioSegment.empty()
        temp_chunk_path = get_path("assets", "temp", "temp_chunk.mp3")
        os.makedirs(os.path.dirname(temp_chunk_path), exist_ok=True)

        for i, text_chunk in enumerate(chunks):
            response = client.audio.speech.create(
                model=TTS_MODEL,
                voice=VOICE,
                input=text_chunk
            )
            
            # Lưu tạm
            response.stream_to_file(temp_chunk_path)
            
            # Ghép vào file tổng
            segment = AudioSegment.from_file(temp_chunk_path)
            combined_audio += segment
            logger.info(f"   ✅ Xong phần {i+1}/{len(chunks)}")

        # 4. Xuất file audio cuối cùng
        # Tên file tùy theo long hay short
        suffix = "long" if mode == "long" else "short"
        output_path = get_path("data", "audio", f"{episode_id}_{suffix}.mp3")
        
        combined_audio.export(output_path, format="mp3")
        logger.info(f"🎧 TTS Hoàn tất: {output_path}")
        
        # Dọn dẹp file tạm
        if os.path.exists(temp_chunk_path):
            os.remove(temp_chunk_path)

        return output_path

    except Exception as e:
        logger.error(f"❌ TTS Error: {e}", exc_info=True)
        return None
