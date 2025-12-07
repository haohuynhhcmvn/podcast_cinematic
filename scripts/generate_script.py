# === scripts/generate_script.py ===
import os
import json
import logging
import re
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# --- CẤU HÌNH ---
GPT_MODEL = "gpt-4o-mini"  # Model rẻ và nhanh, chất lượng đủ tốt
MAX_TOKENS = 4000

def parse_json_garbage(text):
    """Hàm làm sạch JSON trả về từ GPT (đôi khi nó thêm ```json ... ```)"""
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

        # --- [CẬP NHẬT QUAN TRỌNG] PROMPT GÂY SỐC ---
        prompt = f"""
        You are a master storyteller and YouTube strategist for a history channel.
        Topic: {char_name}. Context: {char_desc}.

        TASK: Create a complete package for a viral history documentary (8-10 minutes).
        
        STRUCTURE OF THE SCRIPT:
        1. HOOK (0:00-0:45): Start in medias res (middle of action). Use sensory details (smell of blood, sound of steel). Grab attention immediately.
        2. BACKGROUND: Briefly cover childhood/origins but move fast.
        3. RISING ACTION: The major struggles, battles, or political maneuvers.
        4. CLIMAX: The turning point or most famous moment.
        5. FALL/LEGACY: The tragic end or lasting impact.
        
        CRITICAL INSTRUCTIONS FOR METADATA (SEO & CTR):
        1. YOUTUBE TITLE: MUST be a "Clickbait" style. Use a SHOCKING QUESTION or a CONTROVERSIAL STATEMENT. 
           - Bad: "The History of {char_name}"
           - Good: "Was {char_name} Actually a Psychopath?", "The Horrifying Secret {char_name} Hid for Years", "Why History Lied About {char_name}".
           - Keep it under 60 characters if possible.
           - Use UPPERCASE for emphasis words.
        2. DESCRIPTION: Detailed summary (min 1500 chars) optimized for SEO keywords.
        3. TAGS: 15-20 high-traffic tags.

        OUTPUT FORMAT: Return ONLY a valid JSON object with keys: "title", "description", "tags", "script".
        """

        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        content = response.choices[0].message.content
        clean_json = parse_json_garbage(content)
        result = json.loads(clean_json)

        # Lưu file
        # 1. Script Text
        script_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(result["script"])

        # 2. Metadata (Title, Desc, Tags)
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
