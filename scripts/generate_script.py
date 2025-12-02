# scripts/generate_script.py
import os
import logging
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"


# ============================================================
#  LONG SCRIPT GENERATOR (ENGLISH • 600–700 words)
# ============================================================
def generate_long_script(data):
    """
    Generate an English long-form script (600–700 words)
    based on Vietnamese input → translated + rewritten cinematically.
    Ensures <4000 characters for TTS compatibility.
    Returns dict: {script_path, metadata}
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # --- Prompt cho nội dung dài (ENGLISH) ---
        prompt = f"""
You are a storytelling expert.

Using the information below (written in Vietnamese), create a **cinematic English long-form podcast script**.

DATA:
- Name: {data.get("Name")}
- Core Theme: {data.get("Core Theme")}
- Story Input (Vietnamese notes): {data.get("Content/Input")}

REQUIREMENTS:
- Length: **600–700 words**
- Tone: cinematic, mysterious, legendary, emotional
- No introduction such as "In this podcast we will...". Start directly with atmosphere.
- Must read like a documentary + emotional narration
- Smooth, natural English (no translation artifacts)
- Do NOT exceed **4000 characters**

Write the full script now.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.85,
        )

        script_text = response.choices[0].message.content.strip()

        # Safety trimming
        safe_text = script_text[:4000]

        # Output path
        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        logger.info(f"📝 Long EN script created: {out_path}")

        # Metadata for YouTube
        metadata = {
            "youtube_title": f"{data.get('Name')} – The Untold Story",
            "youtube_description": f"A cinematic deep-dive into the mysterious story of {data.get('Name')}.",
            "youtube_tags": ["podcast", "cinematic", "legend", "storytelling"]
        }

        return {
            "script_path": out_path,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}")
        return None



# ============================================================
#  SHORT SCRIPT GENERATOR (ENGLISH • 25–30 SECONDS)
# ============================================================
def generate_short_script(data):
    """
    Generate a SHORT English script for YouTube Shorts (25–30s)
    - 45–65 words
    - Viral, cinematic, punchy hook
    - Uses Vietnamese input but outputs English
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # Prompt for SHORT script
        prompt = f"""
Write a **45–65 word English script** for a **25–30 second viral cinematic hook** for YouTube Shorts.

Topic:
- Name: {data.get("Name")}
- Theme: {data.get("Core Theme")}
- Input Notes (Vietnamese): {data.get("Content/Input")}

Requirements:
- Start immediately with a shock or mystery.
- No greetings, no "Imagine this", no explanations.
- Tone: legendary, dramatic, mysterious.
- Build rising tension.
- End with a cliffhanger.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.9,
        )

        short_script = response.choices[0].message.content.strip()

        # Save short script
        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(short_script)

        # Short title prompt
        title_prompt = f"""
Write a **5–8 word** CINEMATIC English title for a viral YouTube Short.
It must be mysterious and punchy.
Topic name: {data.get("Name")}
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

        logger.info(f"✨ Short EN script + title created for {data['ID']}")

        return out_script, out_title

    except Exception as e:
        logger.error(f"❌ Error generating short script: {e}")
        return None