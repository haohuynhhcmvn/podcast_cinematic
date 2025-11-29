import os
import logging
from openai import OpenAI
from utils import get_path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def _call_openai(system, user, max_tokens=1000):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return None
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini", # Tiết kiệm chi phí, hiệu năng tốt
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content
    except Exception as e:
        logger.error(f"❌ OpenAI Error: {e}")
        return None

def generate_long_script(data):
    """Kịch bản chi tiết cho Video dài."""
    episode_id = data['ID']
    path = get_path('data', 'episodes', f"{episode_id}_script_long.txt")
    
    sys_prompt = "Bạn là người kể chuyện lịch sử/nhân vật thâm thúy, giọng văn trầm ấm."
    user_prompt = f"Viết kịch bản podcast ĐẦY ĐỦ (1500+ từ) về: {data['Name']}. \nInput: {data['Content/Input']}. \nYêu cầu: Chia 3 phần, phân tích sâu, không dùng chỉ dẫn sân khấu."
    
    content = _call_openai(sys_prompt, user_prompt, max_tokens=10000) or "Nội dung giả lập..."
    with open(path, 'w', encoding='utf-8') as f: f.write(content)
    return path

def generate_short_script(data):
    """Kịch bản Hook nhanh cho Shorts."""
    episode_id = data['ID']
    path = get_path('data', 'episodes', f"{episode_id}_script_short.txt")
    
    sys_prompt = "Bạn là chuyên gia TikTok/Shorts. Viết ngắn gọn, viral."
    user_prompt = f"Viết kịch bản dưới 130 từ về: {data['Name']}. \nInput: {data['Content/Input']}. \nYêu cầu: Bắt đầu bằng câu hỏi sốc, kết thúc kêu gọi Subscribe."
    
    content = _call_openai(sys_prompt, user_prompt, max_tokens=300) or "Shorts giả lập..."
    with open(path, 'w', encoding='utf-8') as f: f.write(content)
    return path
