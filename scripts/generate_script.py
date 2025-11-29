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
TARGET_WORD_COUNT = 1200 # Khoảng 800 - 1200 từ cho video dài
TTS_VOICE_NAME = "Alloy" 

def _call_openai(system, user, max_tokens=1000, response_format=None):
    """Hàm gọi API OpenAI chung, cố định model GPT-4o-mini."""
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
# --- A. HÀM TẠO SCRIPT DÀI (LONG FORM) ---
# ======================================================================================
def generate_long_script(data): 
    """
    Tạo kịch bản dài (Bao gồm Intro/Outro text cố định) và Metadata YouTube.
    """
    episode_id = data['ID']
    title = data.get('Name', 'Unknown Title') 
    core_theme = data.get('Core Theme', 'Unknown Theme')
    raw_input = data.get('Content/Input', '')
    
    script_path = get_path('data', 'episodes', f"{episode_id}_script_long.txt")
    
    # --- 1. ĐỊNH NGHĨA CÂU CHÀO VÀ CÂU KẾT CỐ ĐỊNH ---
    PODCAST_INTRO = f"""
Chào mừng bạn đến với {CHANNEL_NAME}. Đây là nơi chúng ta cùng khám phá những câu chuyện lôi cuốn, những bí ẩn chưa được giải mã, và những góc khuất lịch sử ít người biết đến. 
Hôm nay, chúng ta sẽ đi sâu vào hành trình của: {title}.
"""
    
    PODCAST_OUTRO = f"""
Và đó là tất cả những gì chúng ta đã khám phá trong tập {CHANNEL_NAME} ngày hôm nay. 
Nếu bạn thấy nội dung này hữu ích và truyền cảm hứng, đừng quên nhấn nút Đăng ký, chia sẻ và theo dõi để không bỏ lỡ những hành trình tri thức tiếp theo. 
Cảm ơn bạn đã lắng nghe. Hẹn gặp lại bạn trong tập sau!
"""
    
    # --- LOGIC PROMPT ---
    sys_prompt = f"""
    Bạn là **Master Storyteller** với giọng văn Nam Trầm ({TTS_VOICE_NAME}), chuyên tạo nội dung cinematic.
    Nhiệm vụ của bạn là tạo Kịch bản và Metadata YouTube phải thật LÔI CUỐN, GÂY TÒ MÒ và TỐI ƯU SEO.

    QUY TẮC TẠO KỊCH BẢN (core_script):
    1. Giọng văn phải uyển chuyển, giàu hình ảnh.
    2. Kịch bản phải bắt đầu bằng HOOK mạnh mẽ.
    3. Thời lượng: Khoảng 800 - {TARGET_WORD_COUNT} từ.
    4. **Tốc độ đọc:** Sử dụng dấu chấm, dấu phẩy, và dấu gạch ngang (...) để tạo nhịp điệu đọc (pacing) **chậm rãi, kịch tính, và truyền cảm**.
    5. Định dạng: Chỉ văn bản cần được đọc. KHÔNG BAO GỒM LỜI CHÀO VÀ KẾT.

    QUY TẮC TẠO METADATA YOUTUBE (Tập trung vào SEO và Hấp dẫn):
    1. **youtube_title (Tối đa 100 ký tự):** Phải chứa từ khóa chính, gây tò mò, sử dụng TỪ KHÓA IN HOA.
    2. **youtube_description:** Bắt đầu bằng HOOK VĂN BẢN gây SỐC. Mô tả chi tiết, bao gồm CTA và #Hashtag.
    3. **youtube_tags:** Danh sách 10-15 từ khóa liên quan, bao gồm long-tail keywords và từ khóa viral.

    CHỦ ĐỀ CỐT LÕI: "{core_theme}"
    TÊN TẬP: "{title}"
    """
    
    user_prompt = f"""
    DỮ LIỆU THÔ ĐẦU VÀO TỪ GOOGLE SHEET: {raw_input}
    Hãy trả về dưới dạng JSON với 4 trường sau:
    {{
        "core_script": "[Nội dung kịch bản chính, BẮT ĐẦU BẰNG HOOK CINEMATIC]",
        "youtube_title": "[Tiêu đề video, LÔI CUỐN/VIRAL]",
        "youtube_description": "[Mô tả video, GÂY TÒ MÒ VÀ MỜI GỌI]",
        "youtube_tags": "[Tags video, ngăn cách bằng dấu phẩy, 10-15 từ khóa]"
    }}
    """
    
    raw_json = _call_openai(sys_prompt, user_prompt, max_tokens=16000, response_format={"type": "json_object"})

    try:
        data_json = json.loads(raw_json)
        core_script = data_json.get('core_script', "Nội dung đang cập nhật...")
        
        # GHÉP INTRO/OUTRO VÀO CORE SCRIPT
        full_script = PODCAST_INTRO.strip() + "\n\n" + core_script.strip() + "\n\n" + PODCAST_OUTRO.strip()
        
        with open(script_path, 'w', encoding='utf-8') as f: f.write(full_script)
            
        return {
            'script_path': script_path,
            'metadata': data_json 
        }

    except Exception as e:
        logger.error(f"❌ Lỗi xử lý JSON hoặc lắp ráp kịch bản dài: {e}")
        return None


