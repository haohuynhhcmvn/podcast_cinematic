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
#  🛡️ BỘ LỌC AN NINH (PYTHON GUARDRAIL)
# ============================================================
def check_safety_compliance(text):
    """
    Rà soát văn bản để tìm các từ khóa vi phạm chính sách an toàn/chính trị.
    Trả về: (is_safe: bool, reason: str)
    """
    # Danh sách từ khóa cấm (Bao gồm tiếng Anh và Tiếng Việt)
    # Tập trung vào các từ mang ý nghĩa: Lật đổ, Phản động, Kích động bạo lực chính trị, Xuyên tạc
    forbidden_keywords = [
        # --- Keywords Tiếng Anh (Risk Keywords) ---
        "overthrow the government", "regime change", "topple the regime",
        "incite rebellion", "destroy the state", "illegitimate government",
        "dictatorship of", "oppressive regime", 
        "distort history", "reactionary", "incite violence",
        
        # --- Keywords Tiếng Việt (Phòng trường hợp AI bịa hoặc quote tiếng Việt) ---
        "phản động", "lật đổ", "chống phá", "xuyên tạc", "biểu tình bạo loạn", 
        "bất mãn chế độ", "lật đổ chính quyền"
    ]
    
    text_lower = text.lower()
    
    for word in forbidden_keywords:
        if word in text_lower:
            return False, word # ⛔ Phát hiện từ cấm
            
    return True, None # ✅ An toàn


# ============================================================
#  HÀM LÀM SẠCH KỊCH BẢN
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
#  LONG SCRIPT GENERATOR (TÍCH HỢP SAFETY GUARDRAIL)
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

        # --- FINAL PROMPT: CẬP NHẬT QUY TẮC AN TOÀN CHÍNH TRỊ ---
        prompt = f"""
ROLE:
You are the Head Scriptwriter for "Legendary Footsteps".
Write a **HIGH-DETAIL, LONG-FORM** biography script (Minimum **1800 words**).
Target Video Length: **8 to 12 minutes** (The absolute minimum for monetization).

INPUT DATA:
- Character: {char_name}
- Theme: {core_theme}
- Notes: {input_notes}

CRITICAL RULES (STRICT COMPLIANCE REQUIRED):
1. **POLITICAL NEUTRALITY & LEGALITY (ZERO TOLERANCE):** - You MUST maintain strict historical objectivity. 
   - **ABSOLUTELY FORBIDDEN:** Content that promotes rebellion, "reactionary" ideologies, undermines national sovereignty, or incites hatred against any government.
   - Do NOT draw parallels to modern politics. Do NOT distort historical facts.
   - Focus strictly on the human journey, historical lessons, and factual events.

2. **ULTIMATE LENGTH REQUIREMENT (SENSORY DETAIL):** Do NOT summarize. Every section MUST include detailed sensory description (smell, temperature, specific sounds, palpable emotions, textures) AND/OR a dialogue/quote to push the narrative length beyond 8 minutes.
3. **NO POETIC FLUFF:** BANNED WORDS: tapestry, echoes, unfold, realm, bustling marketplace, swirling storm, testament to, shadows linger, voice of the past, mere words, weaving, the richness of the surrounding. Use gritty, real-world descriptions.
4. **DIALOGUE:** Reconstruct and include at least 3 to 5 actual quotes or monologues to extend the length and drama.
5. **VISUALS:** Use [Visual: description] tags frequently (at least every 3 sentences).
6. **SAFETY GUIDELINES:** Avoid graphic descriptions of excessive gore or sexual violence. Depict war/conflict with a focus on atmosphere and emotional weight, suitable for public broadcast.

EXTENDED STRUCTURE (7 SECTIONS):
[SECTION 1: THE HOOK - 2 Mins] Start with a detailed, slow-motion description of a critical moment (Death or Victory). Focus on the sounds and smells.
[SECTION 2: THE CONTEXT & TRAUMA - 1 Min] The world before them. The family struggles. (Go deep into childhood trauma).
[SECTION 3: THE FIRST STRUGGLE - 1 Min] The early failures. The specific moment they almost gave up.
[SECTION 4: THE TURNING POINT & TACTICS - 2 Mins] Detailed explanation of ONE specific genius strategy. Explain the tactics in depth.
[SECTION 5: THE CLIMAX - 2 Mins] The biggest battle or confrontation. Describe the landscape minute-by-minute.
[SECTION 6: THE DOWNFALL OR OBSTACLE] The specific people or circumstances that turned against them. (Maintain historical accuracy).
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

        # -------------------------------------------------------
        # 🛡️ KIỂM TRA AN TOÀN TRƯỚC KHI XỬ LÝ
        # -------------------------------------------------------
        is_safe, trigger_word = check_safety_compliance(raw_script)
        if not is_safe:
            logger.error(f"⛔ SECURITY ALERT: Long script for '{char_name}' BLOCKED.")
            logger.error(f"Reason: Found sensitive/forbidden keyword: '{trigger_word}'.")
            return None

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
            if "Title:" in meta_text:
                raw_title = meta_text.split("Title:")[1].split("Description:")[0].strip()
            else:
                raw_title = meta_text.split("\n")[0]

            if "Description:" in meta_text:
                yt_desc = meta_text.split("Description:")[1].strip()
            else:
                yt_desc = meta_text

            yt_title = raw_title.replace('"', '').replace('**', '').replace('#', '').replace('Short', '').replace('|', '').strip()
            
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
#  SHORT SCRIPT GENERATOR (TÍCH HỢP SAFETY GUARDRAIL)
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

        # --- CẬP NHẬT PROMPT: THÊM SYSTEM INSTRUCTION AN TOÀN ---
        prompt = f"""
