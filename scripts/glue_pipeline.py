import os
import logging
from dotenv import load_dotenv
import gspread # Cần import gspread để cập nhật trạng thái cuối cùng

# Import TẤT CẢ các hàm
from fetch_content import fetch_content, authenticate_google_sheet
from generate_script import generate_script
from create_tts import create_tts
from auto_music_sfx import auto_music_sfx
from create_subtitle import create_subtitle
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_youtube
from utils import setup_environment

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_status_completed(row_index: int):
    """Cập nhật trạng thái trong Google Sheet thành 'COMPLETED'."""
    try:
        gc = authenticate_google_sheet()
        sheet_id = os.getenv('GOOGLE_SHEET_ID')
        if not gc or not sheet_id: return False

        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0)
        
        # Giả định cột Status là cột thứ 6 (F)
        worksheet.update_cell(row_index, 6, 'COMPLETED') 
        logging.info(f"Đã cập nhật trạng thái hàng {row_index} thành 'COMPLETED'.")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi cập nhật trạng thái COMPLETED: {e}")
        return False


def main_pipeline():
    logging.info("--- BẮT ĐẦU QUY TRÌNH TẠO PODCAST TỰ ĐỘNG ---")

    load_dotenv()
    setup_environment() 
    episode_data = None
    
    try:
        episode_data = fetch_content()
        if not episode_data:
            logging.info("Không có tập mới nào trong Google Sheet để xử lý. Kết thúc.")
            return

        episode_id = episode_data['ID']
        
        # Thực hiện các bước (tôi lược bớt log để giữ ngắn gọn)
        script_path = generate_script(episode_data); 
        if not script_path: raise Exception("Failed at generate_script")

        raw_audio_path = create_tts(script_path, episode_id); 
        if not raw_audio_path: raise Exception("Failed at create_tts")

        final_audio_path = auto_music_sfx(raw_audio_path, episode_id); 
        if not final_audio_path: raise Exception("Failed at auto_music_sfx")

        subtitle_path = create_subtitle(final_audio_path, script_path, episode_id); 
        if not subtitle_path: raise Exception("Failed at create_subtitle")

        video_169_path = create_video(final_audio_path, subtitle_path, episode_id);
        if not video_169_path: raise Exception("Failed at create_video")

        video_916_path = create_shorts(final_audio_path, subtitle_path, episode_id);
        if not video_916_path: raise Exception("Failed at create_shorts")

        upload_status = upload_youtube(video_169_path, episode_data)
        logging.info(f"Trạng thái Upload lên YouTube: {upload_status}")
        
        # Bước hoàn tất: Cập nhật trạng thái
        if episode_data.get('Status_Row'):
            update_status_completed(episode_data['Status_Row'])


    except Exception as e:
        logging.error(f"QUY TRÌNH GẶP LỖI: {e}", exc_info=True)
        # Bổ sung: Cập nhật trạng thái lỗi nếu cần thiết
        if episode_data and episode_data.get('Status_Row'):
             # Tùy chọn: update_status_error(episode_data['Status_Row']) 
             pass
    finally:
        logging.info("--- KẾT THÚC QUY TRÌNH TẠO PODCAST TỰ ĐỘNG ---")


if __name__ == '__main__':
    main_pipeline()
