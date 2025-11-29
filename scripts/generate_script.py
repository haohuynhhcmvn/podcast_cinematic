# scripts/generate_script.py: Tạo kịch bản cho video DÀI (16:9)
import os
import logging
import json
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_full_script(episode_data: dict):
    """
    Tạo kịch bản Full (16:9) và metadata YouTube từ dữ liệu Google Sheet.
    
    :param episode_data: Dict chứa dữ liệu của tập (sử dụng khóa title, character, core_theme)
    :return: Dict chứa đường dẫn file kịch bản và metadata YouTube
    """
    episode_id = episode_data['ID']
    title = episode_data['title']
    core_theme = episode_data['core_theme']
    character = episode_data['character']
    text_hash = episode_data['text_hash']
    
    # --- THỰC HIỆN GỌI LLM (Giả định) ---
    logging.info(f"Đang gọi LLM cho kịch bản DÀI (16:9) của: {title}")
    
    # TẠM THỜI SỬ DỤNG MOCK DATA ĐỂ CHẠY THỬ
    script_text = f"""
    [NHẠC NỀN HOÀNH TRÁNG BẮT ĐẦU]
    Lời dẫn: Kính chào quý vị và các bạn đến với "Theo Dấu Chân Huyền Thoại". Hôm nay, chúng ta sẽ cùng nhau lật lại câu chuyện về "{title}".
    
    Phần 1 - Bối cảnh: 
    {character} là nhân vật chính. Chủ đề cốt lõi là: {core_theme}
    
    Phần 2 - Nội dung chi tiết:
    Cuộc đời {character} là một bản hùng ca với những nốt thăng trầm không thể nào quên.
    [NHẠC KẾT THÚC]
    """
    
    youtube_title = f"[PODCAST] {title}: Theo Dấu Chân Huyền Thoại | Tập {episode_id}"
    youtube_description = f"Hôm nay chúng ta cùng đi sâu vào {core_theme} của {character}. #Podcast #LịchSử"

    # Ghi kịch bản ra file (sử dụng text_hash)
    script_output_dir = os.path.join('outputs', 'scripts')
    os.makedirs(script_output_dir, exist_ok=True)
    full_script_path = os.path.join(script_output_dir, f"{text_hash}_full_script.txt")
    
    with open(full_script_path, 'w', encoding='utf-8') as f:
        f.write(script_text)
        
    logging.info(f"Đã ghi kịch bản DÀI thành công tại: {full_script_path}")
    
    # Trả về kết quả
    return {
        'full_script_path': full_script_path,
        'full_title': youtube_title,
        'full_description': youtube_description,
        'full_subtitle_path': os.path.join(script_output_dir, f"{text_hash}_full_subtitle.srt"),
    }
