import os
import logging
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"


def generate_long_script(data):
    """
    Sinh LONG SCRIPT tiếng Anh (600–700 words)
    Đảm bảo độ dài < 4096 ký tự để OpenAI TTS không lỗi.
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        prompt = f""" ... giữ nguyên prompt cũ ... """

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.85,
        )

        script_text = response.choices[0].message.content.strip()
        safe_text = script_text[:4000]  # safety limit

        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        logger.info(f"📝 Long script created: {out_path}")

        # NEW PART: trả về dict để glue_pipeline không crash
        return {
            "script_path": out_path,
            "metadata": {
                "youtube_title": f"{data.get('Name')} – The Untold Story",
                "youtube_description": f"Cinematic podcast episode about {data.get('Name')}.",
                "youtube_tags": "podcast,storytelling,legend"
            }
        }

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}")
        return None



def generate_short_script(data):
    """
    Tạo SHORT SCRIPT dạng hook 25–30s bằng tiếng Anh
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        prompt = f"""
Write a SHORT English script for a **25–30 second viral hook** for YouTube Shorts.
Topic:
NAME: {data.get("Name")}
THEME: {data.get("Core Theme")}
INPUT NOTES: {data.get("Content/Input")}

Requirements:
- 45–65 words total  
- Fast-paced, dramatic, shocking hook  
- Must feel legendary, mysterious, intense  
- No introduction, jump directly into the punchline  
- End with a strong cliffhanger  
- Pure narrative (no hashtags, no instructions)  
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.9,
        )

        script = response.choices[0].message.content.strip()

        # Save SHORT script
        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(script)

        # Generate hook title
        title_prompt = f"""
Write a 5–8 word SHORT TITLE for this topic.
Must sound viral, cinematic, mysterious.
Topic name: {data.get("Name")}
Theme: {data.get("Core Theme")}
"""
        title_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=50,
            temperature=0.9,
        )
        title = title_res.choices[0].message.content.strip()

        out_title = get_path("data", "episodes", f"{data['ID']}_short_title.txt")
        with open(out_title, "w", encoding="utf-8") as f:
            f.write(title)

        logger.info(f"✨ Short script + title created for {data['ID']}")
        return out_script, out_title

    except Exception as e:
        logger.error(f"❌ Error generating short script: {e}")
        return None
