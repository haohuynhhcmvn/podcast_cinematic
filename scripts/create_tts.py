# === scripts/create_tts.py (FINAL FIXED VERSION) ===
import logging
import os
import asyncio
import textwrap
import random
import re
import time
from openai import OpenAI
from pydub import AudioSegment
import edge_tts
from utils import get_path

logger = logging.getLogger(__name__)

# =========================================================
# ⚙️ CẤU HÌNH HỆ THỐNG
# =========================================================

# Danh sách giọng nam Edge-TTS (Anh - Mỹ) để xoay vòng
EDGE_VOICES = [
    "en-US-ChristopherNeural", # Trầm, điện ảnh
    "en-US-EricNeural",        # Mạnh mẽ, tin tức
    "en-US-GuyNeural",         # Tự nhiên
    "en-US-RogerNeural"        # Hơi máy móc chút nhưng rõ
]

# 🚨 BACKUP PLAN: True = Dùng OpenAI nếu Edge lỗi (Tốn tiền)
USE_OPENAI_BACKUP = True 

# Tốc độ đọc (1.0 = chuẩn, 1.15 = nhanh hơn chút cho YouTube Shorts)
SPEED_MULTIPLIER = 1.15

# =========================================================
# 🧹 MODULE 1: LÀM SẠCH KỊCH BẢN (QUAN TRỌNG)
# =========================================================
def clean_text_for_tts(text):
    """Lọc bỏ ký tự đặc biệt khiến EdgeTTS bị lỗi."""
    if not text: return ""

    # 1. Xóa Markdown của GPT (*bold*, # Title)
    text = text.replace("*", "").replace("#", "").replace("`", "")

    # 2. Xóa các chỉ dẫn trong ngoặc: [Music], (Sigh), [Applause]
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)

    # 3. Xóa các từ khóa kịch bản thừa ở đầu câu
    # Ví dụ: "Narrator: Once upon a time..." -> "Once upon a time..."
    text = re.sub(r"(?i)^(Narrator|Host|Speaker|Scene|Intro|Outro):", "", text)

    # 4. Xóa khoảng trắng thừa
    text = " ".join(text.split())
    
    return text.strip()

# =========================================================
# 🎙️ MODULE 2: EDGE TTS (ASYNC CORE)
# =========================================================
async def _generate_edge_one_chunk(text, output_path):
    """
    Sinh 1 đoạn audio ngắn. 
    Tự động thử lại (Retry) và đổi giọng (Rotate Voice) nếu lỗi.
    """
    # Thử tối đa 3 lần cho mỗi đoạn
    for attempt in range(3):
        # Chọn ngẫu nhiên 1 giọng để tránh bị server Microsoft chặn IP liên tục
        voice = random.choice(EDGE_VOICES)
        
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            
            # [CHECK QUAN TRỌNG] File có tồn tại và có dữ liệu không?
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return True # Thành công!
            
        except Exception as e:
            logger.warning(f"⚠️ EdgeTTS Lỗi (Lần {attempt+1}) - Giọng {voice}: {e}")
            # Nghỉ 1 chút trước khi thử lại
            await asyncio.sleep(1.5)
            
    return False # Thất bại sau 3 lần

def run_edge_tts_batch(chunks, episode_id):
    """Chạy vòng lặp xử lý từng chunk."""
    combined = AudioSegment.empty()
    logger.info(f"🎙️ [Edge-TTS] Đang xử lý {len(chunks)} đoạn...")

    for i, chunk in enumerate(chunks):
        # Lọc rác lần cuối
        safe_text = clean_text_for_tts(chunk)
        if len(safe_text) < 2: continue # Bỏ qua câu quá ngắn

        temp_file = get_path("assets", "temp", f"{episode_id}_edge_{i}.mp3")
        
        # Gọi hàm async trong môi trường sync
        success = asyncio.run(_generate_edge_one_chunk(safe_text, temp_file))
        
        if success:
            try:
                # Đọc file vào RAM ngay lập tức
                segment = AudioSegment.from_file(temp_file)
                combined += segment
                
                # Xóa file tạm ngay để dọn rác
                os.remove(temp_file)
            except Exception as e:
                logger.error(f"❌ Lỗi thư viện Pydub đọc file {temp_file}: {e}")
                return None
        else:
            logger.error(f"💀 EdgeTTS thất bại ở đoạn {i}: '{safe_text[:30]}...'")
            return None # Trả về None để kích hoạt OpenAI Backup
            
    return combined

# =========================================================
# 💎 MODULE 3: OPENAI TTS (FALLBACK)
# =========================================================
def run_openai_tts(chunks, episode_id):
    if not USE_OPENAI_BACKUP: return None
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return None

    logger.warning("💰 Đang dùng OpenAI TTS để cứu video...")
    client = OpenAI(api_key=api_key)
    combined = AudioSegment.empty()

    for i, chunk in enumerate(chunks):
        safe_text = clean_text_for_tts(chunk)
        if len(safe_text) < 2: continue

        try:
            response = client.audio.speech.create(
                model="tts-1", voice="onyx", input=safe_text
            )
            temp_file = get_path("assets", "temp", f"{episode_id}_openai_{i}.mp3")
            response.stream_to_file(temp_file)
            
            combined += AudioSegment.from_file(temp_file)
            os.remove(temp_file)
        except Exception as e:
            logger.error(f"❌ OpenAI TTS Error: {e}")
            return None
            
    return combined

# =========================================================
# 🚀 MAIN FUNCTION (ĐƯỢC GỌI BỞI GLUE_PIPELINE)
# =========================================================
def create_tts(script_path, episode_id, mode="long"):
    """
    Hàm chính: Đọc script -> Text Clean -> Chunking -> TTS -> Speedup -> Save MP3
    """
    try:
        # 1. Đọc file Script
        if not os.path.exists(script_path):
            logger.error(f"❌ Không tìm thấy file script: {script_path}")
            return None
            
        with open(script_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # 2. Chia nhỏ văn bản (Chunking)
        # Giảm xuống 800 ký tự để an toàn cho EdgeTTS
        chunks = textwrap.wrap(raw_text, width=800, break_long_words=False)
        if not chunks: return None

        # 3. Chạy Engine 1: Edge TTS (Free)
        final_audio = run_edge_tts_batch(chunks, episode_id)

        # 4. Chạy Engine 2: OpenAI (Nếu Engine 1 lỗi)
        if final_audio is None:
            final_audio = run_openai_tts(chunks, episode_id)

        # Nếu cả 2 đều lỗi -> Hủy
        if final_audio is None or len(final_audio) < 1000: # < 1 giây
            logger.error("❌ HỦY TASK: Không thể tạo giọng đọc.")
            return None

        # 5. Xử lý hậu kỳ: Tăng tốc độ đọc (Speed Up)
        if SPEED_MULTIPLIER != 1.0:
            logger.info(f"⏩ Đang tăng tốc audio: x{SPEED_MULTIPLIER}")
            rate = final_audio.frame_rate
            final_audio = final_audio._spawn(final_audio.raw_data, overrides={
                "frame_rate": int(rate * SPEED_MULTIPLIER)
            }).set_frame_rate(rate)

        # 6. Xuất file kết quả
        suffix = "long" if mode == "long" else "short"
        # Đảm bảo thư mục tồn tại
        output_dir = get_path("data", "audio")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"{episode_id}_{suffix}.mp3")
        
        final_audio.export(output_path, format="mp3")
        logger.info(f"✅ TTS Hoàn tất: {output_path} (Độ dài: {len(final_audio)/1000:.1f}s)")
        
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng trong create_tts: {e}", exc_info=True)
        return None
