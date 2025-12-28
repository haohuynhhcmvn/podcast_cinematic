# scripts/generate_script.py
import os
import logging
import re
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
        if word in text_lower:
            return False, word
    return True, None

def clean_text_for_tts(text):
    if not text: return ""
    text = text.replace('**', '').replace('__', '')
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'(?i)^\s*(SECTION|PART|SEGMENT|Visual|Sound|Scene|Voiceover)\s*:', '', text, flags=re.MULTILINE)
    return text.strip()

def generate_long_script(data):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        char_name = data.get("Name", "Historical Figure")
        
        # 1. Tạo kịch bản dài
        prompt = f"Write a cinematic 1500-word historical script about {char_name}. Focus on their biggest mistake and the consequences. High-stakes opening."
        response = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            max_tokens=4000, temperature=0.85
        )
        raw_script = response.choices[0].message.content.strip()
        
        is_safe, trigger = check_safety_compliance(raw_script)
        if not is_safe: return None

        clean_script = clean_text_for_tts(raw_script)
        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(clean_script)

        # 2. Tạo Metadata
        meta_prompt = f"Write a clickbait YouTube title and description for a video about {char_name}."
        meta_res = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": meta_prompt}], max_tokens=300
        )
        meta_text = meta_res.choices[0].message.content.strip()
        
        # Logic tách Title và Desc đơn giản
        lines = meta_text.split('\n')
        yt_title = lines[0].replace("Title:", "").strip()
        yt_desc = "\n".join(lines[1:]).replace("Description:", "").strip()

        # TRẢ VỀ ĐÚNG CẤU TRÚC ĐỂ FIX LỖI KEYERROR
        return {
            "script_path": out_path,
            "content": clean_script,
            "metadata": {
                "Title": yt_title if yt_title else f"The Mystery of {char_name}",
                "Description": yt_desc,
                "Tags": ["history", "biography", char_name.lower()]
            }
        }
    except Exception as e:
        logger.error(f"❌ Error in generate_long_script: {e}")
        return None

def generate_5_short_scripts(data, long_script_text):
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = f"Extract 5 viral 50-second Short scripts from this long script: {long_script_text[:5000]}. Separate them with '---'."
        response = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.8
        )
        scripts = response.choices[0].message.content.strip().split("---")
        paths = []
        for i, s in enumerate(scripts[:5]):
            path = get_path("data", "episodes", f"{data['ID']}_short_{i+1}_en.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(clean_text_for_tts(s))
            paths.append(path)
        return paths
    except Exception as e:
        logger.error(f"❌ Error in generate_5_short_scripts: {e}")
        return []
