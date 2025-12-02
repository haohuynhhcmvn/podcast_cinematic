import os
import logging
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"


# ===================================================================
#  LONG SCRIPT (TIẾNG ANH) — 550–650 WORDS (~3500–3900 ký tự)
# ===================================================================
def generate_long_script(data):
    """
    Generate LONG SCRIPT in English (550–650 words)
    Guaranteed length < 4096 chars to avoid TTS errors.
    """

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # --- PROMPT TỐI ƯU ---
        prompt = f"""
Write a **cinematic English storytelling script** about the legendary figure below.

NAME: {data.get("Name")}
THEME: {data.get("Core Theme")}
INPUT NOTES: {data.get("Content/Input")}

Requirements:
- 550–650 words total  
- Style: cinematic, emotional, dramatic, legendary  
- 5 chapter structure:
  1. Hook  
  2. Origin  
  3. Conflict  
  4. Climax  
  5. Legacy / Ending  
- No bullet points
- Must read like a narrative podcast
- No Vietnamese
- No markdown, no headings with symbols (** ### ** etc.) — use plain text only
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.85,
        )

        script_text = response.choices[0].message.content.strip()

        # Safety trimming (max 3900 chars)
        safe_text = script_text[:3900]

        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        logger.info(f"📝 Long script created safely (<4000 chars): {out_path}")

        return {
            "script_path": out_path,
            "metadata": {
                "youtube_title": f"{data.get('Name')} – The Untold Story",
                "youtube_description": f"Cinematic storytelling about {data.get('Name')}.",
                "youtube_tags": "podcast,storytelling,legend,history"
            }
        }

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}")
        return None



# ===================================================================
#  SHORT SCRIPT (25–30s) — 45–65 WORDS
# ===================================================================
def generate_short_script(data):
    """
    Create a 25–30 second English hook script (45–65 words)
    """

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # ---------------- SHORT SCRIPT ----------------
        prompt = f"""
Write a SHORT English script for a **25–30 second viral YouTube Shorts hook**.

Topic:
Name: {data.get("Name")}
Theme: {data.get("Core Theme")}
Notes: {data.get("Content/Input")}

Requirements:
- 45–65 words total
- Start instantly with a shocking or dramatic moment
- Very fast-paced and emotional
- Legendary tone, cinematic tension
- Ends with a cliffhanger
- NO instructions, NO hashtags, NO commentary
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.95,
        )

        script = response.choices[0].message.content.strip()

        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(script)

        # ---------------- SHORT TITLE ----------------
        title_prompt = f"""
Write a **5–8 word viral cinematic title**.
Should feel mysterious, powerful, dramatic.
Topic: {data.get("Name")}
"""

        title_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=30,
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