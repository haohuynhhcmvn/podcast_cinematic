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


#================= HÀM LONG FORM =================
def generate_long_script(data):
    episode_id = data['ID']
    title = data.get('Name', 'Unknown Title')
    core_theme = data.get('Core Theme', 'Unknown Theme')
    raw_input = data.get('Content/Input', '')
    script_path = get_path('data', 'episodes', f"{episode_id}_script_long.txt")

    # ===================== PROMPT MỚI – TỐI ƯU CHO GPT-4o MINI =====================
    sys_prompt = f"""
Bạn là Master Storyteller & Scriptwriter Cinematic (giọng Nam trầm – {TTS_VOICE_NAME}).

Nhiệm vụ của bạn:
- Viết kịch bản podcast dài phong cách phim tài liệu, giàu cảm xúc và hình ảnh.
- Ngôn ngữ trôi chảy, không dùng bullet list.
- Ưu tiên hoàn chỉnh phần core_script trước.
- Đảm bảo JSON hợp lệ tuyệt đối (không có text ngoài JSON).

📌 ĐỘ DÀI BẮT BUỘC:
- core_script phải từ 1500 đến 2000 từ.
- Nếu có nguy cơ bị cắt, ưu tiên viết core_script trước, metadata sau.

Chủ đề: "{core_theme}"
Tựa đề tập: "{title}"
"""

    user_prompt = f"""
DỮ LIỆU GỐC:
{raw_input}

Hãy trả về DUY NHẤT một JSON theo đúng cấu trúc:

{{
    "core_script": "[Kịch bản 1500–2000 từ, cinematic, mở hook mạnh, không bullet, không markdown.]",
    "youtube_title": "[SEO + Viral]",
    "youtube_description": "[Mô tả hấp dẫn + CTA]",
    "youtube_tags": "[10–15 tags, cách nhau bằng dấu phẩy]"
}}

⚠️ QUY TẮC BẮT BUỘC:
- core_script >= 1500 từ.
- Không thêm bất kỳ text nào bên ngoài JSON.
- Không dùng ký tự markdown (#, *, -, >)
"""

    

    # ===================== GỌI OPENAI + XỬ LÝ JSON AN TOÀN ============================
    raw_json = None
    data_json = None

    for attempt in range(3):  # Retry tối đa 3 lần nếu JSON lỗi
        try:
            raw_json = _call_openai(
                sys_prompt,
                user_prompt,
                max_tokens=16000,
                response_format={"type": "json_object"}
            )
            data_json = json.loads(raw_json)
            break
        except Exception as e:
            logger.warning(f"❗ JSON lỗi, thử lại ({attempt+1}/3)… {e}")
            if attempt == 2:
                logger.error("❌ GPT 4o mini trả JSON lỗi 3 lần → dừng.")
                return None
    # ==================================================================================

    core_script = data_json.get("core_script", "")

    # ===================== KIỂM TRA ĐỘ DÀI – AUTOFIX ================================
    word_count = len(core_script.split())

    if word_count < 1500:
        logger.warning(f"⚠️ Core script quá ngắn ({word_count} từ). Đang mở rộng thêm...")

        extend_prompt = f"""
Kịch bản hiện tại chỉ có {word_count} từ.
Hãy mở rộng thành phiên bản hoàn chỉnh 1800–2000 từ, văn xuôi cinematic.

Yêu cầu: trả về DUY NHẤT JSON:
{{
  "core_script": "[bản mở rộng]"
}}
"""

        try:
            extend_raw = _call_openai(
                sys_prompt,
                extend_prompt,
                max_tokens=10000,
                response_format={"type": "json_object"}
            )
            extend_json = json.loads(extend_raw)
            core_script = extend_json.get("core_script", core_script)
        except:
            logger.error("❌ Lỗi mở rộng script — dùng bản gốc.")
    # ==================================================================================

    # ===================== GHÉP INTRO + OUTRO ========================================
    full_script = (
        PODCAST_INTRO.strip()
        + "\n\n"
        + core_script.strip()
        + "\n\n"
        + PODCAST_OUTRO.strip()
    )
    # ==================================================================================

    # ===================== LƯU FILE ===================================================
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(full_script)

    data_json["core_script"] = core_script

    return {
        'script_path': script_path,
        'metadata': data_json
    }





'''# ================= HÀM LONG FORM =================
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
''' 

================= HÀM SHORTS =================
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
