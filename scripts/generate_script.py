# scripts/generate_script.py
import os
import logging
import re  # <--- Thư viện cần thiết để lọc văn bản
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# Giữ nguyên model bạn đang dùng
MODEL = "gpt-4o-mini" 

# ============================================================
#  HÀM LÀM SẠCH KỊCH BẢN CHO TTS (AN TOÀN & KHÔNG GÂY LỖI)
# ============================================================
def clean_text_for_tts(text):
    """
    Hàm này loại bỏ các chỉ dẫn kỹ thuật để TTS không đọc nhầm.
    Nó không làm thay đổi logic file hay đường dẫn.
    """
    if not text:
        return ""

    # 1. Xóa các ký tự Markdown in đậm/nghiêng (VD: **Word** -> Word)
    # TTS thường đọc sai hoặc ngập ngừng khi gặp ký tự này
    text = text.replace('**', '').replace('__', '')

    # 2. Xóa toàn bộ nội dung trong ngoặc vuông [ ] 
    # (Bao gồm: [Visual: ...], [SECTION 1], [Music fades])
    text = re.sub(r'\[.*?\]', '', text)

    # 3. Xóa các tiêu đề phân đoạn nếu AI quên đóng ngoặc (VD: SECTION 1: THE HOOK)
    # Tìm các dòng bắt đầu bằng Section/Part/Segment + số
    text = re.sub(r'(?i)^\s*(SECTION|PART|SEGMENT)\s+\d+.*$', '', text, flags=re.MULTILINE)

    # 4. Xóa các từ khóa chỉ dẫn đứng đầu dòng (VD: Visual: ..., Voiceover:)
    text = re.sub(r'(?i)^\s*(Visual|Sound|Scene|Instruction|Voiceover|Narrator)\s*:', '', text, flags=re.MULTILINE)

    # 5. Xóa các dòng trống dư thừa để file gọn gàng
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

        # Mapping dữ liệu chuẩn theo code của bạn
        char_name = data.get("Name", "Historical Figure")
        core_theme = data.get("Core Theme", "Biography")
        input_notes = data.get("Content/Input", "")

        # Prompt chuẩn (Đã tối ưu ở bước trước)
        prompt = f"""
ROLE:
You are the Head Scriptwriter for "Legendary Footsteps".
Write a viral, high-retention biography script (600-800 words).

INPUT DATA:
- Character: {char_name}
- Theme: {core_theme}
- Notes: {input_notes}

RULES:
1. NO POETIC FLUFF (No "tapestry", "echoes", "shadows linger").
2. NO CLICHÉ INTROS. Start "In Medias Res".
3. TONE: Gritty, fast-paced, psychological.
4. VISUALS: Use [Visual: description] for every scene.

STRUCTURE:
[SECTION 1: THE HOOK] Start with a shock/death/betrayal.
[SECTION 2: THE ORIGIN] The trauma/why.
[SECTION 3: THE RISE] Strategy & genius.
[SECTION 4: THE DOWNFALL] Hubris & mistake.
[SECTION 5: CONCLUSION] Philosophical truth.

OUTPUT: English only. Include [Visual: ...] tags.
"""

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500,
            temperature=0.85,
        )

        raw_script = response.choices[0].message.content.strip()

        # --- ÁP DỤNG HÀM CLEAN TTS TẠI ĐÂY ---
        clean_script = clean_text_for_tts(raw_script)
        # -------------------------------------

        # Cắt ngắn nếu quá dài (Safety trim)
        safe_text = clean_script[:4000]

        # Lưu file (Đường dẫn không đổi)
        out_path = get_path("data", "episodes", f"{data['ID']}_long_en.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(safe_text)

        logger.info(f"📝 Long EN script created & cleaned: {out_path}")

        # Metadata Generation (Không đổi)
        meta_prompt = f"Write 1 Clickbait YouTube Title and a Short Description for {char_name}. Format:\nTitle: ...\nDescription: ..."
        meta_res = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": meta_prompt}], max_tokens=200
        )
        meta_text = meta_res.choices[0].message.content.strip()
        
        try:
            yt_title = meta_text.split("Title:")[1].split("Description:")[0].strip()
            yt_desc = meta_text.split("Description:")[1].strip()
        except:
            yt_title = f"The Untold Story of {char_name}"
            yt_desc = meta_text

        metadata = {
            "youtube_title": yt_title.replace('"', ''),
            "youtube_description": yt_desc,
            "youtube_tags": ["history", "biography", "legendary footsteps", char_name.lower()]
        }

        return {
            "script_path": out_path,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"❌ Error generating long script: {e}")
        return None


# ============================================================
#  SHORT SCRIPT GENERATOR
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

        # Prompt kêu gọi kéo kênh
        prompt = f"""
ROLE: Viral YouTube Shorts Scripter.
TASK: Write a 60-second script (approx 130-150 words) for {char_name}.
INPUT CONTEXT (Vietnamese): {input_notes}

CRITICAL STRUCTURE:
1. **THE HOOK (0-5s):** Start with a SPECIFIC NUMBER or a SHOCKING FACT related to {char_name}.
2. **THE TWIST (5-15s):** Reveal a paradox or conflict.
3. **THE BODY:** Fast-paced storytelling. Gritty details.
4. **THE DUAL CTA (Must be fast):** - Mandatory Line: "Subscribe for more legends, and check the related video below for the full story."

STYLE:
- English Language.
- No "Hello guys". Direct, aggressive storytelling.
- Tone: Mysterious & Urgent.

Write the script now.
"""

#form cũ đã chạy
'''
        prompt = f"""
ROLE: Viral Shorts Scripter.
Write a 60-second script for {char_name}.
INPUT: {input_notes}

STRUCTURE:
1. HOOK (0-5s): Specific number or shocking fact.
2. TWIST: Paradox.
3. BODY: Fast storytelling.
4. LOOP CTA: "Check the related video."

STYLE: English. Direct. No "Hello guys".
"""
'''
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.9,
        )

        raw_script = response.choices[0].message.content.strip()

        # --- ÁP DỤNG HÀM CLEAN TTS TẠI ĐÂY ---
        clean_script = clean_text_for_tts(raw_script)
        # -------------------------------------

        out_script = get_path("data", "episodes", f"{data['ID']}_short_en.txt")
        with open(out_script, "w", encoding="utf-8") as f:
            f.write(clean_script)

        # Title Generation (Không đổi)
        title_res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"Write a 5-word CLICKBAIT title for {char_name}."}],
            max_tokens=50
        )
        title = title_res.choices[0].message.content.strip().replace('"', '')

        out_title = get_path("data", "episodes", f"{data['ID']}_short_title.txt")
        with open(out_title, "w", encoding="utf-8") as f:
            f.write(title)

        logger.info(f"✨ Short EN script created & cleaned for {data['ID']}")

        return out_script, out_title

    except Exception as e:
        logger.error(f"❌ Error generating short script: {e}")
        return None
