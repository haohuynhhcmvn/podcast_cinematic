# scripts/create_tts.py
import logging
import os
import textwrap
from openai import OpenAI
from pydub import AudioSegment
from utils import get_path

logger = logging.getLogger(__name__)

# Cấu hình
TTS_MODEL = "tts-1"
VOICE = "onyx" # Giọng trầm, nam tính (Rất hợp kênh lịch sử/huyền thoại)
SPEED_MULTIPLIER = 1.15 # Tăng tốc nhẹ để bớt buồn ngủ

# =========================================================
# 🧹 HÀM LỌC SẠN KỊCH BẢN (QUAN TRỌNG)
# =========================================================
def clean_and_validate_script(text):
    """
    Loại bỏ các dòng tiêu đề, meta-data thừa (VD: 'Biography Script...', 'Title:')
    để tránh việc AI đọc thành tiếng gây mất chuyên nghiệp.
    """
    if not text: return ""
    
    lines = text.split('\n')
    cleaned_lines = []
    
    # Danh sách từ khóa rác thường xuất hiện ở dòng đầu do GPT sinh ra
    garbage_keywords = [
        "script", "biography", "title:", "host:", "narrator:", 
        "intro:", "outro:", "music:", "visual:", "scene:", 
        "fades in", "camera", "voiceover"
    ]
    
    for i, line in enumerate(lines):
        clean_line = line.strip()
        
        # Bỏ dòng trống
        if not clean_line: 
            continue
            
        # CHỈ KIỂM TRA KỸ 5 DÒNG ĐẦU TIÊN (Header)
        if i < 5:
            lower_line = clean_line.lower()
            
            # 1. Nếu dòng chứa từ khóa rác (VD: "biography script of...")
            if any(kw in lower_line for kw in garbage_keywords):
                logger.warning(f"🗑️ Đã xóa dòng rác đầu file: '{clean_line}'")
                continue
                
            # 2. Nếu dòng quá ngắn (Kiểu tiêu đề) mà không phải câu hoàn chỉnh (không có dấu chấm)
            # VD: "ALEXANDER THE GREAT" -> Xóa để vào thẳng Hook
            if len(clean_line.split()) < 6 and not clean_line.endswith(('.', '!', '?')):
                 logger.warning(f"🗑️ Đã xóa tiêu đề ngắn: '{clean_line}'")
                 continue
                 
        cleaned_lines.append(clean_line)
        
    return "\n".join(cleaned_lines)

# =========================================================
# 🎧 HÀM TẠO TTS CHÍNH
# =========================================================
def create_tts(script_path, episode_id, mode="long"):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # 1. Đọc nội dung file
        if not os.path.exists(script_path):
            logger.error(f"❌ Script not found: {script_path}")
            return None
            
        with open(script_path, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()

        # 2. [FIX] LÀM SẠCH KỊCH BẢN TRƯỚC KHI GỬI CHO AI
        full_text = clean_and_validate_script(raw_text)
        
        if not full_text:
            logger.error("❌ Kịch bản rỗng sau khi lọc.")
            return None

        # 3. Chia nhỏ (Chunking) thông minh để tránh giới hạn API
        # Dùng textwrap để không cắt đôi từ
        chunk_size = 3000
        chunks = textwrap.wrap(full_text, width=chunk_size, break_long_words=False, replace_whitespace=False)

        # 4. Gọi API OpenAI TTS
        combined_audio = AudioSegment.empty()
        
        logger.info(f"🎙️ Đang tạo TTS ({len(chunks)} phần) - Mode: {mode}...")
        
        for i, chunk in enumerate(chunks):
            try:
                response = client.audio.speech.create(
                    model=TTS_MODEL,
                    voice=VOICE,
                    input=chunk
                )
                
                # Lưu tạm từng phần
                temp_chunk_path = get_path("assets", "temp", f"{episode_id}_chunk_{i}.mp3")
                os.makedirs(os.path.dirname(temp_chunk_path), exist_ok=True)
                
                response.stream_to_file(temp_chunk_path)
                
                # Ghép vào audio tổng
                segment = AudioSegment.from_file(temp_chunk_path)
                combined_audio += segment
                
                # Dọn dẹp ngay
                os.remove(temp_chunk_path)
                
            except Exception as e:
                logger.error(f"⚠️ Lỗi chunk {i}: {e}")
                continue

        if len(combined_audio) == 0:
            return None

        # 5. [FIX] TĂNG TỐC ĐỘ (SPEED UP) 1.15x
        # Kỹ thuật: Tăng frame rate giả (nhanh + cao độ tăng) -> Set lại frame rate gốc
        if SPEED_MULTIPLIER != 1.0:
            original_rate = combined_audio.frame_rate
            new_rate = int(original_rate * SPEED_MULTIPLIER)
            
            # Hack tốc độ bằng pydub
            combined_audio = combined_audio._spawn(combined_audio.raw_data, overrides={
                "frame_rate": new_rate
            })
            combined_audio = combined_audio.set_frame_rate(original_rate)
            
            logger.info(f"⚡ Đã tăng tốc độ audio: {SPEED_MULTIPLIER}x")

        # 6. Xuất file cuối cùng
        suffix = "long" if mode == "long" else "short"
        output_path = get_path("data", "audio", f"{episode_id}_{suffix}.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        combined_audio.export(output_path, format="mp3")
        logger.info(f"✅ TTS Hoàn tất: {output_path}")
        
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Create TTS: {e}", exc_info=True)
        return None
