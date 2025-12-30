# === scripts/generate_script.py ===
import os
import logging
import re
import json
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# Model AI (Nên dùng gpt-4o-mini hoặc gpt-4 để viết hay hơn)
MODEL = "gpt-4o-mini" 

# ============================================================
#  🛡️ BỘ LỌC AN NINH (Giữ nguyên)
# ============================================================
def check_safety_compliance(text):
    """Rà soát văn bản để tìm các từ khóa vi phạm."""
    forbidden_keywords = [
        "overthrow the government", "regime change", "topple the regime",
        "incite rebellion", "destroy the state", "illegitimate government",
        "phản động", "lật đổ", "chống phá", "xuyên tạc", "bạo loạn"
    ]
    text_lower = text.lower()
    for word in forbidden_keywords:
        if word in text_lower:
            return False, f"Chứa từ khóa cấm: {word}"
    return True, "Safe"

# ============================================================
#  📝 HÀM 1: TẠO KỊCH BẢN + METADATA CHO VIDEO DÀI
# ============================================================
def generate_long_script(data):
    """
    Input: Dữ liệu từ Google Sheet (Name, Core Theme...)
    Output: Dictionary chứa đường dẫn script và METADATA (Title, Desc, Tags)
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: return None
        client = OpenAI(api_key=api_key)

        name = data.get("Name")
        theme = data.get("Core Theme")
        
        logger.info(f"🧠 Đang viết kịch bản dài về: {name}...")

        # 1. Prompt tạo Script + Metadata (JSON Format)
        # Yêu cầu AI trả về JSON để dễ tách Tiêu đề/Mô tả
        prompt = f"""
        You are a professional documentary scriptwriter and YouTube SEO expert.
        Target Audience: History enthusiasts. Tone: Cinematic, Mysterious, Engaging.
        
        Subject: {name}
        Theme: {theme}
        
        TASK:
        1. Write a 5-minute engaging script (approx 800-1000 words). Do NOT use "Scene" or "Visual" cues, just the narration text.
        2. Create a Clickbait YouTube Title (Under 100 chars).
        3. Write a Video Description (include a hook, summary, and call to action).
        4. Generate 10 relevant Tags (comma separated).

        OUTPUT FORMAT (Strict JSON):
        {{
            "script": "The full narration text here...",
            "title": "The YouTube Title Here",
            "description": "The video description here...",
            "tags": ["tag1", "tag2", "tag3"]
        }}
        """

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"} # Bắt buộc trả về JSON
        )

        # 2. Xử lý kết quả
        content_raw = response.choices[0].message.content
        try:
            result_json = json.loads(content_raw)
        except json.JSONDecodeError:
            logger.error("❌ Lỗi: AI không trả về đúng định dạng JSON.")
            return None

        script_text = result_json.get("script", "")
        
        # Kiểm tra an toàn
        is_safe, reason = check_safety_compliance(script_text)
        if not is_safe:
            logger.error(f"❌ Kịch bản bị từ chối: {reason}")
            return None

        # 3. Lưu file Script
        script_filename = f"{data['ID']}_long.txt"
        script_path = get_path("data", "episodes", script_filename)
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_text)
            
        logger.info(f"✅ Đã lưu kịch bản: {script_path}")

        # 4. Trả về kết quả kèm METADATA
        # Đây là phần quan trọng để file upload_youtube.py đọc được
        return {
            "script_path": script_path,
            "metadata": {
                "Title": result_json.get("title", f"Amazing Facts about {name}"),
                "Summary": result_json.get("description", f"Learn about {name} in this documentary."),
                "Tags": result_json.get("tags", ["history", "documentary", name])
            },
            # Lưu lại prompt ảnh nếu cần dùng lại
            "image_prompt": f"Portrait of {name}, historical setting, cinematic lighting" 
        }

    except Exception as e:
        logger.error(f"❌ Lỗi generate_long_script: {e}", exc_info=True)
        return None

# ============================================================
#  ✂️ HÀM 2: CẮT KỊCH BẢN THÀNH 5 SHORTS
# ============================================================
def split_long_script_to_5_shorts(data, long_script_path):
    """
    Đọc kịch bản dài và nhờ AI tóm tắt/cắt thành 5 đoạn ngắn viral.
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)

        with open(long_script_path, "r", encoding="utf-8") as f:
            full_text = f.read()

        logger.info("✂️ Đang chia nhỏ kịch bản thành 5 Shorts...")

        prompt = f"""
        Source Text: "{full_text[:3000]}..." (truncated)

        TASK:
        Extract 5 distinct, viral short segments from the text above. 
        Each segment must be stand-alone, under 60 seconds (approx 120 words).
        Each segment must have a "Hook" title (under 5 words).

        OUTPUT FORMAT (Strict JSON):
        {{
            "shorts": [
                {{"title": "Hook 1", "content": "Script 1..."}},
                {{"title": "Hook 2", "content": "Script 2..."}},
                {{"title": "Hook 3", "content": "Script 3..."}},
                {{"title": "Hook 4", "content": "Script 4..."}},
                {{"title": "Hook 5", "content": "Script 5..."}}
            ]
        }}
        """

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        res_json = json.loads(response.choices[0].message.content)
        shorts_data = res_json.get("shorts", [])

        if len(shorts_data) < 1:
            logger.error("❌ Không tạo được Shorts nào.")
            return None

        output_list = []
        for i, item in enumerate(shorts_data):
            idx = i + 1
            # Lưu script short
            s_path = get_path("data", "episodes", f"{data['ID']}_short_{idx}.txt")
            with open(s_path, "w", encoding="utf-8") as f:
                f.write(item["content"])
            
            # Lưu title short
            t_path = get_path("data", "episodes", f"{data['ID']}_short_{idx}_title.txt")
            with open(t_path, "w", encoding="utf-8") as f:
                f.write(item["title"])

            output_list.append({
                "index": idx,
                "script": s_path,
                "title": t_path
            })
            
        return output_list

    except Exception as e:
        logger.error(f"❌ Lỗi split_shorts: {e}", exc_info=True)
        return None
