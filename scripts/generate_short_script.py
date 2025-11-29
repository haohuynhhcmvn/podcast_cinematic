# ./scripts/generate_short_script.py (Tạo kịch bản ngắn, hấp dẫn cho Shorts)
import os
import logging
import json
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - 관광-message)s')

def generate_short_script(episode_data):
    """
    Tạo kịch bản siêu ngắn, hấp dẫn (hook) cho video Shorts.
    Độ dài mục tiêu: 100-120 từ (tương đương 45-60 giây đọc).
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logging.error("Thiếu OPENAI_API_KEY."); return None

    try:
        client = OpenAI(api_key=api_key)
        
        episode_id = episode_data['ID']
        title = episode_data['Name']
        core_theme = episode_data['Core Theme']
        raw_content = episode_data['Content/Input']
        
        # --- PROMPT MỚI: TẬP TRUNG VÀO HOOK VÀ SỰ NGẮN GỌN ---
        # Yêu cầu kịch bản ngắn, gây bất ngờ, không cần chào/kết.
        system_prompt = f"""
        Bạn là **Chuyên gia tạo Content Hút Khách** cho TikTok/YouTube Shorts.
        Nhiệm vụ của bạn là tạo ra một kịch bản audio **SIÊU NGẮN, GIẬT GÂN** (a powerful, surprising HOOK) để giữ chân người xem trong 5 giây đầu.

        QUY TẮC TẠO KỊCH BẢN (short_script):
        1. **Thời lượng Cứng:** Độ dài tối đa **120 từ**. Đây là yêu cầu BẮT BUỘC.
        2. **Nội dung:** Phải là một góc nhìn độc đáo, một bí mật, hoặc một câu hỏi gây sốc về nhân vật/chủ đề.
        3. **Giọng văn:** Nhanh, kịch tính, dồn dập, kết thúc mở hoặc bằng một tuyên bố mạnh mẽ.
        4. **Định dạng:** Chỉ văn bản cần được đọc (không chào/kết).

        CHỦ ĐỀ CỐT LÕI CỦA TẬP NÀY: "{core_theme}"
        TÊN NHÂN VẬT/TIÊU ĐỀ: "{title}"
        """

        user_prompt = f"""
        NỘI DUNG THÔ ĐỂ LẤY Ý TƯỞNG HOOK:\n---\n{raw_content}\n---\n
        Hãy tạo Kịch bản **NGẮN (dưới 120 từ)** và trả về dưới dạng JSON với 1 trường:
        {{
            "short_script": "[Nội dung kịch bản siêu ngắn, kịch tính]"
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.9, # Tăng nhiệt độ để nội dung bất ngờ hơn
            response_format={"type": "json_object"} 
        )
        
        # --- XỬ LÝ VÀ LƯU KỊCH BẢN CUỐI CÙNG ---
        try:
            json_response = json.loads(response.choices[0].message.content)
            short_script = json_response.get('short_script', '')
            
        except json.JSONDecodeError as e:
            logging.error(f"Lỗi phân tích cú pháp JSON Shorts từ OpenAI: {e}")
            return None

        # LƯU SCRIPT NGẮN
        output_dir = os.path.join('data', 'episodes')
        os.makedirs(output_dir, exist_ok=True)
        script_filename = f"{episode_id}_short_script.txt"
        script_path = os.path.join(output_dir, script_filename)
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(short_script.strip())
        
        logging.info(f"Đã tạo kịch bản Shorts thành công. Script lưu tại: {script_path}")
        
        return {'short_script_path': script_path}

    except Exception as e:
        logging.error(f"Lỗi tổng quát khi tạo kịch bản Shorts: {e}", exc_info=True)
        return None
