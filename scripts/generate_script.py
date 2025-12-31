# === scripts/generate_script.py ===
import os
import logging
import json
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)
MODEL = "gpt-4o-mini"

# ============================================================
#  📝 HÀM HỖ TRỢ GỌI GPT (HELPER)
# ============================================================
def call_gpt(client, prompt, json_mode=True):
    response_format = {"type": "json_object"} if json_mode else {"type": "text"}
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format=response_format,
        temperature=0.7
    )
    return response.choices[0].message.content

# ============================================================
#  🚀 HÀM CHÍNH: TẠO KỊCH BẢN SIÊU DÀI (MULTI-STAGE)
# ============================================================
def generate_long_script(data):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: return None
        client = OpenAI(api_key=api_key)

        name = data.get("Name")
        theme = data.get("Core Theme")
        
        logger.info(f"🧠 BẮT ĐẦU QUY TRÌNH TẠO KỊCH BẢN 10 PHÚT+: {name}...")

        # --- BƯỚC 1: TẠO METADATA & ĐỀ CƯƠNG ---
        logger.info("   (Step 1/3): Generating SEO Metadata & Chapters...")
        meta_prompt = f"""
        Subject: {name}. Theme: {theme}.
        TASK: Create high-CTR Title, SEO Description (with timestamps), Tags, and a 5-part Outline.
        OUTPUT JSON: {{"title": "...", "description": "...", "tags": [], "chapters": ["Part 1 name", "Part 2 name", ...]}}
        """
        meta_json = json.loads(call_gpt(client, meta_prompt))

        # --- BƯỚC 2: VIẾT CHI TIẾT NỬA ĐẦU (INTRO, PART 1, PART 2) ---
        logger.info("   (Step 2/3): Writing Detailed Part 1, 2, 3 (Deep Dive)...")
        p1_prompt = f"""
        Subject: {name}. Context: {theme}. 
        TASK: Write the first half of a documentary script (Intro, {meta_json['chapters'][0]}, {meta_json['chapters'][1]}).
        REQUIREMENT: Write at least 900 words. Focus on sensory details, atmosphere, and deep history.
        OUTPUT: Plain text narration only.
        """
        part_1_text = call_gpt(client, p1_prompt, json_mode=False)

        # --- BƯỚC 3: VIẾT CHI TIẾT NỬA SAU (PART 3, 4, OUTRO) ---
        logger.info("   (Step 3/3): Writing Detailed Part 4, 5 & Legacy...")
        p2_prompt = f"""
        Subject: {name}. 
        TASK: Write the second half of the documentary script based on the following context: {part_1_text[-500:]}.
        Write for {meta_json['chapters'][2]}, {meta_json['chapters'][3]}, and a powerful Outro.
        REQUIREMENT: Write at least 900 words. Focus on analysis, hidden secrets, and lasting legacy.
        OUTPUT: Plain text narration only.
        """
        part_2_text = call_gpt(client, p2_prompt, json_mode=False)

        # --- KẾT HỢP DỮ LIỆU ---
        full_script = part_1_text + "\n\n" + part_2_text
        word_count = len(full_script.split())
        logger.info(f"📊 TỔNG ĐỘ DÀI: {word_count} từ (~{word_count/150:.1f} phút)")

        # Lưu file
        script_path = get_path("data", "episodes", f"{data['ID']}_long.txt")
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(full_script)
            
        return {
            "script_path": script_path,
            "metadata": {
                "Title": meta_json.get("title"),
                "Summary": meta_json.get("description"),
                "Tags": meta_json.get("tags")
            }
        }

    except Exception as e:
        logger.error(f"❌ Lỗi generate_long_script: {e}", exc_info=True)
        return None

# ============================================================
#  ✂️ HÀM CHIA 5 SHORTS (GIỮ NGUYÊN PIPELINE)
# ============================================================
def split_long_script_to_5_shorts(data, long_script_path):
    # Logic cũ của bạn rất ổn, giữ nguyên để đảm bảo an toàn cho Pipeline
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        with open(long_script_path, "r", encoding="utf-8") as f:
            full_text = f.read()

        logger.info("✂️ Đang chia nhỏ kịch bản khổng lồ thành 5 Shorts đa góc độ...")

        prompt = f"""
        Source Text: "{full_text[:7000]}"
        TASK: Extract 5 viral Short segments (< 60s) from the text. 
        Angles: 1. Shocking Hook, 2. Wisdom/Lesson, 3. Tragedy/Controversy, 4. Epic Quote, 5. Legacy.
        OUTPUT JSON: {{"shorts": [{{"title": "...", "content": "..."}}]}}
        """
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        res_json = json.loads(response.choices[0].message.content)
        shorts_data = res_json.get("shorts", [])

        output_list = []
        for i, item in enumerate(shorts_data):
            idx = i + 1
            s_path = get_path("data", "episodes", f"{data['ID']}_short_{idx}.txt")
            t_path = get_path("data", "episodes", f"{data['ID']}_short_{idx}_title.txt")
            with open(s_path, "w", encoding="utf-8") as f: f.write(item["content"])
            with open(t_path, "w", encoding="utf-8") as f: f.write(item["title"])
            output_list.append({"index": idx, "script": s_path, "title": t_path})
        return output_list
    except Exception as e:
        logger.error(f"❌ Lỗi split_shorts: {e}")
        return None
