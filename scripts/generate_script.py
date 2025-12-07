# === scripts/generate_script.py ===
import os
import json
import logging
import re
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# --- CẤU HÌNH ---
GPT_MODEL = "gpt-4o-mini"
MAX_TOKENS = 4000

def parse_json_garbage(text):
    """Hàm làm sạch JSON trả về từ GPT"""
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()

# ============================================================
# 1. TẠO KỊCH BẢN VIDEO DÀI (LONG FORM)
# ============================================================
def generate_long_script(data):
    """
    Tạo kịch bản dài, tiêu đề YouTube (SỐC) và mô tả chuẩn SEO.
    """
    try:
        char_name = data.get("Name")
        char_desc = data.get("Content/Input") or f"A historical figure named {char_name}"
        
        logger.info(f"📝 Đang viết kịch bản Long-form cho: {char_name}...")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Thiếu OPENAI_API_KEY")
            return None
        
        client = OpenAI(api_key=api_key)

        # --- PROMPT GÂY SỐC (CÓ FIX LỖI DICT) ---
        prompt = f"""
        You are a master storyteller and YouTube strategist for a history channel.
        Topic: {char_name}. Context: {char_desc}.

        TASK: Create a complete package for a viral history documentary (8-10 minutes).
        
        STRUCTURE OF THE SCRIPT:
        1. HOOK (0:00-0:45): Start in medias res (middle of action). Use sensory details.
        2. BACKGROUND: Briefly cover childhood/origins.
        3. RISING ACTION: The major struggles/battles.
        4. CLIMAX: The turning point.
        5. FALL/LEGACY: The tragic end or impact.
        
        CRITICAL INSTRUCTIONS FOR METADATA:
        1. YOUTUBE TITLE: Clickbait style, SHOCKING QUESTION or CONTROVERSIAL STATEMENT. Under 60 chars.
        2. DESCRIPTION: Detailed summary (min 1500 chars).
        3. TAGS: 15-20 high-traffic tags.

        OUTPUT FORMAT: Return ONLY a valid JSON object with keys: "title", "description", "tags", "script".
        IMPORTANT: The value of "script" must be a SINGLE LONG STRING containing the narration (not a nested object).
        """

        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        content = response.choices[0].message.content
        clean_json = parse_json_garbage(content)
        result = json.loads(clean_json)

        # --- [FIX LỖI] XỬ LÝ NẾU SCRIPT LÀ DICT/LIST ---
        raw_script = result.get("script", "")
        final_script_str = ""

        if isinstance(raw_script, str):
            final_script_str = raw_script
        elif isinstance(raw_script, dict):
            # Nếu GPT trả về dict, gộp lại thành string
            lines = []
            for section, text in raw_script.items():
                lines.append(f"[{section.upper()}]\n{text}")
            final_script_str = "\n\n".join(lines)
        elif isinstance(raw_script, list):
            # Nếu GPT trả về list
            final_script_str = "\n\n".join([str(x) for x in raw_script])
        else:
            final_script_str = str(raw_script)
        # -----------------------------------------------

        # Lưu file
        # 1. Script Text (Đã xử lý an toàn)
        script_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(final_script_str)

        # 2. Metadata
        meta_path = get_path("data", "episodes", f"{data['ID']}_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "youtube_title": result["title"],
                "youtube_description": result["description"],
                "youtube_tags": result["tags"]
            }, f, indent=4)

        logger.info(f"✅ Long script & Meta created: {result['title']}")
        
        return {
            "script_path": script_path,
            "metadata": {
                "youtube_title": result["title"],
                "youtube_description": result["description"],
                "youtube_tags": result["tags"]
            }
        }

    except Exception as e:
        logger.error(f"❌ Lỗi tạo Long Script: {e}", exc_info=True)
        return None

# ============================================================
# 2. TẠO KỊCH BẢN SHORTS (GIỮ NGUYÊN)
# ============================================================
def generate_short_script(data):
    try:
        char_name = data.get("Name")
        logger.info(f"✨ Đang viết kịch bản Shorts cho: {char_name}...")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: return None, None
        client = OpenAI(api_key=api_key)

        prompt = f"""
        Write a viral YouTube Shorts script (approx 50-60 seconds speaking time) about {char_name}.
        
        STRUCTURE:
        - 0-5s: The Hook (A shocking fact or question).
        - 5-45s: The Twist/Story (Fast-paced, high energy).
        - 45-60s: Conclusion + Call to Action (Subscribe for more legends).
        
        ALSO PROVIDE: A 3-5 word "Hook Title" for the video overlay (e.g., "TRAITOR OR HERO?", "BLOODY TRUTH").
        
        OUTPUT FORMAT: JSON with keys: "overlay_title", "script".
        """

        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content
        result = json.loads(parse_json_garbage(content))

        # Lưu file
        script_path = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        title_path = get_path("data", "episodes", f"{data['ID']}_short_title.txt")
        
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(result["script"])
        with open(title_path, "w", encoding="utf-8") as f:
            f.write(result["overlay_title"])
            
        logger.info(f"✅ Short script created for {char_name}")
        return script_path, title_path

    except Exception as e:
        logger.error(f"❌ Lỗi tạo Short Script: {e}")
        return None, None
