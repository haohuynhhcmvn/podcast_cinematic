# scripts/generate_script.py
import os
import logging
import re
import json
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)
MODEL = "gpt-4o-mini" 

def check_safety_compliance(text):
    forbidden_keywords = [
        "overthrow the government", "regime change", "topple the regime",
        "incite rebellion", "destroy the state", "illegitimate government",
        "phản động", "lật đổ", "chống phá", "xuyên tạc"
    ]
    text_lower = text.lower()
    for word in forbidden_keywords:
        if word in text_lower: return False, word
    return True, None

def clean_text_for_tts(text):
    if not text: return ""
    text = text.replace('**', '').replace('__', '')
    text = re.sub(r'\[.*?\]', '', text)
    return text.strip()

def generate_long_script(data):
    """KHÔI PHỤC KỊCH BẢN 1800 CHỮ VÀ TẠO TITLE TỰ ĐỘNG"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        char_name = data.get("Name", "Historical Figure")
        core_theme = data.get("Core Theme", "Biography")
        input_notes = data.get("Content/Input", "")

        # PROMPT GỐC 1800 CHỮ CỦA BẠN
        prompt = f"""
ROLE: Head Scriptwriter for "Legendary Footsteps".
OBJECTIVE: 1800-word script about {char_name}. 
THEME: {core_theme} | NOTES: {input_notes}

RULES:
1. START with a HIGH-STAKES CONSEQUENCE (Hook).
2. STRUCTURE: [SECTION 1: THE CONSEQUENCE] to [SECTION 7: HUMAN LESSON].
3. Minimum 1800 words. Gritty, cinematic tone.
4. Use [Visual: description] tags.
"""
        response = client.chat.completions.create(
            model=MODEL, 
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.85
        )
        raw_script = response.choices[0].message.content.strip()

        is_safe, trigger = check_safety_compliance(raw_script)
        if not is_safe: return None

        clean_script = clean_text_for_tts(raw_script)
        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(clean_script)

        # TỰ ĐỘNG TẠO TIÊU ĐỀ HẤP DẪN TỪ AI
        title_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Write a 7-word CLICKBAIT title for a documentary about {char_name}. No quotes."}]
        )
        yt_title = title_res.choices[0].message.content.strip().replace('"', '')

        # TRẢ VỀ DICT ĐỂ FIX LỖI TYPEERROR
        return {
            "script_path": out_path,
            "metadata": {
                "Title": yt_title,
                "Summary": f"Bản kịch bản đầy đủ về {char_name}. {core_theme}",
                "Tags": ["history", "biography", char_name.lower()]
            }
        }
    except Exception as e:
        logger.error(f"❌ Lỗi tạo Long Script: {e}")
        return None

def generate_multi_short_scripts(data, long_script_path):
    """XẺ KỊCH BẢN DÀI THÀNH 5 SHORTS"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        with open(long_script_path, "r", encoding="utf-8") as f:
            long_content = f.read()

        prompt = f"Từ kịch bản này: {long_content[:2000]}. Tạo 5 Shorts JSON: {{'shorts': [{{'title': '...', 'script': '...'}}]}}"
        response = client.chat.completions.create(
            model=MODEL, 
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        
        shorts_data = json.loads(response.choices[0].message.content).get('shorts', [])
        results = []
        for i, item in enumerate(shorts_data[:5]):
            idx = i + 1
            p_script = get_path("data", "episodes", f"{data['ID']}_s{idx}.txt")
            p_title = get_path("data", "episodes", f"{data['ID']}_t{idx}.txt")
            with open(p_script, "w", encoding="utf-8") as f: f.write(clean_text_for_tts(item['script']))
            with open(p_title, "w", encoding="utf-8") as f: f.write(item['title'])
            results.append({"script_path": p_script, "title_path": p_title, "index": idx})
        return results
    except Exception as e:
        logger.error(f"❌ Lỗi tạo Multi Shorts: {e}")
        return []
