# scripts/generate_script.py
import os
import logging
import json
from openai import OpenAI
from utils import get_path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

CHANNEL_NAME = "Podcast Theo Dấu Chân Huyền Thoại"
TARGET_WORD_COUNT = 1200
TTS_VOICE_NAME = "Alloy"

def _call_openai(system, user, max_tokens=1000, response_format=None):
    """Hàm gọi OpenAI chung, cố định model GPT-4o-mini."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logger.error("❌ Thiếu OPENAI_API_KEY. Không thể gọi AI.")
        return None
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
        logger.error(f"❌ OpenAI Error: {e}")
        return None

# ================= HÀM LONG FORM =================
def generate_long_script(data):
    episode_id = data['ID']
    title = data.get('Name', 'Unknown Title') 
    core_theme = data.get('Core Theme', 'Unknown Theme')
    raw_input = data.get('Content/Input', '')
    script_path = get_path('data', 'episodes', f"{episode_id}_script_long.txt")

    PODCAST_INTRO = f"""
Chào mừng bạn đến với {CHANNEL_NAME}. Đây là nơi chúng ta cùng khám phá những câu chuyện lôi cuốn, những bí ẩn chưa được giải mã, và những góc khuất lịch sử ít người biết đến. 
Hôm nay, chúng ta sẽ đi sâu vào hành trình của: {title}.
"""
    PODCAST_OUTRO = f"""
Và đó là tất cả những gì chúng ta đã khám phá trong tập {CHANNEL_NAME} ngày hôm nay. 
Nếu bạn thấy nội dung này hữu ích và truyền cảm hứng, đừng quên nhấn nút Đăng ký, chia sẻ và theo dõi để không bỏ lỡ những hành trình tri thức tiếp theo. 
Cảm ơn bạn đã lắng nghe. Hẹn gặp lại bạn trong tập sau!
"""

    sys_prompt = f"""
Bạn là **Master Storyteller + ScriptWriter Cinematic** (giọng Nam Trầm – {TTS_VOICE_NAME}).  
Tạo kịch bản Podcast dài – lôi cuốn – gây nghiện, giống phim tài liệu.  
Chủ đề: "{core_theme}", Tên tập: "{title}"
"""
    user_prompt = f"""
DỮ LIỆU GỐC: {raw_input}
Trả về JSON chuẩn với 4 trường:
{{
    "core_script": "[Mở bằng HOOK – nội dung lôi cuốn – visual mạnh]",
    "youtube_title": "[Tiêu đề TRIGGER CẢM XÚC + SEO + VIRAL]",
    "youtube_description": "[Mô tả gây tò mò + CTA]",
    "youtube_tags": "[10–15 tags, dấu phẩy]"
}}
"""
    raw_json = _call_openai(sys_prompt, user_prompt, max_tokens=16000, response_format={"type": "json_object"})
    try:
        data_json = json.loads(raw_json)
        core_script = data_json.get('core_script', "Nội dung đang cập nhật...")
        full_script = PODCAST_INTRO.strip() + "\n\n" + core_script.strip() + "\n\n" + PODCAST_OUTRO.strip()
        with open(script_path, 'w', encoding='utf-8') as f: f.write(full_script)
        return {'script_path': script_path, 'metadata': data_json}
    except Exception as e:
        logger.error(f"❌ Lỗi JSON hoặc lắp ráp kịch bản dài: {e}")
        return None

# ================= HÀM SHORTS =================
def generate_short_script(data):
    episode_id = data['ID']
    script_path = get_path('data', 'episodes', f"{episode_id}_script_short.txt")
    title_path = get_path('data', 'episodes', f"{episode_id}_title_short.txt")

    SHORTS_CTA = "Bạn đã sẵn sàng vén màn bí ẩn này? Hãy **nhấn nút Đăng ký, Theo dõi kênh** ngay!"

    sys_prompt = f"""
Bạn là **Video Shorts Script Architect** — nội dung <60s, gây giật mình 3s đầu.
Quy tắc:
1) hook_title: 3–10 từ, IN HOA, giật.
2) script_body: 150–200 từ, tốc độ cao, hành động & hình ảnh rõ.
3) Cuối nối với dynamic_cta.
"""
    user_prompt = f"""
DỮ LIỆU NGUỒN: {data['Content/Input']}
Trả về JSON tuyệt đối:
{{
    "hook_title": "10-50 ký tự – IN HOA – giật",
    "script_body": "110-140 từ – nhịp nhanh, hình ảnh rõ",
    "dynamic_cta": "1 câu chốt – buộc xem tiếp & follow"
}}
"""
    raw_json = _call_openai(sys_prompt, user_prompt, max_tokens=600, response_format={"type": "json_object"})
    hook_title_fallback = f"BÍ MẬT {data['Name'].upper()} VỪA ĐƯỢC VÉN MÀN!"
    script_body_fallback = "Nội dung đang được cập nhật..."
    try:
        data_json = json.loads(raw_json)
        hook_title = data_json.get('hook_title', hook_title_fallback).strip()
        script_body_core = data_json.get('script_body', script_body_fallback).strip()
    except:
        hook_title = hook_title_fallback
        script_body_core = script_body_fallback

    full_script_for_tts = script_body_core + "\n\n" + SHORTS_CTA

    with open(script_path, 'w', encoding='utf-8') as f: f.write(full_script_for_tts)
    with open(title_path, 'w', encoding='utf-8') as f: f.write(hook_title)

    logger.info(f"✅ Kịch bản Shorts đã hoàn tất.")
    return script_path, title_path
