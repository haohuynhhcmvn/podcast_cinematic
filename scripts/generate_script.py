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
    """Khôi phục hàm gốc của bạn và sửa lỗi Return Type"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        char_name = data.get("Name", "Historical Figure")
        
        # Sử dụng prompt chuyên nghiệp của bạn
        prompt = f"Write a 1800-word historical documentary script about {char_name}. Consequence-first hook..."
        
        response = client.chat.completions.create(
            model=MODEL, 
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000
        )
        raw_script = response.choices[0].message.content.strip()

        is_safe, trigger = check_safety_compliance(raw_script)
        if not is_safe: return None

        clean_script = clean_text_for_tts(raw_script)
        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(clean_script)

        # FIX: Trả về dict để glue_pipeline không bị lỗi 'string indices'
        return {
            "script_path": out_path,
            "metadata": {
                "youtube_title": f"The Secret Life of {char_name}",
                "youtube_description": f"Full story of {char_name}.",
                "youtube_tags": ["history", "biography"]
            }
        }
    except Exception as e:
        logger.error(f"Error Long Script: {e}")
        return None

def generate_multi_short_scripts(data, long_script_path):
    """Hàm tạo 5 kịch bản Shorts từ kịch bản dài"""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        with open(long_script_path, "r", encoding="utf-8") as f:
            long_content = f.read()

        prompt = f"Tạo 5 kịch bản Shorts từ nội dung sau: {long_content[:2000]}. JSON: {{'shorts': [{{'title': '...', 'script': '...'}}]}}"
        response = client.chat.completions.create(
            model=MODEL, 
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        
        shorts_data = json.loads(response.choices[0].message.content).get('shorts', [])
        results = []
        for i, item in enumerate(shorts_data[:5]):
            p_script = get_path("data", "episodes", f"{data['ID']}_s{i+1}.txt")
            p_title = get_path("data", "episodes", f"{data['ID']}_t{i+1}.txt")
            with open(p_script, "w", encoding="utf-8") as f: f.write(clean_text_for_tts(item['script']))
            with open(p_title, "w", encoding="utf-8") as f: f.write(item['title'])
            results.append({"script_path": p_script, "title_path": p_title, "index": i+1})
        return results
    except Exception as e:
        logger.error(f"Error Multi Shorts: {e}")
        return []
