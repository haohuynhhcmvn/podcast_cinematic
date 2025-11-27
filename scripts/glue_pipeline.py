# scripts/glue_pipeline.py (ĐÃ SỬA: Thêm Patch PIL.Image.ANTIALIAS)
import sys 
import os
import logging
from dotenv import load_dotenv

# THÊM BƯỚC VÁ LỖI (PATCH) CHO MOVIEPY/PILLOW
# MoviePy cũ sử dụng hằng số PIL.Image.ANTIALIAS đã bị xóa trong Pillow mới.
try:
    from PIL import Image
    # Kiểm tra và gán lại giá trị của LANCZOS cho ANTIALIAS nếu nó không tồn tại
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
        logging.warning("PATCHED: PIL.Image.ANTIALIAS đã được gán lại giá trị LANCZOS.")
except ImportError:
    pass
# KẾT THÚC BƯỚC VÁ LỖI

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

# ... (Phần còn lại của code glue_pipeline.py giữ nguyên)
# ... (Phần còn lại của code glue_pipeline.py giữ nguyên)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def update_status_completed(row_index: int):
# ... (Hàm update_status_completed giữ nguyên)
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
            
        # 2. Generate Script (NHẬN VỀ DICTIONARY)
        script_data = generate_script(episode_data)
        if not script_data: raise Exception("Lỗi generate_script")
        
        # TRÍCH XUẤT CÁC THÔNG TIN CẦN THIẾT
        script_path = script_data['script_path']
        # <<< KHỞI TẠO METADATA YOUTUBE TỪ SCRIPT DATA (CHO VIDEO 16:9 DÀI) >>>
        youtube_metadata = {
            'title': script_data['youtube_title'],
            'description': script_data['youtube_description'],
            'tags': script_data['youtube_tags']
        }
        
        # 3. TTS
        raw_audio_path = create_tts(script_path, episode_id)
        if not raw_audio_path: raise Exception("Lỗi create_tts")

        # 4. Audio Mixing
        final_audio_path = auto_music_sfx(raw_audio_path, episode_id)
        if not final_audio_path: raise Exception("Lỗi auto_music_sfx")

        # 5. Subtitles (BỎ QUA)
        logging.info("BỎ QUA BƯỚC TẠO PHỤ ĐỀ ĐỂ HOÀN THÀNH PIPELINE.")
        # subtitle_path = create_subtitle(final_audio_path, script_path, episode_id) 
        # if not subtitle_path: raise Exception("Lỗi create_subtitle")
        subtitle_path = "SKIP_SUBTITLE" # Đặt một giá trị giả

        # 6. Create Video 16:9
        video_169_path = create_video(final_audio_path, subtitle_path, episode_id)
        if not video_169_path: raise Exception("Lỗi create_video")

        # 7. Create Shorts (NHẬN VỀ ĐƯỜNG DẪN)
        shorts_path = None
        try:
            shorts_path = create_shorts(final_audio_path, subtitle_path, episode_id)
        except Exception as e:
            logging.warning(f"Bỏ qua Shorts do lỗi: {e}")
            
        # 8. Upload YouTube
        
        # 8a. TẠO METADATA RIÊNG CHO SHORTS (Thêm #shorts)
        shorts_metadata = youtube_metadata.copy()
        # Thêm tiền tố và hashtag #shorts vào tiêu đề/mô tả
        shorts_metadata['title'] = "🔥SHORTS | " + shorts_metadata['title']
        # Thêm các hashtag phổ biến vào mô tả để YouTube dễ dàng nhận diện Shorts
        shorts_metadata['description'] = shorts_metadata['description'] + "\n\n#shorts #podcast #vietnam" 
        
        upload_status = 'SKIPPED' # Trạng thái upload 16:9
        shorts_upload_status = 'SKIPPED' # Trạng thái upload Shorts
        
        # Bắt đầu Upload Video 16:9 (Podcast dài)
        logging.info("Bắt đầu upload Video 16:9 (Podcast dài)...")
        upload_status = upload_video(video_169_path, episode_data, youtube_metadata) 
        logging.info(f"Kết quả Upload 16:9: {upload_status}")
        
        # Bắt đầu Upload Video Shorts
        if shorts_path:
             logging.info("Bắt đầu upload Video Shorts 9:16...")
             shorts_upload_status = upload_video(shorts_path, episode_data, shorts_metadata)
             logging.info(f"Kết quả Upload Shorts: {shorts_upload_status}")

        # 9. Update Status
        if episode_data.get('Status_Row') and (upload_status == 'UPLOADED' or shorts_upload_status == 'UPLOADED'):
             update_status_completed(episode_data['Status_Row'])

    except Exception as e:
        logging.error(f"PIPELINE FAILED: {e}", exc_info=True)
        sys.exit(1)

    finally:
        logging.info("=== KẾT THÚC QUY TRÌNH ===")

if __name__ == '__main__':
    main_pipeline()
