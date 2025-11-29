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
TTS_VOICE_NAME = "Alloy" # Giọng Nam Kể Chuyện Chuyên Nghiệp

def _call_openai(system, user, max_tokens=1000, response_format=None):
    """Hàm gọi API OpenAI chung, cố định model GPT-4o-mini và hỗ trợ JSON output."""
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
        # response_format={"type": "json_object"} là cách cứng nhắc nhất để yêu cầu JSON
        if response_format:
            config["response_format"] = response_format

        response = client.chat.completions.create(**config)
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"❌ OpenAI Error: {e}"); return None

# ======================================================================================
# --- A. HÀM TẠO SCRIPT DÀI (LONG FORM) ---
# ======================================================================================
def generate_long_script(data):
    """
    Tạo kịch bản dài và Metadata YouTube dưới dạng JSON (4 trường).
    """
    episode_id = data['ID']
    script_path = get_path('data', 'episodes', f"{episode_id}_script_long.txt")
    
    sys_prompt = f"""
    Bạn là **Master Storyteller** với giọng văn Nam Trầm ({TTS_VOICE_NAME}), chuyên tạo nội dung cinematic.
    Nhiệm vụ của bạn là tạo Kịch bản và Metadata YouTube phải thật LÔI CUỐN và TỐI ƯU SEO.

    QUY TẮC TẠO KỊCH BẢN (core_script):
    1. BẮT ĐẦU NGAY LẬP TỨC: Kịch bản phải bắt đầu bằng HOOK mạnh mẽ.
    2. Thời lượng: Khoảng 800 - {TARGET_WORD_COUNT} từ.
    ... [Các quy tắc khác] ...
    """
    
    user_prompt = f"""
    DỮ LIỆU THÔ ĐẦU VÀO TỪ GOOGLE SHEET: {data['Content/Input']}
    Hãy trả về dưới dạng JSON với 4 trường sau (BẮT BUỘC ĐÚNG FORMAT JSON):
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
        
        full_script = core_script 
        
        with open(script_path, 'w', encoding='utf-8') as f: f.write(full_script)
            
        return {
            'script_path': script_path,
            'metadata': data_json
        }

    except Exception as e:
        logger.error(f"❌ Lỗi xử lý JSON hoặc lắp ráp kịch bản dài: {e}")
        return None

# ======================================================================================
# --- B. HÀM TẠO SCRIPT NGẮN (SHORTS) - ĐÃ FIX LỖI ĐỊNH DẠNG ---
# ======================================================================================
def generate_short_script(data):
    """
    Tạo kịch bản Shorts cô đọng, sử dụng JSON output để đảm bảo định dạng Title và Script.
    (Fix lỗi ValueError: too many values to unpack)
    """
    episode_id = data['ID']
    script_path = get_path('data', 'episodes', f"{episode_id}_script_short.txt")
    title_path = get_path('data', 'episodes', f"{episode_id}_title_short.txt")
    
    # Kêu gọi hành động cố định cho Shorts
    SHORTS_CTA = "Bạn đã sẵn sàng vén màn bí ẩn này? Hãy **nhấn nút Đăng ký, Theo dõi kênh** ngay để luôn nhận được thông tin mới!"

    # 1. CẤU HÌNH PROMPT VÀ YÊU CẦU JSON OUTPUT
    sys_prompt = f"""
    Bạn là **Chuyên gia tạo nội dung Shorts** (video dưới 60 giây). Giọng văn phải **cực kỳ giật gân, cô đọng và mạnh mẽ**.
    
    YÊU CẦU BẮT BUỘC:
    1.  **hook_title:** Tiêu đề TextClip trên video. Phải là câu tuyên bố gây SỐC (tối đa 10 từ, viết IN HOA).
    2.  **script_body:** Kịch bản chính chỉ dài khoảng **70 - 100 từ** (không bao gồm CTA).
    """
    
    user_prompt = f"""
    DỮ LIỆU THÔ ĐẦU VÀO: {data['Content/Input']}.
    Hãy tạo Kịch bản và Tiêu đề Shorts, trả về dưới dạng JSON với 2 trường sau (BẮT BUỘC ĐÚNG FORMAT JSON):
    {{
        "hook_title": "[Tiêu đề giật gân, IN HOA]",
        "script_body": "[Nội dung kịch bản HOOK + CỐT LÕI]"
    }}
    """
    
    # 2. GỌI AI VỚI JSON MODE
    raw_json = _call_openai(sys_prompt, user_prompt, max_tokens=300, response_format={"type": "json_object"})

    # 3. XỬ LÝ LỖI và TÁCH DỮ LIỆU
    # Giá trị mặc định an toàn nếu JSON bị lỗi parsing
    hook_title_fallback = f"BÍ MẬT {data['Name'].upper()} VỪA ĐƯỢC VÉN MÀN!"
    script_body_fallback = "Nội dung đang được cập nhật..."
    
    try:
        data_json = json.loads(raw_json)
        # Sử dụng .get() để lấy giá trị (dùng giá trị mặc định nếu key không tồn tại)
        hook_title = data_json.get('hook_title', hook_title_fallback).strip()
        script_body_core = data_json.get('script_body', script_body_fallback).strip()
    except Exception as e:
        logger.error(f"❌ Lỗi parsing JSON từ Shorts API: {e}. Dùng nội dung Fallback.")
        hook_title = hook_title_fallback
        script_body_core = script_body_fallback

    # 4. NỐI KỊCH BẢN VỚI CTA CỐ ĐỊNH
    full_script_for_tts = script_body_core + "\n\n" + SHORTS_CTA

    # 5. LƯU FILE
    with open(script_path, 'w', encoding='utf-8') as f: f.write(full_script_for_tts)
    with open(title_path, 'w', encoding='utf-8') as f: f.write(hook_title)
    
    logger.info(f"✅ Kịch bản Shorts ({len(full_script_for_tts.split())} từ) đã hoàn tất.")
    
    # TRẢ VỀ CHÍNH XÁC 2 GIÁ TRỊ (script_path, title_path)
    return script_path, title_path
