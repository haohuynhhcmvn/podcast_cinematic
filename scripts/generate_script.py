# scripts/generate_script.py
import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv
from utils import get_path

logger = logging.getLogger(__name__)

# -----------------------
# CẤU HÌNH CHUNG
# -----------------------
CHANNEL_NAME = "Podcast Theo Dấu Chân Huyền Thoại"
TARGET_WORD_COUNT = 1800          # Long Script ~ 10–12 phút
MODEL_NAME = "gpt-4o-mini"
TTS_VOICE_NAME = "Alloy"


# -----------------------
# OPENAI HELPER
# -----------------------
def _call_openai(system, user, max_tokens=4000, response_format=None):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ Thiếu OPENAI_API_KEY.")
        return None

    try:
        client = OpenAI(api_key=api_key)

        config = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "max_tokens": max_tokens
        }

        if response_format:
            config["response_format"] = response_format

        response = client.chat.completions.create(**config)
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"❌ OpenAI Error: {e}")
        return None


# ============================================================
# 1️⃣ TẠO KỊCH BẢN DÀI – CINEMATIC (10–12 phút)
# ============================================================
def generate_long_script(data):
    episode_id = data["ID"]
    title = data.get("Name", "Không tên")
    core_theme = data.get("Core Theme", "Chưa có chủ đề")
    raw_input = data.get("Content/Input", "")

    script_path = get_path("data", "episodes", f"{episode_id}_script_long.txt")

    # GIỌNG DẪN / INTRO
    PODCAST_INTRO = f"""
Chào mừng bạn đến với {CHANNEL_NAME}. 
Hôm nay, chúng ta sẽ cùng bước vào một hành trình đầy cảm xúc để khám phá nhân vật: {title}.
"""

    # GIỌNG KẾT / OUTRO
    PODCAST_OUTRO = f"""
Cảm ơn bạn đã theo dõi hành trình này cùng {CHANNEL_NAME}. 
Đừng quên nhấn Đăng ký & Theo dõi để khám phá thêm nhiều câu chuyện ly kỳ và ý nghĩa.
Hẹn gặp lại bạn trong tập tiếp theo.
"""

    # ---------------------------
    # PROMPT GỌI AI
    # ---------------------------
    sys_prompt = f"""
Bạn là **Master Storyteller – ScriptWriter Cinematic**.
Viết kịch bản podcast GIỌNG NAM TRẦM ({TTS_VOICE_NAME}), 
cảm xúc – điện ảnh – dẫn chuyện như phim tài liệu Netflix.

YÊU CẦU:
- Độ dài: ~{TARGET_WORD_COUNT} từ (bắt buộc gần đúng)
- Chia thành 5 chương rõ ràng:
  1) HOOK mở đầu
  2) Xuất thân – khởi điểm
  3) Xung đột / bước ngoặt lớn
  4) Cao trào – sự kiện quan trọng nhất
  5) Di sản / kết luận
- Văn phong: kể chuyện – hình ảnh mạnh – đầy cảm xúc.
- Tuyệt đối KHÔNG dùng liệt kê khô khan.
"""

    user_prompt = f"""
DỮ LIỆU ĐẦU VÀO:
Tên nhân vật: {title}
Chủ đề: {core_theme}
Nội dung gốc: {raw_input}

TRẢ VỀ JSON CHUẨN GỒM:
{{
  "core_script": "... kịch bản hoàn chỉnh 1500–2200 từ ...",
  "youtube_title": "... tiêu đề SEO + cảm xúc ...",
  "youtube_description": "... mô tả thu hút ...",
  "youtube_tags": "... danh sách tags, phân tách bằng dấu phẩy ..."
}}
"""

    raw_json = _call_openai(
        sys_prompt,
        user_prompt,
        max_tokens=8000,
        response_format={"type": "json_object"}
    )

    if raw_json is None:
        logger.error("❌ Không nhận được phản hồi khi tạo long script.")
        return None

    # Parse JSON
    try:
        data_json = json.loads(raw_json)
    except:
        logger.error("❌ Lỗi JSON khi parse long script.")
        return None

    core_script = data_json.get("core_script", "").strip()
    if len(core_script) < 500:
        logger.warning("⚠️ Script quá ngắn, AI có thể trả về thiếu nội dung.")

    # Lắp intro + outro
    full_script = (
        PODCAST_INTRO.strip()
        + "\n\n"
        + core_script
        + "\n\n"
        + PODCAST_OUTRO.strip()
    )

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(full_script)

    logger.info(f"✅ Kịch bản LONG đã tạo xong: {script_path}")
    return {
        "script_path": script_path,
        "metadata": data_json
    }


# ============================================================
# 2️⃣ TẠO KỊCH BẢN SHORTS (< 30s)
# ============================================================

def generate_short_script(data):
    episode_id = data["ID"]
    short_path = get_path("data", "episodes", f"{episode_id}_script_short.txt")
    title_path = get_path("data", "episodes", f"{episode_id}_title_short.txt")

    sys_prompt = """
Bạn là chuyên gia viết video SHORTS siêu gọn – 25 đến 30 giây.
Quy tắc:
- Độ dài: chỉ 55–70 từ.
- Hook 3 giây đầu phải gây sốc, tò mò hoặc bật cảm xúc.
- Nhịp nhanh, không lan man.
- Văn phong cảm xúc – cinematic – tóm tắt dạng teaser.
- Kết thúc bằng một câu CTA duy nhất để kích thích follow hoặc xem full video.
"""

    user_prompt = f"""
Dữ liệu nguồn cho câu chuyện: {data.get('Content/Input')}
Trả về JSON bắt buộc đúng định dạng:
{{
  "hook_title": "Tiêu đề ngắn – 3 đến 8 từ – IN HOA",
  "script_body": "Nội dung 55–70 từ – kể nhanh và giàu hình ảnh",
  "cta": "Một câu duy nhất kêu gọi follow hoặc xem bản full"
}}
"""

    raw_json = _call_openai(
        sys_prompt,
        user_prompt,
        max_tokens=500,
        response_format={"type": "json_object"}
    )

    if raw_json is None:
        logger.error("❌ Lỗi khi tạo kịch bản shorts.")
        return None

    try:
        data_json = json.loads(raw_json)
    except:
        logger.error("❌ JSON shorts lỗi, không parse được.")
        return None

    # fallback
    hook = data_json.get("hook_title", f"BÍ MẬT {data['Name'].upper()}!")
    body = data_json.get("script_body", "Nội dung đang cập nhật.")
    cta = data_json.get("cta", "Hãy theo dõi để xem phần tiếp theo!")

    full_short = body + "\n\n" + cta

    with open(short_path, "w", encoding="utf-8") as f:
        f.write(full_short)

    with open(title_path, "w", encoding="utf-8") as f:
        f.write(hook)

    logger.info("🎬 Kịch bản SHORTS 25–30 giây đã hoàn tất.")
    return short_path, title_path
