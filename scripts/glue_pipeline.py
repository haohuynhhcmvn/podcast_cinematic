# scripts/glue_pipeline.py
import logging
import sys
import os

# Thiết lập đường dẫn import
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# --- 1. IMPORT CÁC MODULE CHÍNH ---
# Tên hàm và tên file trùng nhau (Pythonic), nhưng cần đảm bảo file fetch_content.py
# không có lỗi cú pháp nào ngăn cản việc import.

from utils import setup_environment
from fetch_content import fetch_content, authenticate_google_sheet 
from generate_script import generate_long_script, generate_short_script 
from auto_music_sfx import auto_music_sfx 

from create_tts import create_tts 
from create_video import create_video 
from create_shorts import create_shorts 
from upload_youtube import upload_video 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# --- HÀM HỖ TRỢ: CẬP NHẬT TRẠNG THÁI ---
def update_status_completed(worksheet, row_idx, status):
    """Cập nhật trạng thái cuối cùng trên Google Sheet."""
    try:
        worksheet.update_cell(row_idx, 6, status) 
        logger.info(f"✅ Đã cập nhật hàng {row_idx}: {status}")
    except Exception as e:
        logger.error(f"❌ Lỗi update sheet: {e}")

# --- HÀM CHÍNH: ORCHESTRATOR ---

def main(): # Đảm bảo tên hàm là main để chạy đúng lệnh 'python scripts/glue_pipeline.py'
    setup_environment()
    
    # 1. Fetch Dữ liệu từ Google Sheet (LỖI ĐÃ XẢY RA TẠI ĐÂY)
    task = fetch_content() # Hàm này đã được import ở trên
    if not task: return
    
    data = task['data']
    eid = data['ID']
    row_idx = task['row_idx']
    worksheet = task['worksheet']

    # ... [Luồng Video Dài bị khóa] ...

    # ====================================================================
    # --- LUỒNG SHORTS (9:16) --- (ĐANG HOẠT ĐỘNG VÀ UPLOAD)
    # ====================================================================
    logger.info("📱 --- LUỒNG SHORTS (9:16) ĐANG CHẠY VÀ UPLOAD YOUTUBE ---")
    
    # 1. Generate Script Short
    result_shorts = generate_short_script(data)
    
    if result_shorts:
        script_short_path, title_short_path = result_shorts
        
        # Đọc nội dung Tiêu đề Hook
        try:
            with open(title_short_path, 'r', encoding='utf-8') as f:
                hook_title = f.read().strip()
        except:
            hook_title = ""

        # 2. Tạo TTS cho phần nội dung
        tts_short = create_tts(script_short_path, eid, "short")
        
        if tts_short:
            # 3. TẠO SHORTS: Dựng video 9:16
            shorts_path = create_shorts(tts_short, hook_title, eid)
            
            # 4. UPLOAD SHORTS
            if shorts_path:
                
                # --- XÂY DỰNG METADATA CHUẨN ---
                short_title = f"{hook_title} | {data.get('Name')} #Shorts"
                short_description = f"🔥 Vén màn bí mật: {data.get('Core Theme', 'Huyền thoại')}\n\n{data.get('Content/Input', 'Video Shorts hấp dẫn, xem ngay!')}\n\nXem toàn bộ câu chuyện và nhiều huyền thoại khác trên kênh Podcast Theo Dấu Chân Huyền Thoại!\n#shorts #viral #podcast"
                short_tags = 'shorts, viral, podcast, storytelling, ' + data.get('Core Theme', '')

                # TẠO DICTIONARY VỚI KEY CHÍNH XÁC: Title, Summary, Tags
                upload_data = {
                    'Title': short_title, 
                    'Summary': short_description, 
                    'Tags': short_tags 
                }
                
                upload_video(shorts_path, upload_data)

    # 5. Update Sheet
    update_status_completed(worksheet, row_idx, 'COMPLETED_SHORTS_TEST')
    logger.info("🎉 HOÀN TẤT LUỒNG TEST SHORTS")

if __name__ == "__main__":
    main() # Gọi hàm main khi chạy script
