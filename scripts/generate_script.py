#./scripts/generate_script.py
import os
import logging
import json 
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_script(episode_data):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logging.error("Missing OPENAI_API_KEY."); return None

    try:
        client = OpenAI(api_key=api_key)
        
        # Lấy dữ liệu tập phim
        episode_id = episode_data['ID']
        title = episode_data['Name']
        core_theme = episode_data['Core Theme']
        raw_content = episode_data['Content/Input']
        
        # --- 1. ĐỊNH NGHĨA CÂU CHÀO VÀ CÂU KẾT CỐ ĐỊNH (TIẾNG ANH) ---
        CHANNEL_NAME = "Legends Trail Podcast" # Đổi tên kênh tiếng Việt thành Tiếng Anh
        
        PODCAST_INTRO = f"""
Welcome to the {CHANNEL_NAME}. This is where we explore compelling stories, unsolved mysteries, and little-known historical corners. 
Today, we delve into the journey of: {title}.
"""
        
        PODCAST_OUTRO = f"""
And that wraps up everything we explored on today's episode of {CHANNEL_NAME}. 
If you found this content helpful and inspiring, don't forget to hit the Subscribe button, share, and follow us so you don't miss our next journey of knowledge. 
Thank you for listening. See you in the next episode!
"""
        
        # --- 2. CẬP NHẬT PROMPT: YÊU CẦU LLM VIẾT BẰNG TIẾNG ANH ---
        system_prompt = f"""
        You are a **Master Storyteller** with a **deep, compelling, and inspiring Male Baritone voice style**.
        Your task is to transform the raw content below into a **JSON object** containing the Cinematic Audio Script (Core Content Only) and accompanying YouTube Metadata.
        
        SCRIPT GENERATION RULES (core_script):
        1. **Language:** The script MUST be written **ENTIRELY IN ENGLISH**.
        2. **Tone:** Compelling, sharp, clear, and rich in imagery.
        3. **Crucial Length Requirement (INCREASED):** The **core content** script should be approximately **2500 - 3000 words**. This is a strict requirement to ensure the video lasts a minimum of 15-20 minutes. Write in depth and detail to meet this length.
        4. **Format:** Only include the text to be read; DO NOT include the intro/outro greetings.

        YOUTUBE METADATA GENERATION RULES (ALL IN ENGLISH):
        1. **youtube_title:** Highly engaging title, maximum 100 characters.
        2. **youtube_description:** Detailed description (approx. 300 words), including summary, Call-to-Action (CTA), and hashtags.
        3. **youtube_tags:** A list of 10-15 relevant keywords, lowercase, separated by commas.

        CORE THEME FOR THIS EPISODE: "{core_theme}"
        CHARACTER/TOPIC NAME: "{title}"
        """

        user_prompt = f"""
        RAW CONTENT TO PROCESS:\n---\n{raw_content}\n---\n
        Generate the **CORE SCRIPT** and YouTube Metadata, returning the result as a JSON with the following 4 fields:
        {{
            "core_script": "[Core script content, EXCLUDING INTRO/OUTRO]",
            "youtube_title": "[Video Title]",
            "youtube_description": "[Video Description]",
            "youtube_tags": "[Video tags, comma-separated]"
        }}
        """

        # Gọi API OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.7,
            response_format={"type": "json_object"} 
        )
        
        # --- 3. XỬ LÝ VÀ GHÉP KỊCH BẢN CUỐI CÙNG ---
        try:
            json_response = json.loads(response.choices[0].message.content)
            
            core_script = json_response.get('core_script', '')
            youtube_title = json_response.get('youtube_title', '')
            youtube_description = json_response.get('youtube_description', '')
            youtube_tags_raw = json_response.get('youtube_tags', '')
            
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON from OpenAI: {e}")
            return None

        # GHÉP KỊCH BẢN CUỐI CÙNG: CÂU CHÀO + NỘI DUNG CHÍNH + CÂU KẾT
        script_content = PODCAST_INTRO.strip() + "\n\n" + core_script.strip() + "\n\n" + PODCAST_OUTRO.strip()
        
        # --- 4. LƯU SCRIPT VÀ TRẢ VỀ DATA ---
        output_dir = os.path.join('data', 'episodes')
        os.makedirs(output_dir, exist_ok=True)
        script_filename = f"{episode_id}_script.txt"
        script_path = os.path.join(output_dir, script_filename)
        
        # Lưu toàn bộ kịch bản đã ghép (Intro + Core + Outro)
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        logging.info(f"Successfully created script (including intro/outro) and metadata. Script saved at: {script_path}")
        
        # Trả về Dictionary chứa cả path và metadata
        return {
            'script_path': script_path,
            'youtube_title': youtube_title,
            'youtube_description': youtube_description,
            'youtube_tags': [tag.strip() for tag in youtube_tags_raw.split(',')] 
        }

    except Exception as e:
        logging.error(f"General error while creating script: {e}", exc_info=True)
        return None
