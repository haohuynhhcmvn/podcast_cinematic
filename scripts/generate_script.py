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
    forbidden_keywords = [
        "overthrow the government", "regime change", "topple the regime",
        "incite rebellion", "destroy the state", "illegitimate government",
        "dictatorship of", "oppressive regime", 
        "distort history", "reactionary", "incite violence",
        "phản động", "lật đổ", "chống phá", "xuyên tạc", "biểu tình bạo loạn", 
        "bất mãn chế độ", "lật đổ chính quyền"
    ]
    
    text_lower = text.lower()
    for word in forbidden_keywords:
        if word in text_lower:
            return False, word
            
    return True, None


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
ROLE: Head Scriptwriter for "Legendary Footsteps".
OBJECTIVE: Hook viewers with high-stakes consequence first. Minimum 1800 words.
INPUT: {char_name}, {core_theme}, {input_notes}.
RULES: Strict historical objectivity, no modern politics. Reveal consequence before cause.
"""
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.85,
        )

        raw_script = response.choices[0].message.content.strip()
        is_safe, trigger_word = check_safety_compliance(raw_script)
        if not is_safe:
            logger.error(f"⛔ SECURITY ALERT: Long script BLOCKED. Reason: {trigger_word}")
            return None

        clean_script = clean_text_for_tts(raw_script)
        safe_text = clean_script[:15000] 

        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        # Metadata Generation logic...
        # [Phần tạo Metadata giữ nguyên như code cũ của bạn]

        return {"script_path": out_path, "content": safe_text} # Trả về content để làm đầu vào cho Shorts

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}")
        return None

# ============================================================
#  🚀 5x SHORTS GENERATOR (NEW LOGIC)
# ============================================================
def generate_5_short_scripts(data, long_script_text):
    """
    Trích xuất 5 kịch bản Shorts từ kịch bản dài dựa trên 5 góc độ tâm lý.
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        char_name = data.get("Name", "Legendary Figure")

        prompt = f"""
ROLE: Viral Content Strategist. Extract 5 high-retention Short scripts (45-60s) from the LONG SCRIPT provided.
LONG SCRIPT: {long_script_text[:7000]} 

ANGLES REQUIRED:
1. THE MISTAKE: Focus on the biggest error/regret.
2. THE BETRAYAL: Focus on conflict or emotional tension.
3. THE SHOCKING FACT: A detail about {char_name} that is hard to believe.
4. THE STRATEGY: A genius move that eventually backfired.
5. THE LESSON: A brutal truth about human nature.

RULES:
- Start with a strong HOOK (0-3s).
- MAX 130 words per script.
- FORMAT: Script 1 --- Script 2 --- Script 3 --- Script 4 --- Script 5
- CTA: "The full story explains why this failed. Link in description."
"""
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        
        scripts = response.choices[0].message.content.strip().split("---")
        paths = []
        for i, s in enumerate(scripts[:5]):
            # Kiểm tra an toàn cho từng đoạn short
            is_safe, trigger = check_safety_compliance(s)
            if not is_safe: continue

            clean_s = clean_text_for_tts(s)
            path = get_path("data", "episodes", f"{data['ID']}_short_{i+1}_en.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(clean_s)
            paths.append(path)
            
        logger.info(f"✅ Created {len(paths)} short scripts for {char_name}")
        return paths

    except Exception as e:
        logger.error(f"❌ Error generating 5 shorts: {e}")
        return []
