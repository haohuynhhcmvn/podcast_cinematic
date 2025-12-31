# === scripts/generate_script.py ===
import os
import logging
import json
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# ✅ Đã chuyển về gpt-4o-mini theo yêu cầu
MODEL = "gpt-4o-mini"

# ============================================================
#  🛡️ BỘ LỌC AN NINH
# ============================================================
def check_safety_compliance(text):
    forbidden_keywords = [
        "overthrow the government", "regime change", "topple the regime",
        "incite rebellion", "destroy the state", "illegitimate government",
        "phản động", "lật đổ", "chống phá", "xuyên tạc", "bạo loạn"
    ]
    text_lower = text.lower()
    for word in forbidden_keywords:
        if word in text_lower:
            return False, f"Chứa từ khóa cấm: {word}"
    return True, "Safe"

# ============================================================
#  📝 HÀM 1: TẠO KỊCH BẢN DÀI (TỐI ƯU CHO MINI)
# ============================================================
def generate_long_script(data):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key: return None
        client = OpenAI(api_key=api_key)

        name = data.get("Name")
        theme = data.get("Core Theme")
        
        logger.info(f"🧠 Đang viết kịch bản (GPT-4o-mini) về: {name}...")

        # 💡 CHIẾN THUẬT CHO MINI:
        # 1. Giảm yêu cầu xuống 1500 từ (khoảng 8-10 phút) để tránh lỗi JSON.
        # 2. Ép cấu trúc chương hồi rõ ràng để AI không viết lười.
        prompt = f"""
        You are a professional documentary scriptwriter.
        Subject: {name}
        Theme: {theme}
        
        TASK: Write a detailed 10-minute documentary script (approx 1500 words).
        Tone: Cinematic, Engaging, Educational.
        
        CRITICAL: You MUST follow this structure to ensure length:
        1. INTRO (1 min): Hook the audience immediately.
        2. PART 1: BACKGROUND (2 mins): Early history/context.
        3. PART 2: MAIN EVENTS (3 mins): The core story, conflict, or discovery.
        4. PART 3: ANALYSIS (2 mins): Why this matters, hidden details.
        5. OUTRO (2 mins): Legacy and conclusion.

        Do NOT use "Scene" cues (like [Visuals]). Write ONLY the narration text.

        OUTPUT FORMAT (Strict JSON):
        {{
            "script": "The full narration text...",
            "title": "Clickbait YouTube Title",
            "description": "YouTube Description with hashtags...",
            "tags": ["tag1", "tag2", "tag3"]
        }}
        """

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_tokens=16000, # Mini hỗ trợ output token lớn, cứ để max
            temperature=0.7
        )

        content_raw = response.choices[0].message.content
        try:
            result_json = json.loads(content_raw)
        except json.JSONDecodeError:
            logger.error("❌ Lỗi JSON (gpt-4o-mini bị quá tải). Đang cứu dữ liệu...")
            return {
                "script_path": save_raw_script(data, content_raw),
                "metadata": {"Title": name, "Summary": "Documentary", "Tags": ["history"]}
            }

        script_text = result_json.get("script", "")
        
        # Log độ dài để bạn kiểm tra
        word_count = len(script_text.split())
        logger.info(f"📊 Độ dài kịch bản: {word_count} từ (~{word_count/150:.1f} phút)")

        # Kiểm tra an toàn
        is_safe, reason = check_safety_compliance(script_text)
        if not is_safe:
            logger.error(f"❌ Kịch bản bị từ chối: {reason}")
            return None

        script_filename = f"{data['ID']}_long.txt"
        script_path = get_path("data", "episodes", script_filename)
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_text)
            
        return {
            "script_path": script_path,
            "metadata": {
                "Title": result_json.get("title", f"Amazing Facts about {name}"),
                "Summary": result_json.get("description", f"Learn about {name}."),
                "Tags": result_json.get("tags", ["history", name])
            }
        }

    except Exception as e:
        logger.error(f"❌ Lỗi generate_long_script: {e}", exc_info=True)
        return None

def save_raw_script(data, text):
    """Hàm cứu dữ liệu khi JSON bị lỗi"""
    path = get_path("data", "episodes", f"{data['ID']}_long_raw.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

# ============================================================
#  ✂️ HÀM 2: CẮT KỊCH BẢN THÀNH 5 SHORTS
# ============================================================
def split_long_script_to_5_shorts(data, long_script_path):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)

        with open(long_script_path, "r", encoding="utf-8") as f:
            full_text = f.read()

        logger.info("✂️ Đang chia nhỏ kịch bản thành 5 Shorts...")

        # Giảm context gửi vào để tiết kiệm token cho mini
        prompt = f"""
        Source Text: "{full_text[:6000]}"

        TASK: Từ nội dung trên, trích xuất chính xác 5 đoạn kịch bản Shorts (mỗi đoạn < 60s). 
        Yêu cầu mỗi Short phải đánh vào một góc nhìn tâm lý khác nhau để không trùng lặp:

        1. Short 1 (The Hook): Sự thật gây sốc nhất hoặc một lầm tưởng phổ biến về nhân vật.
        2. Short 2 (The Lesson): Một bài học trí tuệ hoặc chiến thuật mà khán giả có thể áp dụng ngay.
        3. Short 3 (The Dark Side): Một góc khuất, bi kịch hoặc hành động gây tranh cãi của nhân vật.
        4. Short 4 (The Quote): Một câu nói bất hủ được đặt trong hoàn cảnh cực kỳ kịch tính.
        5. Short 5 (The Legacy): Tầm ảnh hưởng khủng khiếp của nhân vật đến thế giới hiện đại.

        OUTPUT FORMAT (Strict JSON):
        {{
          "shorts": [
            {{
              "title": "TIÊU ĐỀ HOOK NGẮN (VIẾT HOA)",
              "content": "Lời dẫn truyện đầy kịch tính, nhịp điệu nhanh, có mở đầu và kết thúc trọn vẹn."
            }},
            ... (lặp lại đủ 5 đoạn)
          ]
        }}
        """
        
        ##Source Text: "{full_text[:5000]}..."
        ##TASK: Extract 5 distinct, viral short segments (under 60s each).
        ##OUTPUT JSON: {{ "shorts": [ {{"title": "Hook", "content": "..."}}, ... ] }}
        

        response = client.chat.completions.create(
            model=MODEL, # Vẫn dùng mini
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        res_json = json.loads(response.choices[0].message.content)
        shorts_data = res_json.get("shorts", [])

        if not shorts_data: return None

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
