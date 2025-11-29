# scripts/generate_script.py
import os
import logging
import json
import time

# Thêm import cho các hàm OpenAI
# from openai import OpenAI # Ví dụ

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Giả định: Sử dụng một hàm LLM để tạo nội dung
def call_llm_for_script(prompt, episode_name):
    """
    Hàm giả định gọi mô hình LLM (như Gemini hoặc OpenAI)
    để tạo kịch bản và metadata.
    """
    # TẠO KỊCH BẢN MÔ PHỎNG DỰA TRÊN DỮ LIỆU ĐẦU VÀO
    logging.info(f"Đang gọi LLM cho kịch bản: {episode_name}")
    
    # -----------------------------------------------------------
    # Ở đây, bạn sẽ gọi API LLM thực tế
    # Ví dụ: response = client.chat.completions.create(...)
    # -----------------------------------------------------------
    
    # Giả định dữ liệu trả về từ LLM
    mock_script = f"""
    [NHẠC NỀN HOÀNH TRÁNG BẮT ĐẦU]
    Lời dẫn: Kính chào quý vị và các bạn đến với "Theo Dấu Chân Huyền Thoại". 
    Hôm nay, chúng ta sẽ cùng nhau lật lại cuộc đời và sự nghiệp của {episode_name}.
    
    Phần 1 - Bối cảnh: 
    {episode_name} đã đi vào lịch sử không chỉ bởi tài năng mà còn bởi những biến cố. 
    Nội dung cốt lõi: {{CoreTheme}}
    
    Phần 2 - Nội dung chi tiết:
    Như thông tin đầu vào: {{ContentInput}}
    Cuộc đời ông/bà là một bản hùng ca với những nốt thăng trầm không thể nào quên.
    [NHẠC KẾT THÚC]
    """
    
    mock_title = f"[PODCAST] {episode_name}: Theo Dấu Chân Huyền Thoại - Tập {time.strftime('%Y%m%d')}"
    mock_description = f"Đây là tập podcast về {episode_name}. Chủ đề cốt lõi: {episode_name}."
    
    return mock_script, mock_title, mock_description

def generate_script(episode_data: dict):
    """
    Tạo kịch bản và metadata YouTube từ dữ liệu Google Sheet.
    
    :param episode_data: Dict chứa dữ liệu của tập (ID, Name, CoreTheme, ContentInput...)
    :return: Dict chứa đường dẫn file kịch bản và metadata YouTube
    """
    episode_id = episode_data['ID']
    episode_name = episode_data['Name']
    content_input = episode_data['ContentInput']
    core_theme = episode_data['CoreTheme']
    
    # Tạo Prompt cho LLM
    system_prompt = "Bạn là một nhà sản xuất kịch bản podcast chuyên nghiệp, giọng văn truyền cảm và hùng hồn."
    user_prompt = f"""
    Sử dụng nội dung sau để tạo một kịch bản podcast có độ dài 4-5 phút.
    - Tiêu đề tập: {episode_name}
    - Chủ đề cốt lõi: {core_theme}
    - Nội dung thô: {content_input}
    
    Yêu cầu:
    1. Chia kịch bản thành các phần rõ ràng (Lời dẫn, Phần 1, Phần 2...).
    2. Đưa ra 1 tiêu đề YouTube hấp dẫn và 1 đoạn mô tả video.
    3. Trả lời dưới dạng JSON có 3 trường: "script", "title", "description".
    """
    
    # --- THỰC HIỆN GỌI LLM ---
    # Thay thế bằng hàm gọi LLM thực tế của bạn
    # script_text, youtube_title, youtube_description = call_llm_for_script(...)
    
    # TẠM THỜI SỬ DỤNG MOCK DATA ĐỂ CHẠY THỬ
    script_text = f"""
    [NHẠC NỀN HOÀNH TRÁNG BẮT ĐẦU]
    Lời dẫn: Kính chào quý vị và các bạn đến với "Theo Dấu Chân Huyền Thoại". Hôm nay, chúng ta sẽ cùng nhau lật lại cuộc đời và sự nghiệp của {episode_name}.
    
    Phần 1 - Bối cảnh: 
    {episode_name} đã đi vào lịch sử không chỉ bởi tài năng mà còn bởi những biến cố. Nội dung cốt lõi: {core_theme}
    
    Phần 2 - Nội dung chi tiết:
    Như thông tin đầu vào: {content_input} Cuộc đời ông/bà là một bản hùng ca với những nốt thăng trầm không thể nào quên.
    [NHẠC KẾT THÚC]
    """
    youtube_title = f"[PODCAST] {episode_name}: Theo Dấu Chân Huyền Thoại | Tập {episode_id}"
    youtube_description = f"Hôm nay chúng ta cùng đi sâu vào chủ đề {core_theme} của {episode_name}."


    # Ghi kịch bản ra file
    script_output_dir = os.path.join('outputs', 'scripts')
    os.makedirs(script_output_dir, exist_ok=True)
    script_filename = f"{episode_id}_script.txt"
    script_path = os.path.join(script_output_dir, script_filename)
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_text)
        
    logging.info(f"Đã ghi kịch bản thành công tại: {script_path}")
    
    # Trả về kết quả
    return {
        'episode_id': episode_id,
        'script_path': script_path,
        'title': youtube_title,
        'description': youtube_description,
        'subtitle_path': os.path.join(script_output_dir, f"{episode_id}_subtitle.srt"), # Giả định file phụ đề
        'image_folder': episode_data['ImageFolder']
    }
