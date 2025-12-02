# scripts/generate_script.py
import os
import logging
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# Khuyên dùng gpt-4o để viết văn phong kể chuyện tốt nhất
MODEL = "gpt-4o-mini" 

# ============================================================
#  LONG SCRIPT GENERATOR (ENGLISH • HIGH RETENTION)
# ============================================================
def generate_long_script(data):
    """
    Generate Long Script based on:
    - Name
    - Core Theme
    - Content/Input
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # --- 1. TRÍCH XUẤT DỮ LIỆU ĐẦU VÀO (INPUT MAPPING) ---
        # Đảm bảo khớp chính xác với các Key trong Data Object của bạn
        char_name = data.get("Name", "Historical Figure")
        core_theme = data.get("Core Theme", "Biography")
        input_notes = data.get("Content/Input", "")

        # --- 2. MASTER SYSTEM PROMPT (LONG FORM) ---
        # Đã đưa biến {core_theme} vào để AI hiểu bối cảnh tốt hơn
        prompt = f"""
ROLE:
You are the Head Scriptwriter for "Legendary Footsteps", a top-tier YouTube history channel.
Your goal is to write a viral, high-retention biography script (approx 600-800 words) that sounds like a Netflix thriller.

INPUT DATA (FROM VIETNAMESE SOURCE):
- Character Name: {char_name}
- Core Theme/Archetype: {core_theme}
- Detailed Notes: {input_notes}

CRITICAL RULES (NON-NEGOTIABLE):
1. **NO POETIC FLUFF:** BANNED words: "tapestry", "echoes of time", "shadows linger", "unfold", "in the midst", "testament to".
2. **NO CLICHÉ INTROS:** NEVER start with "Born in...", "Welcome back...", or "Let's dive in".
3. **TONE:** Gritty, fast-paced, psychological. Use active voice.
4. **VISUALS:** You MUST provide visual descriptions in brackets [Visual: ...] for every scene.

SCRIPT STRUCTURE:

[SECTION 1: THE HOOK - 00:00 to 00:45]
- **Technique:** Start "In Medias Res" (Start with a death, a betrayal, or a crisis).
- **The Context:** Briefly mention the {core_theme} to set the mood.
- **The Twist:** Present a Paradox about {char_name}.
- **Ending:** A "Curiosity Gap" question.

[SECTION 2: THE ORIGIN OF EVIL/GENIUS]
- Focus on the TRAUMA or PAIN found in the input notes.
- What made them hungry for power?

[SECTION 3: THE RISE & STRATEGY]
- How did they destroy their enemies?
- Use specific details from the "Detailed Notes" provided above.

[SECTION 4: THE DOWNFALL]
- The moment of Hubris (Arrogance).
- The specific mistake leading to the end.

[SECTION 5: THE CONCLUSION]
- End with a dark, philosophical truth about human nature.
- **Final Line:** A punchy statement looping back to the Hook.

OUTPUT FORMAT:
- English Language Only.
- Clear paragraph breaks.
- Include [Visual: ...] cues.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.85, 
        )

        script_text = response.choices[0].message.content.strip()

        # Safety trimming (<4000 chars cho TTS)
        safe_text = script_text[:4000]

        # --- 3. XỬ LÝ ĐẦU RA (OUTPUT MAPPING) ---
        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        logger.info(f"📝 Long EN script created: {out_path}")

        # --- 4. TẠO METADATA TỰ ĐỘNG ---
        meta_prompt = f"""
Based on the story of {char_name} ({core_theme}), write:
1. One High-CTR YouTube Title (Max 60 chars, Clickbait style).
2. A Short Description (First 2 lines must be a hook).
Output format:
Title: [Text]
Description: [Text]
"""
        meta_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": meta_prompt}],
            max_tokens=200,
            temperature=0.9
        )
        meta_text = meta_res.choices[0].message.content.strip()
        
        try:
            yt_title = meta_text.split("Title:")[1].split("Description:")[0].strip()
            yt_desc = meta_text.split("Description:")[1].strip()
        except:
            yt_title = f"The Insane True Story of {char_name}"
            yt_desc = meta_text

        metadata = {
            "youtube_title": yt_title.replace('"', ''),
            "youtube_description": yt_desc,
            "youtube_tags": ["history", "documentary", "biography", "legendary footsteps", char_name.lower(), core_theme.lower()]
        }

        return {
            "script_path": out_path,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}")
        return None



# ============================================================
#  SHORT SCRIPT GENERATOR (ENGLISH • VIRAL LOOP)
# ============================================================
def generate_short_script(data):
    """
    Generate Short Script based on Name & Content/Input
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # Input Mapping
        char_name = data.get("Name", "Legendary Figure")
        input_notes = data.get("Content/Input", "")

        # --- VIRAL SHORTS PROMPT ---
        prompt = f"""
ROLE: Viral YouTube Shorts Scripter.
TASK: Write a 60-second script (approx 130-150 words) for {char_name}.
INPUT CONTEXT (Vietnamese): {input_notes}

CRITICAL STRUCTURE (THE LOOP):
1. **THE HOOK (0-5s):** Start with a SPECIFIC NUMBER or a SHOCKING FACT related to {char_name}.
2. **THE TWIST (5-15s):** Reveal a paradox.
3. **THE BODY:** Fast-paced storytelling based on the input context.
4. **THE CTA & LOOP:** End with a question that loops back to the start.
   - Mandatory CTA: "Check the related video for the full truth."

STYLE:
- English Language.
- No "Hello guys". Direct, aggressive storytelling.

Write the script now.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.9,
        )

        short_script = response.choices[0].message.content.strip()

        # Output Mapping
        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(short_script)

        # Title Generation
        title_prompt = f"""
Write a **5-word** CLICKBAIT English title for a YouTube Short about {char_name}.
Must invoke CURIOSITY or SHOCK.
"""
        title_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=50,
            temperature=0.9,
        )
        title = title_res.choices[0].message.content.strip().replace('"', '')

        out_title = get_path("data", "episodes", f"{data['ID']}_short_title.txt")
        with open(out_title, "w", encoding="utf-8") as f:
            f.write(title)

        logger.info(f"✨ Short EN script + title created for {data['ID']}")

        return out_script, out_title

    except Exception as e:
        logger.error(f"❌ Error generating short script: {e}")
        return None
