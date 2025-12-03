# scripts/generate_script.py
import os
import logging
import re
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# Giữ nguyên model
MODEL = "gpt-4o-mini" 

# ============================================================
#  HÀM LÀM SẠCH KỊCH BẢN (GIỮ NGUYÊN)
# ============================================================
def clean_text_for_tts(text):
    if not text: return ""
    text = text.replace('**', '').replace('__', '')
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'(?i)^\s*(SECTION|PART|SEGMENT)\s+\d+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?i)^\s*(Visual|Sound|Scene|Instruction|Voiceover|Narrator)\s*:', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    return text

# ============================================================
#  LONG SCRIPT GENERATOR (PHIÊN BẢN 8-10 PHÚT)
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

        # --- NÂNG CẤP PROMPT ĐỂ VIẾT DÀI HƠN (DEEP DIVE) ---
        prompt = f"""
ROLE:
You are the Head Scriptwriter for "Legendary Footsteps".
Write a **DEEP DIVE, LONG-FORM** biography script (Minimum **1500-1800 words**).
Target Video Length: **8 to 12 minutes**.

INPUT DATA:
- Character: {char_name}
- Theme: {core_theme}
- Notes: {input_notes}

CRITICAL RULES:
1. **LENGTH IS KING:** Do NOT summarize. Expand on details. Describe the weather, the smell of the battlefield, the specific emotions.
2. **NO POETIC FLUFF:** No "tapestry", "echoes", "unfold". Use gritty, real-world descriptions.
3. **DIALOGUE:** Reconstruct specific conversations or monologues based on historical records to add length and drama.
4. **VISUALS:** Use [Visual: description] tags frequently.

EXTENDED STRUCTURE (7 SECTIONS):
[SECTION 1: THE HOOK - 2 Mins] Start with a detailed, slow-motion description of a critical moment (Death or Victory).
[SECTION 2: THE CONTEXT] The world before them. The family struggles. (Go deep into childhood trauma).
[SECTION 3: THE FIRST STRUGGLE] The early failures. The specific moment they almost gave up.
[SECTION 4: THE TURNING POINT] The strategy that changed everything. Explain the tactics in detail.
[SECTION 5: THE CLIMAX] The biggest battle or conflict. Describe it minute-by-minute.
[SECTION 6: THE BETRAYAL/DOWNFALL] The specific people who turned against them.
[SECTION 7: LEGACY & PHILOSOPHY] A long, reflective conclusion on human nature.

OUTPUT: English only.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000, # Tăng token cho câu trả lời
            temperature=0.85,
        )

        raw_script = response.choices[0].message.content.strip()

        # --- CLEAN TTS ---
        clean_script = clean_text_for_tts(raw_script)

        # -------------------------------------------------------
        # 🔓 MỞ KHÓA GIỚI HẠN (QUAN TRỌNG NHẤT)
        # -------------------------------------------------------
        # Cũ: [:4000] -> Mới: [:15000]
        # 15,000 ký tự ~ 2500 từ ~ 15 phút nói.
        safe_text = clean_script[:15000] 

        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        logger.info(f"📝 Long EN script created ({len(safe_text)} chars): {out_path}")

        # Metadata Generation
        meta_prompt = f"Write 1 Clickbait YouTube Title and a Short Description for {char_name}."
        meta_res = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": meta_prompt}], max_tokens=200
        )
        meta_text = meta_res.choices[0].message.content.strip()
        
        try:
            yt_title = meta_text.split("Title:")[1].split("Description:")[0].strip()
            yt_desc = meta_text.split("Description:")[1].strip()
        except:
            yt_title = f"The Untold Story of {char_name}"
            yt_desc = meta_text

        metadata = {
            "youtube_title": yt_title.replace('"', ''),
            "youtube_description": yt_desc,
            "youtube_tags": ["history", "biography", char_name.lower()]
        }

        return {
            "script_path": out_path,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}")
        return None


# ============================================================
#  SHORT SCRIPT GENERATOR (GIỮ NGUYÊN)
# ============================================================
def generate_short_script(data):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)
        
        char_name = data.get("Name", "Legendary Figure")
        input_notes = data.get("Content/Input", "")

        prompt = f"""
ROLE: Viral YouTube Shorts Scripter.
TASK: Write a 60-second script (approx 140-160 words) for {char_name}.
INPUT: {input_notes}

STRUCTURE:
1. HOOK (0-5s): Specific number or shocking fact.
2. TWIST: Paradox.
3. BODY: Fast storytelling.
4. DUAL CTA: "Subscribe for more, and check the related video below."

STYLE: English. Direct. Mysterious.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.9,
        )

        raw_script = response.choices[0].message.content.strip()
        clean_script = clean_text_for_tts(raw_script)

        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(clean_script)

        title_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Write a 5-word CLICKBAIT title for {char_name}."}],
            max_tokens=50
        )
        title = title_res.choices[0].message.content.strip().replace('"', '')

        out_title = get_path("data", "episodes", f"{data['ID']}_short_title.txt")
        with open(out_title, "w", encoding="utf-8") as f:
            f.write(title)

        logger.info(f"✨ Short EN script created for {data['ID']}")
        return out_script, out_title

    except Exception as e:
        logger.error(f"❌ Error generating short script: {e}")
        return None
