import os
import logging
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"


def generate_long_script(data):
    """
    Sinh LONG SCRIPT tiếng Anh (600–700 words)
    Đảm bảo độ dài < 4096 ký tự để OpenAI TTS không lỗi.
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        prompt = f"""
You are a professional documentary writer. 
Write a **cinematic, dramatic, English storytelling script**, about the topic below.
The script will be used for TTS → MUST be between **600–700 words** (target 3800–4200 characters).

###
SUBJECT NAME: {data.get("Name")}
THEME / CORE MESSAGE: {data.get("Core Theme")}
INPUT NOTES: {data.get("Content/Input")}
###

Write in 5 clear sections:

[1] INTRO — 80–120 words  
- Strong cinematic opening  
- Build tension  
- Present the core mystery or conflict  

[2] BACKSTORY — 120–160 words  
- Important background  
- Events that shaped the character/theme  

[3] RISE / CONFLICT — 160–200 words  
- Dramatic escalation  
- Turning points  
- Emotional storytelling  

[4] RESOLUTION — 140–160 words  
- How things ended or where the story stands today  
- Lessons  
- Legacy  

[5] OUTRO — 80–100 words  
- Poetic ending  
- Leave listeners with emotion  
- Invitation to reflect  

Tone:  
• cinematic  
• legendary  
• suspenseful  
• emotionally deep  
• smooth flow for voice narration  

STRICT REQUIREMENTS:  
- 600–700 words only  
- No bullet points  
- No section titles, ONLY narrative paragraphs  
- Must read like a script for a dramatic voiceover  
- Fully in English  
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.85,
        )

        script_text = response.choices[0].message.content.strip()
        safe_text = script_text[:4000]  # safety limit

        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        logger.info(f"📝 Long script created: {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}")
        return None


def generate_short_script(data):
    """
    Tạo SHORT SCRIPT dạng hook 25–30s bằng tiếng Anh
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        prompt = f"""
Write a SHORT English script for a **25–30 second viral hook** for YouTube Shorts.
Topic:
NAME: {data.get("Name")}
THEME: {data.get("Core Theme")}
INPUT NOTES: {data.get("Content/Input")}

Requirements:
- 45–65 words total  
- Fast-paced, dramatic, shocking hook  
- Must feel legendary, mysterious, intense  
- No introduction, jump directly into the punchline  
- End with a strong cliffhanger  
- Pure narrative (no hashtags, no instructions)  
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.9,
        )

        script = response.choices[0].message.content.strip()

        # Save SHORT script
        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(script)

        # Generate hook title
        title_prompt = f"""
Write a 5–8 word SHORT TITLE for this topic.
Must sound viral, cinematic, mysterious.
Topic name: {data.get("Name")}
Theme: {data.get("Core Theme")}
"""
        title_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=50,
            temperature=0.9,
        )
        title = title_res.choices[0].message.content.strip()

        out_title = get_path("data", "episodes", f"{data['ID']}_short_title.txt")
        with open(out_title, "w", encoding="utf-8") as f:
            f.write(title)

        logger.info(f"✨ Short script + title created for {data['ID']}")
        return out_script, out_title

    except Exception as e:
        logger.error(f"❌ Error generating short script: {e}")
        return None