ROLE: Viral YouTube Shorts Scripter.
TASK: Write a **tight, fast-paced** 50-55 second script (MAXIMUM 135 words) for {char_name}.
INPUT: {input_notes}

CRITICAL RULES:
1. **SAFETY & LEGALITY:** NO content promoting rebellion, reactionary ideologies, or hate speech. Keep it historically accurate and compliant with public broadcast standards.
2. **LENGTH:** STRICTLY UNDER 140 words. If it's too long, it fails as a Short.
3. **NO POETIC FLUFF:** BANNED WORDS: tapestry, echoes, unfold, realm, weaving, testament, mere words, swirling. 
4. **TONE:** Direct, gritty, aggressive but SAFE. No rhetorical questions at the end.

STRUCTURE:
1. HOOK (0-5s): Start immediately with a specific number or shocking fact. No "Did you know".
2. THE TWIST: Reveal the paradox or conflict.
3. THE BODY: Fast storytelling.
4. THE BRIDGE CTA (Must be exact): "Subscribe for more legends, and check the related video below for the full story!"

OUTPUT: English only.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.9,
        )

        raw_script = response.choices[0].message.content.strip()

        # -------------------------------------------------------
        # 🛡️ KIỂM TRA AN TOÀN SHORT SCRIPT
        # -------------------------------------------------------
        is_safe, trigger_word = check_safety_compliance(raw_script)
        if not is_safe:
            logger.error(f"⛔ SECURITY ALERT: Short script for '{char_name}' BLOCKED.")
            logger.error(f"Reason: Found sensitive/forbidden keyword: '{trigger_word}'.")
            return None

        clean_script = clean_text_for_tts(raw_script)

        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(clean_script)

        # Tạo Title sạch
        title_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Write a 5-word CLICKBAIT title for {char_name}. NO HASHTAGS. NO QUOTES. SAFE CONTENT."}],
            max_tokens=50
        )
        title = title_res.choices[0].message.content.strip().replace('"', '').replace('#', '').replace('Shorts', '')

        out_title = get_path("data", "episodes", f"{data['ID']}_short_title.txt")
        with open(out_title, "w", encoding="utf-8") as f:
            f.write(title)

        logger.info(f"✨ Short EN script created for {data['ID']}")
        return out_script, out_title

    except Exception as e:
        logger.error(f"❌ Error generating short script: {e}")
        return None
