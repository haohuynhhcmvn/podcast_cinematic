# scripts/generate_script.py
import os
import logging
import json 
from openai import OpenAI
from utils import get_path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# --- CÁC THAM SỐ CỐ ĐỊNH ---
CHANNEL_NAME = "Podcast Theo Dấu Chân Huyền Thoại"
TARGET_WORD_COUNT = 1200 
TTS_VOICE_NAME = "Alloy" # Giọng Nam Kể Chuyện Chuyên Nghiệp (Alloy)

def _call_openai(system, user, max_tokens=1000, response_format=None):
    """Hàm gọi API OpenAI chung, hỗ trợ JSON output và model GPT-4o-mini."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logger.error("❌ Thiếu OPENAI_API_KEY. Không thể gọi AI."); return None
    try:
        client = OpenAI(api_key=api_key)
        
        config = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens
        }
        if response_format:
            config["response_format"] = response_format

        response = client.chat.completions.create(**config)
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"❌ OpenAI Error: {e}"); return None

# ======================================================================================
# --- A. HÀM TẠO SCRIPT DÀI (LONG FORM) - TẠO METADATA HẤP DẪN ---
# ======================================================================================
def generate_long_script(data):
    """
    Tạo kịch bản dài và Metadata YouTube dưới dạng JSON. Kịch bản vào là đọc luôn.
    """
    episode_id = data['ID']
    script_path = get_path('data', 'episodes', f"{episode_id}_script_long.txt")
    
    sys_prompt = f"""
    Bạn là **Master Storyteller** với giọng văn Nam Trầm ({TTS_VOICE_NAME}), chuyên tạo nội dung cinematic.
    Nhiệm vụ của bạn là tạo **Kịch bản** và **Metadata YouTube** phải thật **LÔI CUỐN và TỐI ƯU SEO** để tăng Click-Through Rate (CTR).

    QUY TẮC TẠO KỊCH BẢN (core_script):
    1.  **BẮT ĐẦU NGAY LẬP TỨC:** Kịch bản phải bắt đầu bằng **HOOK** mạnh mẽ nhất (không có lời chào/giới thiệu kênh).
    2.  **Thời lượng:** Khoảng 800 - {TARGET_WORD_COUNT} từ.
    3.  **Định dạng:** Chỉ văn bản cần được đọc.

    QUY TẮC TẠO METADATA YOUTUBE (Tập trung vào SEO và Hấp dẫn):
    1.  **youtube_title (Tối đa 100 ký tự):** Phải chứa **từ khóa chính** ở đầu, gây tò mò, sử dụng số hoặc dấu ngoặc đơn/kép để tăng CTR.
    2.  **youtube_description:** Bắt đầu bằng **HOOK văn bản** (2-3 câu gây sốc), sau đó là tóm tắt chi tiết. Kết thúc bằng Kêu gọi hành động (CTA) và các hashtag liên quan.
    3.  **youtube_tags:** Danh sách 10-15 từ khóa liên quan, bao gồm các từ khóa dài (long-tail keywords) và từ khóa liên quan đến kênh (podcast, cinematic, [Core Theme]).

    CHỦ ĐỀ CỐT LÕI CỦA TẬP NÀY: "{data['Core Theme']}"
    TÊN NHÂN VẬT/TIÊU ĐỀ: "{data['Name']}"
    """
    
    user_prompt = f"""
    DỮ LIỆU THÔ ĐẦU VÀO TỪ GOOGLE SHEET: {data['Content/Input']}
    Hãy trả về dưới dạng JSON với 4 trường sau:
    {{
        "core_script": "[Nội dung kịch bản chính, BẮT ĐẦU BẰNG HOOK CINEMATIC]",
        "youtube_title": "[Tiêu đề video, TỐI ƯU SEO VÀ CTR]",
        "youtube_description": "[Mô tả video, BẮT ĐẦU BẰNG HOOK MẠNH MẼ]",
        "youtube_tags": "[Tags video, ngăn cách bằng dấu phẩy]"
    }}
    """
    
    raw_json = _call_openai(sys_prompt, user_prompt, max_tokens=16000, response_format={"type": "json_object"})

    try:
        data_json = json.loads(raw_json)
        core_script = data_json.get('core_script', "Nội dung đang cập nhật...")
        
        # KỊCH BẢN CUỐI CÙNG: Chỉ là phần core script (Vào là đọc luôn)
        full_script = core_script 
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(full_script)
            
        return {
            'script_path': script_path,
            'metadata': data_json
        }

    except Exception as e:
        logger.error(f"❌ Lỗi xử lý JSON hoặc lắp ráp kịch bản dài: {e}")
        return None

# ======================================================================================
# --- B. HÀM TẠO SCRIPT NGẮN (SHORTS) - TẠO HOOK GIẬT GÂN ---
# ======================================================================================
def generate_short_script(data):
    """
    Tạo kịch bản Shorts cô đọng, tập trung vào Hook giật gân và CTA.
    Trả về 2 giá trị (script_path, title_path).
    """
    episode_id = data['ID']
    script_path = get_path('data', 'episodes', f"{episode_id}_script_short.txt")
    title_path = get_path('data', 'episodes', f"{episode_id}_title_short.txt")
    
    # Kêu gọi hành động cố định cho Shorts
    SHORTS_CTA = "Bạn đã sẵn sàng vén màn bí ẩn này? Hãy **nhấn nút Đăng ký, Theo dõi kênh** ngay để luôn nhận được thông tin mới!"

    sys_prompt = f"""
    Bạn là **Chuyên gia tạo nội dung Shorts** (video dưới 60 giây). Giọng văn phải **cực kỳ giật gân, cô đọng và mạnh mẽ**.
    
    YÊU CẦU BẮT BUỘC:
    1.  **Tiêu đề (HOOK):** Phải là một câu tuyên bố hoặc câu hỏi **gây SỐC** cực độ (tối đa 10 từ). Phải viết IN HOA. (Đây là Tiêu đề TextClip trên video).
    2.  **Kịch bản:** Kịch bản chính chỉ dài khoảng **70 - 100 từ** để có chỗ cho nhạc và CTA.
    3.  **Cấu trúc:** [HOOK GIẬT GÂN] | [Nội dung HOOK + CỐT LÕI].
        
    CHỦ ĐỀ CỐT LÕI CỦA TẬP NÀY: "{data['Core Theme']}"
    """
    
    user_prompt = f"DỮ LIỆU THÔ ĐẦU VÀO: {data['Content/Input']}. Hãy tạo [Tiêu đề] và [Kịch bản] cho Shorts theo định dạng bắt buộc."
    
    raw_content = _call_openai(sys_prompt, user_prompt, max_tokens=300)

    # 4. Tách Tiêu đề và Kịch bản
    if raw_content and "|" in raw_content:
        parts = raw_content.split("|", 1)
        hook_title = parts[0].strip()
        script_body_core = parts[1].strip()
    else:
        logger.warning("⚠️ AI không trả lời đúng định dạng Shorts. Dùng Fallback.")
        hook_title = f"BÍ MẬT {data['Name'].upper()} VỪA ĐƯỢC VÉN MÀN!"
        script_body_core = raw_content if raw_content else "Nội dung đang cập nhật..."

    # 5. NỐI KỊCH BẢN VỚI CTA CỐ ĐỊNH
    full_script_for_tts = script_body_core + "\n\n" + SHORTS_CTA

    # 6. LƯU FILE
    with open(script_path, 'w', encoding='utf-8') as f: f.write(full_script_for_tts)
    with open(title_path, 'w', encoding='utf-8') as f: f.write(hook_title)
    
    logger.info(f"✅ Kịch bản Shorts ({len(full_script_for_tts.split())} từ) đã hoàn tất.")
    
    return script_path, title_path
