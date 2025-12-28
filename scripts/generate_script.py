# scripts/generate_script.py
import os
import logging
import re
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"

# ============================================================
# 🛡️ SAFETY GUARDRAIL
# ============================================================
def check_safety_compliance(text: str):
    forbidden_keywords = [
        "overthrow the government", "regime change", "topple the regime",
        "incite rebellion", "destroy the state", "reactionary",
        "incite violence",
        "phản động", "lật đổ", "chống phá", "xuyên tạc",
        "biểu tình bạo loạn", "lật đổ chính quyền"
    ]
    text_lower = text.lower()
    for kw in forbidden_keywords:
        if kw in text_lower:
            return False, kw
    return True, None


# ============================================================
# 🧹 CLEAN TEXT FOR TTS
# ============================================================
def clean_text_for_tts(text: str):
    if not text:
        return ""
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"(?i)^\s*(section|part|scene)\s+\d+.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


# ============================================================
# 🎬 GENERATE LONG SCRIPT
# ============================================================
def generate_long_script(data: dict):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY")
            return None

        client = OpenAI(api_key=api_key)

        char_name = data.get("Name", "Historical Figure")
        core_theme = data.get("Core Theme", "Biography")
        notes = data.get("Content/Input", "")

        prompt = f"""
ROLE: Head Scriptwriter for cinematic history channel.

OBJECTIVE:
Hook viewers emotionally. Start with consequence, not background.

CHARACTER: {char_name}
THEME: {core_theme}
NOTES: {notes}

RULES:
- No modern politics
- No rebellion ideology
- Focus on decisions, mistakes, consequences
- 1800+ words
- English only
"""

        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=4000
        )

        raw = res.choices[0].message.content.strip()

        is_safe, trigger = check_safety_compliance(raw)
        if not is_safe:
            logger.error(f"⛔ BLOCKED long script: {trigger}")
            return None

        clean = clean_text_for_tts(raw)[:15000]

        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(clean)

        # Metadata
        meta_prompt = f"Write 1 YouTube title and 1 short description for {char_name}."
        meta_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": meta_prompt}],
            max_tokens=150
        )
        meta_text = meta_res.choices[0].message.content.strip()

        return {
            "script_path": out_path,
            "metadata": {
                "youtube_title": meta_text.split("\n")[0][:100],
                "youtube_description": meta_text,
                "youtube_tags": ["history", char_name.lower()]
            }
        }

    except Exception as e:
        logger.error(f"❌ generate_long_script error: {e}", exc_info=True)
        return None


# ============================================================
# ✂️ SPLIT LONG → 5 SHORT SCRIPTS
# ============================================================
def split_long_script_to_5_shorts(long_script_path: str, data: dict):
    try:
        with open(long_script_path, "r", encoding="utf-8") as f:
            text = f.read()

        paragraphs = [p for p in text.split("\n\n") if len(p.strip()) > 180]
        if len(paragraphs) < 10:
            logger.error("❌ Long script too short for shorts.")
            return None

        total = len(paragraphs)
        size = total // 5
        short_paths = []

        for i in range(5):
            start = i * size
            end = start + size if i < 4 else total
            chunk = " ".join(paragraphs[start:end])

            words = chunk.split()
            if len(words) > 135:
                chunk = " ".join(words[:135])

            chunk = clean_text_for_tts(chunk)

            safe, trigger = check_safety_compliance(chunk)
            if not safe:
                logger.error(f"⛔ Short {i+1} blocked: {trigger}")
                return None

            out = get_path("data", "episodes", f"{data['ID']}_short_{i+1}_en.txt")
            with open(out, "w", encoding="utf-8") as f:
                f.write(chunk)

            short_paths.append(out)

        logger.info("✂️ Long script split into 5 shorts.")
        return short_paths

    except Exception as e:
        logger.error(f"❌ split_long_script_to_5_shorts error: {e}", exc_info=True)
        return None


# ============================================================
# 🎯 GENERATE 5 SHORT TITLES
# ============================================================
def generate_5_short_titles(short_script_paths: list, data: dict):
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        title_paths = []

        for idx, path in enumerate(short_script_paths, 1):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            prompt = f"""
Write ONE viral YouTube Shorts title.
Max 6 words. No hashtags. No quotes.

Story:
{content}
"""
            res = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.95,
                max_tokens=30
            )

            title = res.choices[0].message.content.strip().replace('"', '')
            out = get_path("data", "episodes", f"{data['ID']}_short_{idx}_title.txt")

            with open(out, "w", encoding="utf-8") as f:
                f.write(title)

            title_paths.append(out)

        logger.info("🎯 Generated 5 short titles.")
        return title_paths

    except Exception as e:
        logger.error(f"❌ generate_5_short_titles error: {e}", exc_info=True)
        return None
