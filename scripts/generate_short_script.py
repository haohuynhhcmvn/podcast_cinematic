# ./scripts/generate_short_script.py (Generate short, compelling script for Shorts)
import os
import logging
import json
from openai import OpenAI
from dotenv import load_dotenv

# Fixing the logging format error for consistency
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_short_script(episode_data):
    """
    Generates an ultra-short, compelling hook script for YouTube Shorts.
    Target length: 100-120 words (equivalent to 45-60 seconds of reading).
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logging.error("Missing OPENAI_API_KEY."); return None

    try:
        client = OpenAI(api_key=api_key)
        
        episode_id = episode_data['ID']
        title = episode_data['Name']
        core_theme = episode_data['Core Theme']
        raw_content = episode_data['Content/Input']
        
        # --- NEW PROMPT: FOCUS ON HOOK AND CONCISENESS (IN ENGLISH) ---
        # Request a short, surprising script without intro/outro.
        system_prompt = f"""
        You are a **Viral Content Expert** for TikTok/YouTube Shorts.
        Your mission is to generate an **ULTRA-SHORT, SENSATIONAL** audio script (a powerful, surprising HOOK) to retain viewers within the first 5 seconds.

        SCRIPT GENERATION RULES (short_script):
        1. **Language:** The script MUST be written **ENTIRELY IN ENGLISH**.
        2. **Hard Length Limit:** Maximum length is **120 words**. This is a STRICT requirement.
        3. **Content:** Must be a unique angle, a secret, or a shocking question about the character/topic.
        4. **Tone:** Fast-paced, dramatic, urgent, ending with an open conclusion or a powerful statement.
        5. **Format:** Only include the text to be read (no intro/outro).

        CORE THEME FOR THIS EPISODE: "{core_theme}"
        CHARACTER/TOPIC NAME: "{title}"
        """

        user_prompt = f"""
        RAW CONTENT FOR HOOK IDEA GENERATION:\n---\n{raw_content}\n---\n
        Generate the **SHORT SCRIPT (under 120 words)** and return it as a JSON with 1 field:
        {{
            "short_script": "[Sensational, ultra-short script content in English]"
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.9, # Increased temperature for more surprising content
            response_format={"type": "json_object"} 
        )
        
        # --- PROCESS AND SAVE THE FINAL SCRIPT ---
        try:
            json_response = json.loads(response.choices[0].message.content)
            short_script = json_response.get('short_script', '')
            
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing Shorts JSON from OpenAI: {e}")
            return None

        # SAVE SHORT SCRIPT
        output_dir = os.path.join('data', 'episodes')
        os.makedirs(output_dir, exist_ok=True)
        script_filename = f"{episode_id}_short_script.txt"
        script_path = os.path.join(output_dir, script_filename)
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(short_script.strip())
        
        logging.info(f"Successfully created Shorts script. Script saved at: {script_path}")
        
        return {'short_script_path': script_path}

    except Exception as e:
        logging.error(f"General error while creating Shorts script: {e}", exc_info=True)
        return None
