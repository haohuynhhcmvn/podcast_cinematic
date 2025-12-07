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
# Tăng Max Tokens để đảm bảo script dài
MAX_TOKENS = 10000 

def parse_json_garbage(text):
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()

# ============================================================
# 1. TẠO KỊCH BẢN VIDEO DÀI (LONG FORM) - TÁCH 2 BƯỚC
# ============================================================
def generate_long_script(data):
    try:
        char_name = data.get("Name")
        char_desc = data.get("Content/Input") or f"A historical figure named {char_name}"
        
        logger.info(f"📝 Đang viết kịch bản Long-form cho: {char_name}...")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: return None
        client = OpenAI(api_key=api_key)

        # ---------------------------------------------------------
        # BƯỚC 1: TẠO SCRIPT (RAW TEXT) - ĐỂ ĐẠT ĐỘ DÀI TỐI ĐA
        # ---------------------------------------------------------
        prompt_script = f"""
        You are a master historian and storyteller.
        Topic: {char_name}. Context: {char_desc}.

        TASK: Write a comprehensive, cinematic, and immersive podcast script (Documentary style).
        LENGTH GOAL: The script MUST be long enough for an 8-10 minute video (Approx 1500-2000 words).
        
        STRUCTURE:
        1. [HOOK] (0:00-1:00): Start in the middle of a chaotic scene (battle, betrayal). Use sensory details (smell, sound, sight).
        2. [ORIGINS]: Briefly cover the rise to power.
        3. [THE RISE]: Key achievements and struggles.
        4. [THE CLIMAX]: The most dramatic moment of their life.
        5. [THE FALL/LEGACY]: The tragic end and lasting impact.

        TONE: Dramatic, engaging, objective but storytelling-driven. 
        IMPORTANT: Do NOT use markdown formatting like **bold** or # headings. Just plain text narration.
        Do NOT output JSON. Just the raw script.
        """

        logger.info("   ...Đang gọi GPT tạo Script (Text mode)...")
        resp_script = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt_script}],
            temperature=0.7
        )
        final_script = resp_script.choices[0].message.content.strip()

        # Kiểm tra độ dài
        word_count = len(final_script.split())
        logger.info(f"   ✅ Script đã tạo: {word_count} từ (~{word_count/150:.1f} phút).")

        # ---------------------------------------------------------
        # BƯỚC 2: TẠO METADATA (TITLE, DESC, TAGS) - JSON
        # ---------------------------------------------------------
        prompt_meta = f"""
        Based on the story of {char_name}:
        
        1. YOUTUBE TITLE: Generate a CLICKBAIT title. Must be a SHOCKING QUESTION or CONTROVERSIAL STATEMENT. (e.g. "Was He a Monster?", "The Bloody Truth About..."). Under 60 chars.
        2. DESCRIPTION: A SEO-optimized description (min 200 words).
        3. TAGS: 20 high-volume tags.

        OUTPUT FORMAT: JSON with keys: "title", "description", "tags".
        """

        logger.info("   ...Đang gọi GPT tạo Metadata...")
        resp_meta = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt_meta}],
            temperature=0.7
        )
        
        clean_json = parse_json_garbage(resp_meta.choices[0].message.content)
        meta_result = json.loads(clean_json)

        # ---------------------------------------------------------
        # LƯU FILE
        # ---------------------------------------------------------
        # 1. Lưu Script
        script_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(final_script)

        # 2. Lưu Metadata
        meta_path = get_path("data", "episodes", f"{data['ID']}_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "youtube_title": meta_result["title"],
                "youtube_description": meta_result["description"],
                "youtube_tags": meta_result["tags"]
            }, f, indent=4)

        return {
            "script_path": script_path,
            "metadata": {
                "youtube_title": meta_result["title"],
                "youtube_description": meta_result["description"],
                "youtube_tags": meta_result["tags"]
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
        Write a viral YouTube Shorts script (50-60s speaking time) about {char_name}.
        STRUCTURE: Hook -> Twist -> CTA.
        ALSO PROVIDE: A 3-5 word "Hook Title" for video overlay (e.g. "HERO OR VILLAIN?").
        OUTPUT FORMAT: JSON with keys: "overlay_title", "script".
        """

        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content
        result = json.loads(parse_json_garbage(content))

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
