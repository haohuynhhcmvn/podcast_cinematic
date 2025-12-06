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
#  LONG SCRIPT GENERATOR (PHIÊN BẢN 8-10 PHÚT CHUẨN)
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

        # --- FINAL PROMPT: ÉP VIẾT DÀI & CHI TIẾT CẢM QUAN ---
        prompt = f"""
ROLE:
You are the Head Scriptwriter for "Legendary Footsteps".
Write a **HIGH-DETAIL, LONG-FORM** biography script (Minimum **1800 words**).
Target Video Length: **8 to 12 minutes** (The absolute minimum for monetization).

INPUT DATA:
- Character: {char_name}
- Theme: {core_theme}
- Notes: {input_notes}

CRITICAL RULES:
1. **ULTIMATE LENGTH REQUIREMENT (SENSORY DETAIL):** Do NOT summarize. Every section MUST include detailed sensory description (smell, temperature, specific sounds, palpable emotions, textures) AND/OR a dialogue/quote to push the narrative length beyond 8 minutes.
2. **NO POETIC FLUFF:** BANNED WORDS: tapestry, echoes, unfold, realm, bustling marketplace, swirling storm, testament to, shadows linger, voice of the past, mere words, weaving. Use gritty, real-world descriptions.
3. **DIALOGUE:** Reconstruct and include at least 3 to 5 actual quotes or monologues to extend the length and drama.
4. **VISUALS:** Use [Visual: description] tags frequently (at least every 3 sentences).

EXTENDED STRUCTURE (7 SECTIONS):
[SECTION 1: THE HOOK - 2 Mins] Start with a detailed, slow-motion description of a critical moment (Death or Victory). Focus on the sounds and smells.
[SECTION 2: THE CONTEXT & TRAUMA - 1 Min] The world before them. The family struggles. (Go deep into childhood trauma).
[SECTION 3: THE FIRST STRUGGLE - 1 Min] The early failures. The specific moment they almost gave up.
[SECTION 4: THE TURNING POINT & TACTICS - 2 Mins] Detailed explanation of ONE specific genius strategy. Explain the tactics in depth.
[SECTION 5: THE CLIMAX - 2 Mins] The biggest battle or confrontation. Describe the landscape minute-by-minute.
[SECTION 6: THE BETRAYAL/DOWNFALL] The specific people who turned against them. (Must include a direct quote).
[SECTION 7: LEGACY & PHILOSOPHY - 1 Min] A long, reflective conclusion on human nature.

OUTPUT: English only.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.85,
        )

        raw_script = response.choices[0].message.content.strip()

        # --- CLEAN TTS ---
        clean_script = clean_text_for_tts(raw_script)

        # -------------------------------------------------------
        # 🔓 GIỚI HẠN KÝ TỰ (GIỮ NGUYÊN 15000 CHO VIDEO DÀI)
        # -------------------------------------------------------
        safe_text = clean_script[:15000] 

        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        logger.info(f"📝 Long EN script created ({len(safe_text)} chars): {out_path}")

        # Metadata Generation
        meta_prompt = f"Write 1 Clickbait YouTube Title and a Short Description for {char_name}. The title MUST be clean and free of special characters or hashtags."
        meta_res = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": meta_prompt}], max_tokens=200
        )
        meta_text = meta_res.choices[0].message.content.strip()
        
        try:
            # Tách Title và Description
            if "Title:" in meta_text:
                raw_title = meta_text.split("Title:")[1].split("Description:")[0].strip()
            else:
                raw_title = meta_text.split("\n")[0] # Fallback nếu format sai

            if "Description:" in meta_text:
                yt_desc = meta_text.split("Description:")[1].strip()
            else:
                yt_desc = meta_text

            # 🔥 [FIX QUAN TRỌNG]: LÀM SẠCH TITLE CHO LONG FORM
            # Loại bỏ các từ khóa dễ gây hiểu lầm cho thuật toán
            yt_title = raw_title.replace('"', '').replace('**', '').replace('#', '').replace('Short', '').strip()
            
        except:
            yt_title = f"The Untold Story of {char_name}"
            yt_desc = meta_text

        metadata = {
            "youtube_title": yt_title,
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
#  SHORT SCRIPT GENERATOR (PHIÊN BẢN TỐI ƯU 55s & HARD CTA)
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

        # --- CẬP NHẬT PROMPT: KHẮC PHỤC LỖI 61 GIÂY & VĂN MẪU ---
        prompt = f"""
ROLE: Viral YouTube Shorts Scripter.
TASK: Write a **tight, fast-paced** 50-55 second script (MAXIMUM 135 words) for {char_name}.
INPUT: {input_notes}

CRITICAL RULES:
1. **LENGTH:** STRICTLY UNDER 140 words. If it's too long, it fails as a Short.
2. **NO POETIC FLUFF:** BANNED WORDS: tapestry, echoes, unfold, realm, weaving, testament, mere words, swirling. 
3. **TONE:** Direct, gritty, aggressive. No rhetorical questions at the end.

STRUCTURE:
1. HOOK (0-5s): Start immediately with a specific number or shocking fact. No "Did you know".
2. THE TWIST: Reveal the paradox or conflict.
3. THE BODY: Fast storytelling.
4. THE BRIDGE CTA (Must be exact): "Subscribe for more legends, and click the link below for the full brutal story!"

OUTPUT: English only.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300, # Giảm token để tránh AI viết lan man
            temperature=0.9,
        )

        raw_script = response.choices[0].message.content.strip()
        clean_script = clean_text_for_tts(raw_script)

        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(clean_script)

        # Tạo Title sạch (Không chứa #Shorts, không chứa ký tự lạ)
        title_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Write a 5-word CLICKBAIT title for {char_name}. NO HASHTAGS. NO QUOTES."}],
            max_tokens=50
        )
        # Làm sạch Title thủ công để chắc chắn 100%
        title = title_res.choices[0].message.content.strip().replace('"', '').replace('#', '').replace('Shorts', '')

        out_title = get_path("data", "episodes", f"{data['ID']}_short_title.txt")
        with open(out_title, "w", encoding="utf-8") as f:
            f.write(title)

        logger.info(f"✨ Short EN script created for {data['ID']}")
        return out_script, out_title

    except Exception as e:
        logger.error(f"❌ Error generating short script: {e}")
        return None
