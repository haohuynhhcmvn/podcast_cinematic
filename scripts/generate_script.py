import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_script(episode_data):
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
        
        system_prompt = f"""
        Bạn là **Master Storyteller** (Người kể chuyện bậc thầy) với giọng văn **Nam Trầm, lôi cuốn, có chiều sâu và truyền cảm hứng**. 
        Nhiệm vụ của bạn là biến nội dung thô dưới đây thành một kịch bản audio cinematic, phù hợp cho podcast chất lượng cao.

        QUY TẮC:
        1. **Giọng văn:** Lôi cuốn, sắc nét, rõ ràng, giàu hình ảnh.
        2. **Thời lượng:** Kịch bản nên có độ dài khoảng 10 - 15 từ.
        3. **Định dạng Output:** Phải là nội dung kịch bản thuần túy, không có lời dẫn (ví dụ: [GIỌNG NAM TRẦM ĐỌC:]). Chỉ bao gồm văn bản cần được đọc.

        CHỦ ĐỀ CỐT LÕI CỦA TẬP NÀY: "{core_theme}"
        TÊN NHÂN VẬT/TIÊU ĐỀ: "{title}"
        """

        user_prompt = f"""NỘI DUNG THÔ CẦN XỬ LÝ:\n---\n{raw_content}\n---\nHãy bắt đầu tạo kịch bản ngay bây giờ."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.7
        )
        
        script_content = response.choices[0].message.content
        
        output_dir = os.path.join('data', 'episodes')
        script_filename = f"{episode_id}_script.txt"
        script_path = os.path.join(output_dir, script_filename)
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        logging.info(f"Đã tạo kịch bản thành công và lưu tại: {script_path}")
        return script_path

    except Exception as e:
        logging.error(f"Lỗi khi gọi API OpenAI để tạo kịch bản: {e}")
        return None
