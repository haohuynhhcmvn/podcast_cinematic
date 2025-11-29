import os
import logging
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Khởi tạo OpenAI Client
# Key sẽ được lấy tự động từ biến môi trường OPENAI_API_KEY
client = OpenAI()

# --- CONFIG ---
OUTPUT_DIR = "data/episodes"
TARGET_WORD_COUNT = 3000 # Mục tiêu 2500-3000 từ cho video 15-20 phút
MODEL = "gpt-4o-mini" # Sử dụng mô hình tốc độ cao và chi phí thấp

# --- SCHEMA CHO ĐẦU RA JSON ---
# Yêu cầu mô hình trả về một đối tượng JSON với Script và Metadata
FULL_SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "YouTube Title: Hấp dẫn, chứa từ khóa, tối đa 80 ký tự."},
        "description": {"type": "string", "description": "YouTube Description: Chi tiết, bao gồm tóm tắt, chương mục, và kêu gọi hành động (Call to Action). Tối thiểu 500 ký tự."},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "YouTube Tags: Khoảng 10-15 từ khóa liên quan đến nội dung và chủ đề."},
        "script": {"type": "string", "description": "Kịch bản chi tiết, hấp dẫn, dài khoảng 2500 đến 3000 từ để đảm bảo thời lượng video khoảng 15-20 phút."}
    },
    "required": ["title", "description", "tags", "script"]
}

def generate_full_script(episode_data: dict) -> dict:
    """
    Sử dụng LLM để tạo kịch bản chi tiết và metadata YouTube.
    
    Args:
        episode_data (dict): Dữ liệu từ Google Sheet (ID, title, character, core_theme).
        
    Returns:
        dict: Chứa đường dẫn file kịch bản, tiêu đề và mô tả.
    """
    
    episode_id = episode_data.get('ID')
    text_hash = episode_data.get('text_hash')
    title = episode_data.get('title', 'Unknown Title')
    character = episode_data.get('character', 'Unknown Character')
    core_theme = episode_data.get('core_theme', 'Unknown Theme')
    
    # Tạo Prompt hướng dẫn chi tiết
    system_prompt = f"""
    Bạn là một chuyên gia viết kịch bản video/podcast chuyên nghiệp, hấp dẫn, và có tính học thuật cao.
    Nhiệm vụ của bạn là viết một kịch bản chi tiết, chất lượng cao, dài khoảng {TARGET_WORD_COUNT} từ 
    dựa trên chủ đề sau. Kịch bản phải có cấu trúc rõ ràng: Mở đầu gây tò mò, nội dung sâu sắc theo chủ đề, và kết luận đúc kết.
    
    YÊU CẦU ĐẦU RA: Phải là một đối tượng JSON hợp lệ theo schema được cung cấp.
    
    Ngôn ngữ: Tiếng Việt.
    Phong cách: Lôi cuốn, truyền cảm hứng, nhưng giữ tính xác thực và lịch sử.
    
    Nội dung:
    - Chủ đề chính: {core_theme}
    - Nhân vật/Đối tượng chính: {character}
    - Tiêu đề gợi ý (để viết script): {title}
    """
    
    # Tạo thư mục output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_filepath = os.path.join(OUTPUT_DIR, f"{text_hash}_full_script.json")
    
    try:
        logging.info(f"Đang gọi LLM ({MODEL}) để tạo kịch bản cho ID {episode_id}...")
        
        # Gọi API với Response Schema để đảm bảo đầu ra là JSON
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Vui lòng viết kịch bản cho tập '{title}' về '{character}' và chủ đề '{core_theme}'. Đảm bảo kịch bản dài khoảng {TARGET_WORD_COUNT} từ."}
            ],
            response_model=FULL_SCRIPT_SCHEMA, # Sử dụng Pydantic Schema
            max_tokens=None # Cho phép mô hình sử dụng tối đa tokens
        )
        
        # Dữ liệu trả về đã là đối tượng JSON/Dict
        json_output = response.model_dump()
        
        # 1. Ghi toàn bộ JSON Output (Script + Metadata)
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(json_output, f, ensure_ascii=False, indent=4)
            
        # 2. Tạo một file .txt chỉ chứa kịch bản (cho bước TTS sau này)
        script_only_path = os.path.join(OUTPUT_DIR, f"{text_hash}_full_script.txt")
        with open(script_only_path, 'w', encoding='utf-8') as f:
            f.write(json_output['script'])
            
        logging.info(f"Đã tạo và lưu kịch bản DÀI thành công tại: {output_filepath}")
        
        return {
            'full_script_json_path': output_filepath,
            'full_script_txt_path': script_only_path,
            'full_title': json_output['title'],
            'full_description': json_output['description']
        }

    except Exception as e:
        logging.error(f"LỖI TẠO KỊCH BẢN DÀI cho {title}: {e}", exc_info=True)
        # Tạo file trống để pipeline không bị dừng đột ngột
        with open(output_filepath, 'w', encoding='utf-8') as f:
             json.dump({"error": str(e)}, f, ensure_ascii=False, indent=4)
        return {
            'full_script_json_path': output_filepath,
            'full_script_txt_path': '',
            'full_title': f"[FAILED] {title}",
            'full_description': "Lỗi tạo kịch bản."
        }
        
if __name__ == "__main__":
    # Ví dụ chạy thử (chỉ chạy khi file được chạy trực tiếp)
    mock_data = {
        'ID': 999,
        'title': 'Sự sụp đổ của đế chế Nokia và bài học về sự đổi mới',
        'character': 'Nokia',
        'core_theme': 'Chiến lược kinh doanh và thất bại trong đổi mới công nghệ',
        'text_hash': 'abcdefg999'
    }
    result = generate_full_script(mock_data)
    logging.info(f"Kết quả thử nghiệm: {result.get('full_title')}")
