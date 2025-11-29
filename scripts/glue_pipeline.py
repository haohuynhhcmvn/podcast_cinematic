# scripts/glue_pipeline.py
import sys 
import os
import logging
from dotenv import load_dotenv

# Thiết lập đường dẫn import
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import Modules
from create_video import create_video
from upload_youtube import upload_video 
from fetch_content import fetch_content, authenticate_google_sheet
from generate_script import generate_script
from create_tts import create_tts
from auto_music_sfx import auto_music_sfx
from create_subtitle import create_subtitle
from create_shorts import create_shorts
from utils import setup_environment

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_status_completed(row_index: int):
    """Hàm cập nhật trạng thái sử dụng lại logic xác thực của fetch_content"""
    try:
        gc = authenticate_google_sheet()
        sheet_id = os.getenv('GOOGLE_SHEET_ID')
        if not gc or not sheet_id: return False

        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0)
        # Update cột F (cột 6) thành COMPLETED
        worksheet.update_cell(row_index, 6, 'COMPLETED') 
        logging.info(f"Đã cập nhật hàng {row_index}: COMPLETED")
        return True
    except Exception as e:
        logging.error(f"Lỗi update sheet: {e}")
        return False

def main_pipeline():
    logging.info("=== BẮT ĐẦU PIPELINE ===")
    load_dotenv()
    setup_environment() 
    
    try:
        # 1. Lấy dữ liệu
        episode_data = fetch_content()
        if not episode_data:
            logging.info("Không có dữ liệu mới.")
            return

        episode_id = episode_data['ID']
        logging.info(f"Đang xử lý Episode ID: {episode_id}")
        
        logging.info("Sử dụng ảnh nền và micro tĩnh từ assets/images/")
             
        # 2. Generate Script
        script_path = generate_script(episode_data)
        if not script_path: raise Exception("Lỗi generate_script")

        # 3. TTS
        raw_audio_path = create_tts(script_path, episode_id)
        if not raw_audio_path: raise Exception("Lỗi create_tts")

        # 4. Audio Mixing
        final_audio_path = auto_music_sfx(raw_audio_path, episode_id)
        if not final_audio_path: raise Exception("Lỗi auto_music_sfx")

        # 5. Subtitles
        subtitle_path = create_subtitle(final_audio_path, script_path, episode_id)
        # (Subtitle có thể None nếu tắt tính năng, không cần raise Exception)

        # 6. Create Video 16:9
        video_169_path = create_video(final_audio_path, subtitle_path, episode_id)
        if not video_169_path: raise Exception("Lỗi create_video")

        # 7. Create Shorts
        shorts_path = None
        try:
            # Hứng lấy đường dẫn file shorts trả về
            shorts_path = create_shorts(final_audio_path, subtitle_path, episode_id)
        except Exception as e:
            logging.warning(f"Bỏ qua Shorts do lỗi: {e}")

        # 8. Upload YouTube (Video 16:9)
        logging.info("--> Bắt đầu upload Video 16:9...")
        upload_status_169 = upload_video(video_169_path, episode_data)
        logging.info(f"Kết quả Upload 16:9: {upload_status_169}")
        
        # 9. Upload YouTube (Shorts) - MỚI THÊM
        upload_status_shorts = "SKIPPED"
        if shorts_path and os.path.exists(shorts_path):
            logging.info("--> Bắt đầu upload Video Shorts...")
            
            # Tạo metadata riêng cho Shorts (Thêm tag #Shorts vào tiêu đề)
            shorts_data = episode_data.copy()
            original_title = shorts_data.get('Title', shorts_data.get('Name', 'Shorts'))
            shorts_data['Name'] = f"{original_title} #Shorts"
            
            # Gọi hàm upload lần 2
            upload_status_shorts = upload_video(shorts_path, shorts_data)
            logging.info(f"Kết quả Upload Shorts: {upload_status_shorts}")
        else:
            logging.warning("Không tìm thấy file Shorts để upload.")

        # 10. Update Status
        # Chỉ cần Video chính (16:9) lên thành công là coi như task hoàn thành
        if episode_data.get('Status_Row') and upload_status_169 == 'UPLOADED':
            update_status_completed(episode_data['Status_Row'])

    except Exception as e:
        logging.error(f"PIPELINE FAILED: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logging.info("=== KẾT THÚC QUY TRÌNH ===")

if __name__ == '__main__':
    main_pipeline()
