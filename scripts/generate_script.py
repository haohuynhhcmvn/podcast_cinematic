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


         # --- FINAL PROMPT: GROWTH-OPTIMIZED + SAFETY COMPLIANT ---
        # CHỈNH SỬA: 
        # - Thêm Hook đánh vào HỆ QUẢ ngay từ đầu
        # - Ép tư duy QUYẾT ĐỊNH & SAI LẦM (không kể tiểu sử thuần)
        # - VẪN giữ độ dài + an toàn chính trị

        prompt = f"""
ROLE:
You are the Head Scriptwriter for "Legendary Footsteps".

OBJECTIVE (GROWTH-CRITICAL):
This script must HOOK viewers who do NOT know this person.
Prioritize retention, emotional tension, and curiosity over education.

INPUT DATA:
- Character: {char_name}
- Theme: {core_theme}
- Notes: {input_notes}

CRITICAL RULES (NON-NEGOTIABLE):

1. POLITICAL NEUTRALITY & LEGALITY:
- Maintain strict historical objectivity.
- ABSOLUTELY FORBIDDEN: rebellion, reactionary ideology, modern political parallels.
- Focus on human decisions, consequences, and historical lessons only.

2. OPENING RULE (MOST IMPORTANT):
- DO NOT start with childhood, background, or chronology.
- START with a HIGH-STAKES CONSEQUENCE:
  death, collapse, betrayal, irreversible loss, or ultimate victory.
- Make the viewer feel: “How did it come to this?”

3. NARRATIVE LOGIC:
- Always reveal CONSEQUENCE before CAUSE.
- Focus on:
  • Decisions
  • Mistakes
  • Strategic thinking
  • Human flaws under pressure

4. LENGTH REQUIREMENT (UNCHANGED):
- Minimum 1800 words.
- Target runtime: 8–12 minutes.
- Do NOT summarize.
- Use sensory detail and reconstructed dialogue to maintain length.

5. LANGUAGE & STYLE:
- Gritty, grounded, cinematic.
- NO poetic fluff.
- BANNED WORDS remain enforced.

6. VISUALS:
- Use [Visual: description] tags frequently (unchanged).

EXTENDED STRUCTURE (REFINED FOR RETENTION):

[SECTION 1 – THE CONSEQUENCE (2 mins)]
Start at the moment everything is lost or decided.
No introduction. No explanation. Just impact.

[SECTION 2 – THE PRESSURE BUILDING]
Reveal the hidden forces, enemies, or internal flaws.

[SECTION 3 – THE FIRST CRITICAL DECISION]
The moment that set everything in motion.

[SECTION 4 – THE STRATEGY OR ILLUSION]
What they believed would save them—and why it worked (or didn’t).

[SECTION 5 – THE CLIMAX]
Minute-by-minute tension of the decisive event.

[SECTION 6 – THE BETRAYAL / FAILURE / COST]
Who turned. What failed. What could not be undone.

[SECTION 7 – THE HUMAN LESSON]
What this reveals about power, ambition, and human nature.
NO modern politics.

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
        # --- UPDATED SHORTS PROMPT: RETENTION-FIRST ---
        # CHỈNH SỬA:
        # - Không bắt đầu bằng số máy móc
        # - Thêm CONSEQUENCE-FIRST hook
        # - CTA kích thích session thay vì xin sub lộ liễu

        prompt = f"""
ROLE: Viral YouTube Shorts Scriptwriter.
OBJECTIVE: Stop scrolling within 3 seconds.

INPUT:
- Character: {char_name}
- Notes: {input_notes}

CRITICAL RULES:
1. SAFETY & LEGALITY: Fully compliant. No rebellion, no modern politics.
2. LENGTH: 45–55 seconds. MAX 135 words.
3. NO POETIC FLUFF. Spoken, punchy English.
4. Write for viewers who DO NOT know this person.

STRUCTURE (RETENTION-OPTIMIZED):

1. HOOK (0–3s):
Start with a consequence, mistake, or shocking outcome.
NO names. NO dates.

2. THE TURN:
Reveal the decision or belief that caused it.

3. ESCALATION:
Fast, tense storytelling. Short sentences.

4. OPEN LOOP CTA (DO NOT CHANGE WORDING):
\"The full story explains why this decision failed.\"

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
