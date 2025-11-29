# File: ./scripts/generate_script.py
# Chức năng: Gọi API LLM (OpenAI) để tạo kịch bản đầy đủ và metadata từ dữ liệu đầu vào.

import os
import sys
import json
import logging
import time
import random 
from openai import OpenAI, APIError
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cấu hình API cho việc TẠO KỊCH BẢN (Sử dụng OPENAI)
MODEL_NAME = "gpt-4o-mini" # Sử dụng mô hình OpenAI phù hợp
MAX_RETRIES = 5
INITIAL_DELAY = 2

# --- HÀM GỌI API OPENAI ---
def call_openai_api(system_prompt: str, user_query: str) -> str:
    """Gọi API OpenAI và xử lý exponential backoff."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("Thiếu OPENAI_API_KEY. Không thể gọi API tạo kịch bản.")
        return None

    client = OpenAI(api_key=api_key)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.7 # Thiết lập nhiệt độ phù hợp cho kịch bản sáng tạo
            )
            
            # Xử lý phản hồi thành công
            text = response.choices[0].message.content.strip()
            
            if text:
                return text
            else:
                logging.warning(f"API trả về nội dung trống. Thử lại sau.")

        except APIError as e:
            # Lỗi API của OpenAI (ví dụ: Rate limit, Authentication error)
            logging.warning(f"Lỗi API OpenAI (Lần {attempt+1}/{MAX_RETRIES}): {e}")
        except Exception as e:
            # Lỗi không xác định
            logging.error(f"Lỗi không xác định khi gọi API: {e}")
            break

        if attempt < MAX_RETRIES - 1:
            delay = INITIAL_DELAY * (2 ** attempt) + random.uniform(0, 1)
            logging.info(f"Đang chờ {delay:.2f} giây trước khi thử lại...")
            time.sleep(delay)
        else:
            logging.error("Đã thử lại tối đa. Thất bại khi tạo kịch bản.")
            return None
    return None

# --- HÀM CHÍNH: TẠO KỊCH BẢN ĐẦY ĐỦ ---
def generate_full_script(episode_data: dict) -> dict:
    """
    Tạo kịch bản đầy đủ (full script) và metadata bằng cách gọi API LLM (OpenAI).
    """
    
    # Chuẩn bị dữ liệu đầu vào
    title = episode_data.get('title', 'Câu chuyện hấp dẫn')
    character = episode_data.get('character', 'Ngôi sao nhạc pop thế giới')
    core_theme = episode_data.get('core_theme', 'Hành trình vượt qua thử thách để đạt được thành công')
    text_hash = episode_data.get('text_hash')
    episode_id = episode_data.get('ID')

    if not text_hash:
        logging.error("Không có hash để lưu file kịch bản.")
        return {}
    
    # 1. Định nghĩa System Prompt và User Query
    system_prompt = (
        "Bạn là một biên kịch podcast chuyên nghiệp. Nhiệm vụ của bạn là viết một kịch bản podcast "
        "dài, hấp dẫn, có tính giáo dục và truyền cảm hứng. Kịch bản phải có độ dài khoảng 1000-1200 từ, "
        "sử dụng ngôn ngữ thân mật, gần gũi, giọng điệu kể chuyện cuốn hút. "
        "Kịch bản phải được chia thành các đoạn văn ngắn, rõ ràng, phù hợp cho việc chuyển văn bản thành giọng nói (TTS). "
        "Đảm bảo không đưa tiêu đề (TITLE) hay tiêu đề phụ (HEADING) vào nội dung kịch bản, chỉ là đoạn văn thuần túy."
    )

    user_query = (
        f"Viết một kịch bản podcast hoàn chỉnh (khoảng 1000-1200 từ) dựa trên các thông tin sau:\n"
        f"- Tên tập/Tiêu đề: {title}\n"
        f"- Nhân vật chính: {character}\n"
        f"- Chủ đề cốt lõi: {core_theme}\n"
        f"Hãy đảm bảo nội dung hấp dẫn, truyền cảm hứng và không được vượt quá 1200 từ."
    )

    # 2. Gọi API để tạo kịch bản
    logging.info(f"Đang gọi LLM (OpenAI) để tạo kịch bản DÀI cho ID {episode_id}...")
    # Sửa tên hàm gọi API:
    script_content = call_openai_api(system_prompt, user_query)
    
    if not script_content:
        logging.error("LLM (OpenAI) không tạo được kịch bản.")
        return {}

    # 3. Lưu kịch bản vào file
    output_dir = os.path.join('data', 'episodes')
    os.makedirs(output_dir, exist_ok=True)
    full_script_path = os.path.join(output_dir, f"{text_hash}_full_script.txt")
    
    try:
        with open(full_script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        logging.info(f"Kịch bản DÀI đã được lưu thành công tại: {full_script_path}")
    except Exception as e:
        logging.error(f"Lỗi khi lưu file kịch bản: {e}")
        return {}
        
    # 4. Giả lập Metadata 
    metadata = {
        'title': title,
        'description': f"Tóm tắt câu chuyện về {character}. Chủ đề: {core_theme}.",
        'keywords': f"{character}, {title}, {core_theme}",
    }
    
    # Lưu metadata (ví dụ: JSON)
    metadata_path = os.path.join(output_dir, f"{text_hash}_metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    
    return {
        'full_script_txt_path': full_script_path,
        'metadata': metadata,
        'metadata_json_path': metadata_path,
    }

# --- HÀM TẠO KỊCH BẢN NGẮN (SHORT SCRIPT) ---
def generate_short_script(episode_data: dict) -> dict:
    """
    Tạo kịch bản ngắn (short script) tóm tắt nội dung chính bằng cách gọi API LLM (OpenAI).
    """
    
    # Chuẩn bị dữ liệu đầu vào
    title = episode_data.get('title', 'Tóm tắt câu chuyện hấp dẫn')
    character = episode_data.get('character', 'Ngôi sao nhạc pop thế giới')
    core_theme = episode_data.get('core_theme', 'Hành trình vượt qua thử thách để đạt được thành công')
    text_hash = episode_data.get('text_hash')
    episode_id = episode_data.get('ID')

    if not text_hash:
        logging.error("Không có hash để lưu file kịch bản ngắn.")
        return {}
    
    # 1. Định nghĩa System Prompt và User Query
    system_prompt = (
        "Bạn là một biên kịch chuyên nghiệp. Nhiệm vụ của bạn là viết một tóm tắt kịch bản ngắn (short script) "
        "khoảng 150-200 từ, có tính viral cao, dùng cho video dạng Shorts/TikTok. "
        "Kịch bản phải tóm tắt được nội dung chính một cách hấp dẫn. "
        "Kịch bản phải được chia thành các đoạn văn ngắn, rõ ràng, phù hợp cho việc chuyển văn bản thành giọng nói (TTS). "
        "Đảm bảo không đưa tiêu đề (TITLE) hay tiêu đề phụ (HEADING) vào nội dung kịch bản, chỉ là đoạn văn thuần túy."
    )

    user_query = (
        f"Viết một kịch bản ngắn (khoảng 150-200 từ) dựa trên các thông tin sau:\n"
        f"- Tên tập/Tiêu đề: {title}\n"
        f"- Nhân vật chính: {character}\n"
        f"- Chủ đề cốt lõi: {core_theme}\n"
        f"Hãy đảm bảo nội dung hấp dẫn, có tính lan truyền và không được vượt quá 200 từ."
    )

    # 2. Gọi API để tạo kịch bản
    logging.info(f"Đang gọi LLM (OpenAI) để tạo kịch bản NGẮN cho ID {episode_id}...")
    # Sửa tên hàm gọi API:
    script_content = call_openai_api(system_prompt, user_query)
    
    if not script_content:
        logging.error("LLM (OpenAI) không tạo được kịch bản ngắn.")
        return {}

    # 3. Lưu kịch bản vào file
    output_dir = os.path.join('data', 'episodes')
    os.makedirs(output_dir, exist_ok=True)
    short_script_path = os.path.join(output_dir, f"{text_hash}_short_script.txt")
    
    try:
        with open(short_script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        logging.info(f"Kịch bản NGẮN đã được lưu thành công tại: {short_script_path}")
    except Exception as e:
        logging.error(f"Lỗi khi lưu file kịch bản ngắn: {e}")
        return {}
        
    # Metadata (có thể đơn giản hơn cho short)
    metadata = {
        'short_title': title,
        'summary': f"Tóm tắt ngắn về {character}. Chủ đề: {core_theme}.",
    }
    
    # Lưu metadata (ví dụ: JSON)
    metadata_path = os.path.join(output_dir, f"{text_hash}_short_metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    
    return {
        'short_script_txt_path': short_script_path,
        'metadata': metadata,
        'metadata_json_path': metadata_path,
    }
