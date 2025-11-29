# scripts/generate_script.py
import os
import logging
from openai import OpenAI
from utils import get_path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def _call_openai(system, user, max_tokens=1000):
    """Hàm gọi API OpenAI chung, cố định model GPT-4o-mini."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logger.error("❌ Thiếu OPENAI_API_KEY. Không thể gọi AI.")
        return None
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"❌ OpenAI Error: {e}")
        return None

def generate_long_script(data):
    """Tạo kịch bản chi tiết (dài nhất có thể) cho Video Dài."""
    episode_id = data['ID']
    path = get_path('data', 'episodes', f"{episode_id}_script_long.txt")
    
    sys_prompt = "Bạn là người kể chuyện lịch sử/nhân vật thâm thúy, giọng văn trầm ấm."
    user_prompt = f"Viết kịch bản podcast ĐẦY ĐỦ (1500+ từ) về: {data['Name']}. \nInput: {data['Content/Input']}. \nYêu cầu: Chia 3 phần, phân tích sâu, không dùng chỉ dẫn sân khấu."
    
    # max_tokens lớn để AI viết dài nhất có thể
    content = _call_openai(sys_prompt, user_prompt, max_tokens=10000)
    
    # Fallback an toàn
    if not content:
        content = "Đây là nội dung kịch bản dài đang được xử lý..."
        
    with open(path, 'w', encoding='utf-8') as f: f.write(content)
    return path

def generate_short_script(data):
    """
    Tạo kịch bản Shorts. Trả về 2 giá trị (script_path, title_path).
    SỬA LỖI: Luôn đảm bảo trả về 2 giá trị để tránh ValueError.
    """
    episode_id = data['ID']
    script_path = get_path('data', 'episodes', f"{episode_id}_script_short.txt")
    title_path = get_path('data', 'episodes', f"{episode_id}_title_short.txt")
    
    sys_prompt = "Bạn là chuyên gia TikTok/Shorts. Nhiệm vụ: Viết 1 Tiêu đề giật gân và Kịch bản nội dung."
    user_prompt = f"""
    Chủ đề: {data['Name']}. Input: {data['Content/Input']}.
    YÊU CẦU OUTPUT BẮT BUỘC: [Tiêu đề cực sốc, viết IN HOA] | [Nội dung kịch bản để đọc, dưới 130 từ]
    """
    
    raw_content = _call_openai(sys_prompt, user_prompt, max_tokens=300)
    
    # --- XỬ LÝ LỖI và TÁCH DỮ LIỆU ---
    hook_title = f"BÍ MẬT VỀ {data['Name'].upper()}" # Tiêu đề mặc định
    script_body = "Nội dung đang được cập nhật..." # Script mặc định
    
    if raw_content and "|" in raw_content:
        # Nếu AI trả về đúng format, ta tách ra
        parts = raw_content.split("|", 1)
        hook_title = parts[0].strip()
        script_body = parts[1].strip()
    elif raw_content:
        # Nếu AI trả về nội dung nhưng quên dấu "|", ta dùng toàn bộ làm body
        script_body = raw_content

    # Lưu 2 file riêng (Dù AI có lỗi vẫn phải tạo 2 file để các bước sau không bị lỗi)
    with open(script_path, 'w', encoding='utf-8') as f: f.write(script_body)
    with open(title_path, 'w', encoding='utf-8') as f: f.write(hook_title)
    
    # QUAN TRỌNG: LUÔN TRẢ VỀ TUPLE 2 GIÁ TRỊ (Fix lỗi ValueError)
    return script_path, title_path
