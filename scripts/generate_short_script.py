# scripts/generate_short_script.py: Tạo kịch bản cho video NGẮN (9:16)
import os
import logging
import json
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_shorts_script(episode_data: dict):
    """
    Tạo kịch bản Shorts (9:16) và metadata YouTube từ dữ liệu Google Sheet.
    
    :param episode_data: Dict chứa dữ liệu của tập (sử dụng khóa title, character, core_theme)
    :return: Dict chứa đường dẫn file kịch bản và metadata YouTube
    """
    episode_id = episode_data['ID']
    title = episode_data['title']
    core_theme = episode_data['core_theme']
    character = episode_data['character']
    text_hash = episode_data['text_hash']
    
    # --- THỰC HIỆN GỌI LLM (Giả định) ---
    logging.info(f"Đang gọi LLM cho kịch bản NGẮN (Shorts 9:16) của: {title}")
    
    # TẠM THỜI SỬ DỤNG MOCK DATA ĐỂ CHẠY THỬ
    shorts_text = f"""
    [NHẠC KÍCH THÍCH BẮT ĐẦU]
    Lời dẫn (Nhanh): Bạn có biết, {character} đã làm một điều không tưởng liên quan đến {core_theme} là gì không?
    
    Điểm nhấn: {title}! Điều này đã thay đổi hoàn toàn cục diện.
    
    Kêu gọi hành động: Xem full video "{title}" trên kênh để biết thêm chi tiết!
    [NHẠC KẾT THÚC CỰC ĐỘT NGỘT]
    """
    
    shorts_title = f"#SHORTS | BÍ ẨN: {title} và {core_theme}!"
    shorts_description = f"Một góc nhìn nhanh về {core_theme} của {character}. Xem full tập podcast để hiểu rõ hơn!"

    # Ghi kịch bản ra file (sử dụng text_hash)
    script_output_dir = os.path.join('outputs', 'scripts')
    os.makedirs(script_output_dir, exist_ok=True)
    shorts_script_path = os.path.join(script_output_dir, f"{text_hash}_shorts_script.txt")
    
    with open(shorts_script_path, 'w', encoding='utf-8') as f:
        f.write(shorts_text)
        
    logging.info(f"Đã ghi kịch bản NGẮN thành công tại: {shorts_script_path}")

    # Trả về kết quả
    return {
        'shorts_script_path': shorts_script_path,
        'shorts_title': shorts_title,
        'shorts_description': shorts_description,
        'shorts_subtitle_path': os.path.join(script_output_dir, f"{text_hash}_shorts_subtitle.srt"),
    }
