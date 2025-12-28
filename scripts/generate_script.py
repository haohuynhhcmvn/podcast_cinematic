# scripts/generate_script.py
import os
import logging
import re
import json
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# Giữ nguyên model
MODEL = "gpt-4o-mini" 

# ============================================================
#  🛡️ BỘ LỌC AN NINH (PYTHON GUARDRAIL) - GIỮ NGUYÊN
# ============================================================
def check_safety_compliance(text):
    """
    Rà soát văn bản để tìm các từ khóa vi phạm chính sách an toàn/chính trị.
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
#  HÀM LÀM SẠCH KỊCH BẢN - GIỮ NGUYÊN
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
#  🎬 LONG SCRIPT GENERATOR - GIỮ NGUYÊN 100% LOGIC CỦA BẠN
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
ROLE: You are the Head Scriptwriter for "Legendary Footsteps".
OBJECTIVE: Write a retention-optimized script for {char_name}.
(Các yêu cầu về structure, consequence-first... của bạn được giữ nguyên ở đây)
...
"""
        # (Tôi lược bớt phần text prompt dài trong này để tiết kiệm không gian, 
        # nhưng khi bạn copy, hãy giữ nguyên prompt gốc của bạn nhé)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.85,
        )

        raw_script = response.choices[0].message.content.strip()

        is_safe, trigger_word = check_safety_compliance(raw_script)
        if not is_safe:
            logger.error(f"⛔ SECURITY ALERT: Long script for '{char_name}' BLOCKED.")
            return None

        clean_script = clean_text_for_tts(raw_script)
        safe_text = clean_script[:15000] 

        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        return clean_script # Trả về nội dung để các bước sau sử dụng

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}")
        return None

# ============================================================
#  ✨ HÀM MỚI: TẠO 05 SHORT SCRIPTS TỪ LONG SCRIPT
# ============================================================
def generate_multi_short_scripts(data, long_script_content):
    """
    Dựa trên kịch bản dài đã tạo, xẻ thành 5 đoạn shorts hấp dẫn.
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Dựa trên kịch bản video dài về '{data.get('Name')}' sau đây:
        ---
        {long_script_content[:4000]} 
        ---
        Nhiệm vụ: Tạo ra 5 kịch bản YouTube Shorts khác nhau (mỗi đoạn ~45-55 giây).
        Yêu cầu:
        1. Mỗi đoạn tập trung vào 1 sự thật hoặc khoảnh khắc kịch tính duy nhất.
        2. Giọng văn punchy, gây tò mò.
        3. Tuyệt đối tuân thủ an toàn chính trị.
        4. Trả về định dạng JSON:
        {{
          "shorts": [
            {{"title": "Clickbait Title 1", "script": "Script content 1"}},
            ...
          ]
        }}
        """
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        
        shorts_data = json.loads(response.choices[0].message.content).get('shorts', [])
        results = []
        
        for i, item in enumerate(shorts_data[:5]):
            idx = i + 1
            # Check safety cho từng đoạn short
            is_safe, _ = check_safety_compliance(item['script'])
            if not is_safe: continue

            p_script = get_path("data", "episodes", f"{data['ID']}_s{idx}.txt")
            p_title = get_path("data", "episodes", f"{data['ID']}_t{idx}.txt")
            
            with open(p_script, "w", encoding="utf-8") as f: 
                f.write(clean_text_for_tts(item['script']))
            with open(p_title, "w", encoding="utf-8") as f: 
                f.write(item['title'].replace('#', ''))
            
            results.append({"script_path": p_script, "title_path": p_title, "index": idx})
            
        return results
    except Exception as e:
        logger.error(f"❌ Lỗi tạo multi-shorts: {e}")
        return []

# Giữ nguyên hàm generate_short_script cũ của bạn để không hỏng pipeline hiện tại
def generate_short_script(data):
    # (Giữ nguyên code cũ của bạn tại đây)
    pass
