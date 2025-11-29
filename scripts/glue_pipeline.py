import logging
import os
import time

# IMPORT CÁC HÀM CẦN THIẾT
# Thay thế read_sheet (hoặc get_episode_data) bằng fetch_content
from fetch_content import fetch_content, update_sheet_status
# Import hàm tạo kịch bản thực tế
from generate_script import generate_full_script
# TẠM THỜI DÙNG MOCK CHO HÀM NGẮN
def generate_shorts_script(data): 
    logging.info(f"MOCK: Tạo kịch bản NGẮN cho {data.get('title')}")
    hash_id = data.get('text_hash')
    return {
        'shorts_script_json_path': f"data/episodes/{hash_id}_shorts_script.json",
        'shorts_script_txt_path': f"data/episodes/{hash_id}_shorts_script.txt",
        'shorts_title': f"[SHORT] {data.get('title')}", 
        'shorts_description': 'Mock Shorts Desc'
    }

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("--- BẮT ĐẦU PIPELINE TẠO NỘI DUNG ---")
    
    # 1. LẤY DỮ LIỆU TỪ GOOGLE SHEET (Sử dụng hàm thống nhất: fetch_content)
    episode_data = fetch_content()
    
    if episode_data is None:
        logging.info("Pipeline kết thúc. Không tìm thấy tập mới để xử lý.")
        return

    episode_id = episode_data['ID']
    title = episode_data['title']
    text_hash = episode_data['text_hash']
    logging.info(f"Đang xử lý tập: {title} (ID: {episode_id}, Hash: {text_hash})")
    
    # Dict tổng hợp kết quả của tất cả các bước
    all_results = {'episode_data': episode_data}
    
    try:
        # 2.A. TẠO KỊCH BẢN DÀI (FULL SCRIPT) - HÀM THỰC TẾ
        logging.info("Bắt đầu tạo kịch bản DÀI (16:9)...")
        full_results = generate_full_script(episode_data)
        all_results.update(full_results)
        logging.info("Tạo kịch bản DÀI thành công.")

        # 2.B. TẠO KỊCH BẢN NGẮN (SHORTS SCRIPT) - HÀM MOCK
        logging.info("Bắt đầu tạo kịch bản NGẮN (Shorts 9:16)...")
        shorts_results = generate_shorts_script(episode_data)
        all_results.update(shorts_results)
        logging.info("Tạo kịch bản NGẮN thành công.")

        # Cập nhật trạng thái thành công
        update_sheet_status(episode_id, "processed")
        
    except Exception as e:
        logging.error(f"PIPELINE THẤT BẠI cho tập '{title}'. Chi tiết: {e}", exc_info=True)
        update_sheet_status(episode_id, "failed")
        
if __name__ == "__main__":
    main()
