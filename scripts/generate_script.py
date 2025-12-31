# === scripts/generate_script.py ===
import os
import logging
import json
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# ✅ Sử dụng gpt-4o-mini để tối ưu chi phí và hiệu suất
MODEL = "gpt-4o-mini"

# ============================================================
#  🛡️ BỘ LỌC AN NINH
# ============================================================
def check_safety_compliance(text):
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
#  📝 HÀM 1: TẠO KỊCH BẢN DÀI (CHUYÊN NGHIỆP & SEO)
# ============================================================
def generate_long_script(data):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: return None
        client = OpenAI(api_key=api_key)

        name = data.get("Name")
        theme = data.get("Core Theme")
        
        logger.info(f"🧠 Đang viết kịch bản quốc tế về: {name}...")

        prompt = f"""
        You are a world-class documentary scriptwriter for a high-end history channel.
        Subject: {name}
        Theme: {theme}
        
        TASK 1: Write a 10-minute documentary script (approx 1500 words).
        Tone: Cinematic, Epic, and Deeply Engaging. 
        Structure Requirements:
        1. INTRO (1 min): Start with a shocking scene or a deep philosophical question.
        2. PART 1: ORIGINS (2 mins): Early life and the environment that shaped them.
        3. PART 2: THE CLIMAX (3 mins): The most significant conflict or achievement.
        4. PART 3: THE UNTOLD (2 mins): Hidden facts or psychological depth.
        5. OUTRO (2 mins): Their lasting legacy and a final thought-provoking closing.

        TASK 2: Create SEO Metadata.
        - Title: High-CTR, Clickbait but professional.
        - Description: Must include: 
            - A powerful opening hook.
            - Timestamps: 0:00 Intro, 1:30 Origins, 3:45 The Turning Point, 6:15 The Secret Truth, 8:30 Legacy, 10:00 Final Thought.
            - SEO-rich paragraph (200 words) using keywords related to {name} and history.
        - Tags: 15 relevant SEO tags.

        OUTPUT FORMAT (Strict JSON):
        {{
            "script": "The full narration text...",
            "title": "...",
            "description": "...",
            "tags": ["...", "..."]
        }}
        """

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=16000,
            temperature=0.7
        )

        content_raw = response.choices[0].message.content
        try:
            result_json = json.loads(content_raw)
        except json.JSONDecodeError:
            logger.error("❌ Lỗi JSON. Đang thực hiện cứu dữ liệu raw...")
            return {
                "script_path": save_raw_script(data, content_raw),
                "metadata": {"Title": name, "Summary": "Historical Documentary", "Tags": ["history"]}
            }

        script_text = result_json.get("script", "")
        
        # Kiểm tra an toàn
        is_safe, reason = check_safety_compliance(script_text)
        if not is_safe:
            logger.error(f"❌ Kịch bản vi phạm chính sách: {reason}")
            return None

        script_filename = f"{data['ID']}_long.txt"
        script_path = get_path("data", "episodes", script_filename)
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_text)
            
        return {
            "script_path": script_path,
            "metadata": {
                "Title": result_json.get("title", f"The Legend of {name}"),
                "Summary": result_json.get("description", ""),
                "Tags": result_json.get("tags", ["history"])
            }
        }

    except Exception as e:
        logger.error(f"❌ Lỗi generate_long_script: {e}", exc_info=True)
        return None

def save_raw_script(data, text):
    path = get_path("data", "episodes", f"{data['ID']}_long_raw.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

# ============================================================
#  ✂️ HÀM 2: CHIA 5 SHORTS (5 GÓC ĐỘ TÂM LÝ)
# ============================================================
def split_long_script_to_5_shorts(data, long_script_path):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)

        with open(long_script_path, "r", encoding="utf-8") as f:
            full_text = f.read()

        logger.info("✂️ Đang phân tích và cắt 5 phân đoạn Shorts chiến lược...")

        prompt = f"""
        Source Text: "{full_text[:6000]}"

        TASK: Extract exactly 5 distinct, viral Short segments (each under 60s) from the text. 
        Each Short must target a different psychological angle:

        1. Short 1 (The Hook): A shocking fact or misconception.
        2. Short 2 (The Lesson): A piece of wisdom for the audience.
        3. Short 3 (The Dark Side): A tragedy or controversy.
        4. Short 4 (The Quote): A powerful, dramatic quote from the subject.
        5. Short 5 (The Legacy): How they still impact the world today.

        OUTPUT FORMAT (Strict JSON):
        {{
          "shorts": [
            {{
              "title": "CATCHY HOOK TITLE (IN UPPERCASE)",
              "content": "Dramatic, fast-paced narration."
            }},
            ... (exactly 5 items)
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

        if not shorts_data: return None

        output_list = []
        for i, item in enumerate(shorts_data):
            idx = i + 1
            s_path = get_path("data", "episodes", f"{data['ID']}_short_{idx}.txt")
            t_path = get_path("data", "episodes", f"{data['ID']}_short_{idx}_title.txt")
            
            with open(s_path, "w", encoding="utf-8") as f: f.write(item["content"])
            with open(t_path, "w", encoding="utf-8") as f: f.write(item["title"])

            output_list.append({"index": idx, "script": s_path, "title": t_path})
            
        return output_list

    except Exception as e:
        logger.error(f"❌ Lỗi split_shorts: {e}")
        return None
