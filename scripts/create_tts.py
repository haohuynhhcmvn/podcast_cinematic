# === scripts/create_tts.py ===
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

# Tốc độ đọc (1.15 là chuẩn cho Short, 1.1 cho Long để dễ nghe hơn)
SPEED_MULTIPLIER_LONG = 1.10
SPEED_MULTIPLIER_SHORT = 1.15

# =========================================================
# 🧹 MODULE 1: LÀM SẠCH KỊCH BẢN
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
    text = re.sub(r"(?i)^(Narrator|Host|Speaker|Scene|Intro|Outro):", "", text)

    # 4. Xóa khoảng trắng thừa
    text = " ".join(text.split())
    
    return text.strip()

# =========================================================
# 🎙️ MODULE 2: EDGE TTS (XỬ LÝ TỪNG CHUNK)
# =========================================================
async def _generate_edge_one_chunk(text, output_path):
    """
    Sinh 1 đoạn audio ngắn. 
    Tự động thử lại (Retry) và đổi giọng (Rotate Voice) nếu lỗi.
    """
    # Thử tối đa 3 lần cho mỗi đoạn
    for attempt in range(3):
        voice = random.choice(EDGE_VOICES)
        try:
            # Thêm độ trễ ngẫu nhiên để tránh bị chặn
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            
            # [CHECK QUAN TRỌNG] File có tồn tại và có dữ liệu (>1KB) không?
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return True 
            
        except Exception as e:
            logger.warning(f"⚠️ EdgeTTS Chunk Lỗi (Lần {attempt+1}): {e}")
            
    return False

# =========================================================
# 💎 MODULE 3: OPENAI TTS (FALLBACK CHO TỪNG CHUNK)
# =========================================================
def _generate_openai_one_chunk(text, output_path):
    if not USE_OPENAI_BACKUP: return False
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return False

    try:
        client = OpenAI(api_key=api_key)
        response = client.audio.speech.create(
            model="tts-1", voice="onyx", input=text
        )
        response.stream_to_file(output_path)
        return True
    except Exception as e:
        logger.error(f"❌ OpenAI TTS Error: {e}")
        return False

# =========================================================
# 🚀 MAIN FUNCTION: XỬ LÝ GHÉP CHUNK (BẤT TỬ)
# =========================================================
def create_tts(script_path, episode_id, mode="long"):
    """
    Hàm chính: Đọc script -> Chia nhỏ -> Xử lý từng phần -> Ghép lại
    """
    try:
        # 1. Đọc file Script
        if not os.path.exists(script_path):
            logger.error(f"❌ Không tìm thấy file script: {script_path}")
            return None
            
        with open(script_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # 2. Chia nhỏ văn bản (Chunking) - AN TOÀN TUYỆT ĐỐI
        # Chia thành các đoạn nhỏ 800 ký tự để không bao giờ bị Timeout
        full_text = clean_text_for_tts(raw_text)
        chunks = textwrap.wrap(full_text, width=800, break_long_words=False)
        
        if not chunks: return None

        logger.info(f"🎙️ Bắt đầu TTS: {len(chunks)} đoạn (Mode: {mode})...")

        # Khởi tạo file Audio rỗng
        combined = AudioSegment.empty()
        
        # 3. Vòng lặp xử lý từng đoạn (Tuần tự)
        for i, chunk in enumerate(chunks):
            if len(chunk) < 2: continue
            
            chunk_file = get_path("assets", "temp", f"{episode_id}_part_{i}.mp3")
            
            # A. Thử EdgeTTS trước
            success = asyncio.run(_generate_edge_one_chunk(chunk, chunk_file))
            
            # B. Nếu Edge lỗi, thử OpenAI
            if not success:
                logger.warning(f"⚠️ Chuyển sang OpenAI Backup cho đoạn {i}...")
                success = _generate_openai_one_chunk(chunk, chunk_file)
            
            # C. Ghép vào file tổng
            if success and os.path.exists(chunk_file):
                try:
                    segment = AudioSegment.from_file(chunk_file)
                    combined += segment
                    # Dọn rác ngay lập tức để nhẹ RAM
                    os.remove(chunk_file)
                    
                    # Log tiến độ mỗi 5 đoạn để biết không bị treo
                    if i % 5 == 0:
                        logger.info(f"   ...Đã xong {i+1}/{len(chunks)} đoạn")
                except Exception as e:
                    logger.error(f"❌ Lỗi ghép file audio đoạn {i}: {e}")
            else:
                logger.error(f"💀 BỎ QUA ĐOẠN {i} (Không tạo được Audio): '{chunk[:20]}...'")

        # 4. Kiểm tra kết quả
        if len(combined) < 5000: # Nếu tổng file < 5 giây là lỗi
            logger.error("❌ HỦY TASK: Audio quá ngắn hoặc lỗi toàn bộ.")
            return None

        # 5. Xử lý hậu kỳ: Tăng tốc độ đọc (Speed Up)
        speed = SPEED_MULTIPLIER_LONG if mode == "long" else SPEED_MULTIPLIER_SHORT
        
        if speed != 1.0:
            logger.info(f"⏩ Tăng tốc audio: x{speed}")
            rate = combined.frame_rate
            combined = combined._spawn(combined.raw_data, overrides={
                "frame_rate": int(rate * speed)
            }).set_frame_rate(rate)

        # 6. Xuất file kết quả
        suffix = "long" if mode == "long" else "short"
        output_dir = get_path("data", "audio")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"{episode_id}_{suffix}.mp3")
        
        # Xuất file mp3 bitrate chuẩn
        combined.export(output_path, format="mp3", bitrate="192k")
        logger.info(f"✅ TTS Hoàn tất: {output_path} (Độ dài: {len(combined)/1000/60:.1f} phút)")
        
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng trong create_tts: {e}", exc_info=True)
        return None