# ======================================================================================
# --- B. HÀM TẠO SCRIPT NGẮN (SHORTS) - FIX HOOK GÂY SỐC ---
# ======================================================================================
def generate_short_script(data):
    """
    Tạo kịch bản Shorts cô đọng, sử dụng JSON output để đảm bảo định dạng Title và Script.
    """
    episode_id = data['ID']
    script_path = get_path('data', 'episodes', f"{episode_id}_script_short.txt")
    title_path = get_path('data', 'episodes', f"{episode_id}_title_short.txt")
    
    # Kêu gọi hành động cố định cho Shorts
    SHORTS_CTA = "Bạn đã sẵn sàng vén màn bí ẩn này? Hãy **nhấn nút Đăng ký, Theo dõi kênh** ngay để luôn nhận được thông tin mới!"

    # 1. CẤU HÌNH PROMPT VÀ YÊU CẦU JSON OUTPUT
    sys_prompt = f"""
    Bạn là **Chuyên gia tạo nội dung Shorts** (video tối đa 60 giây). Giọng văn phải **cực kỳ giật gân, cô đọng và mạnh mẽ**.
    
    YÊU CẦU BẮT BUỘC:
    1.  **hook_title (VIRAL):** Tiêu đề TextClip trên video. Phải là câu tuyên bố gây SỐC (tối đa 10 từ, viết IN HOA).
    2.  **script_body (CÔ ĐỌNG, DÀI HƠN):** Kịch bản chính **phải có độ dài từ 150 đến 200 từ** để đạt thời lượng 60 giây.
    3.  **Tốc độ đọc:** Sử dụng dấu phẩy và dấu chấm một cách dồn dập, ít khoảng trắng giữa các câu để tạo nhịp đọc **NHANH, GẤP GÁP, KỊCH TÍNH**.
    4.  **QUAN TRỌNG:** Kịch bản phải **BẮT ĐẦU BẰNG MỘT TUYÊN BỐ GÂY SỐC** về nghịch lý/xung đột lớn nhất của nhân vật/sự kiện. Tên nhân vật chỉ được nhắc đến ở **giữa hoặc cuối câu đầu tiên** để giữ sự tò mò. (Ví dụ: "NGƯỜI NÀY ĐÃ TẠO RA DÒNG ĐIỆN XOAY CHIỀU, NHƯNG LẠI CHẾT TRONG CÔ ĐƠN: **Nikola Tesla**.")
    """
    
    user_prompt = f"""
    DỮ LIỆU THÔ ĐẦU VÀO: {data['Content/Input']}.
    Hãy tạo Kịch bản và Tiêu đề Shorts, trả về dưới dạng JSON với 2 trường sau (BẮT BUỘC ĐÚNG FORMAT JSON):
    {{
        "hook_title": "[Tiêu đề giật gân, IN HOA, LÔI CUỐN]",
        "script_body": "[Nội dung kịch bản HOOK GÂY SỐC + CỐT LÕI]"
    }}
    """
    
    # 2. GỌI AI VỚI JSON MODE
    raw_json = _call_openai(sys_prompt, user_prompt, max_tokens=600, response_format={"type": "json_object"}) 

    # 3. XỬ LÝ LỖI và TÁCH DỮ LIỆU
    hook_title_fallback = f"BÍ MẬT {data['Name'].upper()} VỪA ĐƯỢC VÉN MÀN!"
    script_body_fallback = "Nội dung đang được cập nhật..."
    
    try:
        data_json = json.loads(raw_json)
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
    
    logger.info(f"✅ Kịch bản Shorts đã hoàn tất.")
    
    return script_path, title_path
