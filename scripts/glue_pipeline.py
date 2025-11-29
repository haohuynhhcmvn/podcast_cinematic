import os
import sys
import logging
import time
import json
from dotenv import load_dotenv

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Thêm thư mục scripts vào PATH để import
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

# Import các modules cần thiết
try:
    from fetch_content import fetch_pending_episodes, update_episode_status
    from generate_script import generate_full_script 
    from text_to_speech import text_to_speech 
    from finalize_audio import finalize_audio 
except ImportError as e:
    logging.error(f"Lỗi Import: Không thể tải một trong các module. Vui lòng kiểm tra tên file. Lỗi: {e}")
    sys.exit(1)


# --- MOCK CHỨC NĂNG TẠO KỊCH BẢN NGẮN (CHƯA TRIỂN KHAI) ---
def mock_generate_short_script(episode_data: dict, full_script_path: str):
    """
    Giả lập việc tạo kịch bản ngắn bằng cách lấy 1/4 nội dung của kịch bản dài.
    Sau này sẽ thay bằng gọi LLM để tóm tắt.
    """
    
    # Lấy hash và ID
    text_hash = episode_data.get('text_hash')
    episode_id = episode_data.get('ID')
    
    if not full_script_path or not os.path.exists(full_script_path):
        logging.warning("Không tìm thấy kịch bản dài để tạo kịch bản ngắn mock.")
        return {'short_script_txt_path': ''}

    output_dir = os.path.join('data', 'episodes')
    short_script_path = os.path.join(output_dir, f"{text_hash}_short_script.txt")

    try:
        logging.info(f"MOCK: Tạo kịch bản NGẮN cho ID {episode_id}")
        
        with open(full_script_path, 'r', encoding='utf-8') as f:
            full_script_content = f.read()
        
        # Lấy 1/4 kịch bản dài làm kịch bản ngắn (tạm thời)
        words = full_script_content.split()
        short_content = ' '.join(words[:len(words)//4])

        with open(short_script_path, 'w', encoding='utf-8') as f:
            f.write(short_content)

        return {
            'short_script_txt_path': short_script_path,
        }

    except Exception as e:
        logging.error(f"LỖI MOCK TẠO KỊCH BẢN NGẮN: {e}")
        return {'short_script_txt_path': ''}
# -----------------------------------------------------------------


def run_pipeline():
    """Chạy toàn bộ quy trình tạo nội dung từ Google Sheet."""
    load_dotenv()
    logging.info("--- BẮT ĐẦU PIPELINE TẠO NỘI DUNG ---")
    
    # BƯỚC 1: LẤY DỮ LIỆU TỪ GOOGLE SHEET
    episodes_to_process = []
    try:
        episodes_to_process = fetch_pending_episodes()
    except Exception as e:
        logging.error(f"LỖI KẾT NỐI/ĐỌC SHEET: {e}")
        return

    if not episodes_to_process:
        logging.info("Không tìm thấy tập mới nào cần xử lý ('pending').")
        return

    for episode in episodes_to_process:
        episode_id = episode.get('ID')
        text_hash = episode.get('text_hash')
        title = episode.get('title', 'Tập Không Tiêu Đề')
        
        processing_status = 'processing'
        success_status = 'processed'
        
        try:
            logging.info(f"Đang xử lý tập: {title} (ID: {episode_id}, Hash: {text_hash})")
            
            # ĐÁNH DẤU TRẠNG THÁI 'processing'
            update_episode_status(episode_id, processing_status)
            
            
            # --- BƯỚC 2: TẠO KỊCH BẢN DÀI (16:9) & METADATA ---
            logging.info("Bắt đầu tạo kịch bản DÀI (16:9)...")
            script_long_data = generate_full_script(episode)
            if not script_long_data or not script_long_data.get('full_script_txt_path'):
                 raise Exception("LLM thất bại khi tạo kịch bản DÀI hoặc trả về dữ liệu rỗng.")
            logging.info("Tạo kịch bản DÀI thành công.")
            
            
            # --- BƯỚC 3: TẠO KỊCH BẢN NGẮN (Shorts 9:16) (MOCK) ---
            logging.info("Bắt đầu tạo kịch bản NGẮN (Shorts 9:16)...")
            script_short_data = mock_generate_short_script(episode, script_long_data['full_script_txt_path'])
            if not script_short_data or not script_short_data.get('short_script_txt_path'):
                 logging.warning("Không tạo được kịch bản ngắn (Mock). Bỏ qua bước Shorts.")
            logging.info("Tạo kịch bản NGẮN thành công.")
            
            
            # --- BƯỚC 4: TẠO TTS AUDIO DÀI ---
            logging.info("Bắt đầu tạo TTS Audio DÀI...")
            raw_audio_long_path = text_to_speech(script_long_data['full_script_txt_path'], is_short=False)
            if not raw_audio_long_path:
                raise Exception("TTS thất bại khi tạo audio DÀI.")
            logging.info("Tạo TTS Audio DÀI thành công.")

            # --- BƯỚC 5: TRỘN AUDIO DÀI VỚI NHẠC NỀN ---
            logging.info("Bắt đầu trộn Audio DÀI (BGM)...")
            final_audio_long_path = finalize_audio(raw_audio_long_path, is_short=False)
            if not final_audio_long_path:
                raise Exception("Trộn Audio DÀI thất bại.")
            logging.info(f"Hoàn thành trộn Audio DÀI tại: {final_audio_long_path}")

            
            # --- BƯỚC 6: TẠO TTS AUDIO NGẮN (Nếu kịch bản ngắn tồn tại) ---
            raw_audio_short_path = None
            if script_short_data.get('short_script_txt_path'):
                logging.info("Bắt đầu tạo TTS Audio NGẮN...")
                raw_audio_short_path = text_to_speech(script_short_data['short_script_txt_path'], is_short=True)
                if not raw_audio_short_path:
                     logging.warning("TTS thất bại khi tạo audio NGẮN. Bỏ qua bước Shorts.")
                else:
                    logging.info("Tạo TTS Audio NGẮN thành công.")

                    # --- BƯỚC 7: TRỘN AUDIO NGẮN VỚI NHẠC NỀN ---
                    logging.info("Bắt đầu trộn Audio NGẮN (BGM)...")
                    final_audio_short_path = finalize_audio(raw_audio_short_path, is_short=True)
                    if not final_audio_short_path:
                        logging.warning("Trộn Audio NGẮN thất bại. Bỏ qua bước Shorts.")
                    else:
                        logging.info(f"Hoàn thành trộn Audio NGẮN tại: {final_audio_short_path}")
            
            
            # --- BƯỚC 8: CẬP NHẬT TRẠNG THÁI THÀNH CÔNG ---
            update_episode_status(episode_id, success_status)
            
        except Exception as e:
            logging.error(f"PIPELINE THẤT BẠI cho tập ID {episode_id}: {e}", exc_info=True)
            # CẬP NHẬT TRẠNG THÁI 'failed' TRÊN SHEET NẾU CÓ LỖI XẢY RA
            update_episode_status(episode_id, 'failed')
            
        # Tạm dừng 1 giây giữa các lần xử lý tập
        time.sleep(1) 


if __name__ == "__main__":
    run_pipeline()
