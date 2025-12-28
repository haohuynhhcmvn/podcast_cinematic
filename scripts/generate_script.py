import os
import logging
import re
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# ============================================================
#  MODEL CONFIG
# ============================================================
MODEL = "gpt-4o-mini"


# ============================================================
#  🛡️ SAFETY GUARDRAIL
# ============================================================
def check_safety_compliance(text):
    forbidden_keywords = [
        "overthrow the government", "regime change", "topple the regime",
        "incite rebellion", "destroy the state", "illegitimate government",
        "dictatorship of", "oppressive regime",
        "distort history", "reactionary", "incite violence",
        "phản động", "lật đổ", "chống phá", "xuyên tạc",
        "biểu tình bạo loạn", "bất mãn chế độ", "lật đổ chính quyền"
    ]

    text_lower = text.lower()
    for word in forbidden_keywords:
        if word in text_lower:
            return False, word

    return True, None


# ============================================================
#  CLEAN TEXT FOR TTS
# ============================================================
def clean_text_for_tts(text):
    if not text:
        return ""

    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(
        r"(?i)^\s*(SECTION|PART|SEGMENT)\s+\d+.*$",
        "",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"(?i)^\s*(Visual|Sound|Scene|Instruction|Voiceover|Narrator)\s*:",
        "",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(r"\n\s*\n", "\n\n", text).strip()
    return text


# ============================================================
#  LONG SCRIPT GENERATOR
# ============================================================
def generate_long_script(data):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        char_name = data.get("Name", "Historical Figure")
        core_theme = data.get("Core Theme", "Biography")
        input_notes = data.get("Content/Input", "")

        prompt = f"""
ROLE:
You are the Head Scriptwriter for "Legendary Footsteps".

OBJECTIVE:
Hook viewers who do NOT know this person.
Retention > education.

INPUT:
- Character: {char_name}
- Theme: {core_theme}
- Notes: {input_notes}

RULES:
- Consequence before cause
- No modern politics
- Focus on decisions, mistakes, cost
- Minimum 1800 words
- Gritty, cinematic English
- Use [Visual:] tags

STRUCTURE:
[1] Consequence
[2] Pressure
[3] First decision
[4] Strategy or illusion
[5] Climax
[6] Betrayal / failure
[7] Human lesson

OUTPUT: English only.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.85,
        )

        raw_script = response.choices[0].message.content.strip()

        is_safe, trigger = check_safety_compliance(raw_script)
        if not is_safe:
            logger.error(f"⛔ BLOCKED long script: {trigger}")
            return None

        clean_script = clean_text_for_tts(raw_script)
        safe_text = clean_script[:15000]

        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        logger.info(f"📝 Long script created: {out_path}")

        meta_prompt = f"Write a clean clickbait YouTube title and short description for {char_name}."
        meta_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": meta_prompt}],
            max_tokens=200,
        )
        meta_text = meta_res.choices[0].message.content.strip()

        yt_title = meta_text.split("\n")[0].replace('"', "").replace("#", "")
        yt_desc = meta_text

        return {
            "script_path": out_path,
            "metadata": {
                "youtube_title": yt_title,
                "youtube_description": yt_desc,
                "youtube_tags": ["history", "biography", char_name.lower()],
            },
        }

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}", exc_info=True)
        return None


# ============================================================
#  SINGLE SHORT SCRIPT (LEGACY – GIỮ ĐỂ TƯƠNG THÍCH)
# ============================================================
def generate_short_script(data):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        client = OpenAI(api_key=api_key)

        char_name = data.get("Name", "Legendary Figure")

        prompt = f"""
ROLE: Viral Shorts Scriptwriter.

RULES:
- 45–55 seconds
- Consequence-first hook
- Spoken English
- End with:
"The full story explains why this decision failed."

Character: {char_name}
"""

        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.9,
        )

        script = clean_text_for_tts(res.choices[0].message.content.strip())

        is_safe, trigger = check_safety_compliance(script)
        if not is_safe:
            return None

        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(script)

        return out_script, None

    except Exception:
        return None


# ============================================================
#  5 SHORTS FROM LONG SCRIPT (MAIN FEATURE)
# ============================================================
def generate_5_shorts_from_long(long_script_path: str, data: dict):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not os.path.exists(long_script_path):
            return None

        client = OpenAI(api_key=api_key)

        with open(long_script_path, "r", encoding="utf-8") as f:
            long_text = f.read()

        eid = str(data.get("ID"))

        prompt = f"""
ROLE: Professional Viral Shorts Editor.

TASK:
Extract EXACTLY 5 YouTube Shorts from this long script.

RULES:
- 45–55 seconds each
- Different moment each
- Consequence-first hook
- Spoken English
- End with:
"The full story explains why this decision failed."

FORMAT:
SHORT 1:
...
SHORT 2:
...
SHORT 3:
...
SHORT 4:
...
SHORT 5:
...

LONG SCRIPT:
{long_text}
"""

        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.9,
        )

        raw = res.choices[0].message.content.strip()

        is_safe, trigger = check_safety_compliance(raw)
        if not is_safe:
            return None

        shorts = []
        for i in range(1, 6):
            key = f"SHORT {i}:"
            part = raw.split(key)[1]
            if i < 5:
                part = part.split(f"SHORT {i+1}:")[0]
            shorts.append(clean_text_for_tts(part.strip()))

        paths = []
        for i, txt in enumerate(shorts, 1):
            path = get_path("data", "episodes", f"{eid}_short_{i}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            paths.append(path)

        logger.info(f"✨ Generated 5 shorts from long script")
        return paths

    except Exception as e:
        logger.error(f"❌ Error generating shorts: {e}", exc_info=True)
        return None
