# scripts/glue_pipeline.py
import logging
import sys
import os

# Setup Path (Dùng để import các file ngang hàng)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import setup_environment
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_short_script
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from auto_music_sfx import auto_music_sfx
from upload_youtube import upload_video

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# --- BỔ SUNG: HÀM CẬP NHẬT STATUS (TỪ FETCH_CONTENT) ---
# Cần phải import hàm này hoặc tái tạo nó để cập nhật trạng thái sau khi xử lý xong
# (Giả định fetch_content đã trả về 'worksheet' và 'row_idx')
def update_status_completed(worksheet, row_idx, status):
    """Cập nhật trạng thái cuối cùng trên Google Sheet."""
    try:
        # Giả định cột Status là cột 6 (F)
        worksheet.update_cell(row_idx, 6, status) 
        logger.info(f"✅ Đã cập nhật hàng {row_idx}: {status}")
    except Exception as e:
        logger.error(f"❌ Lỗi update sheet: {e}")

# --- HÀM CHÍNH ---

def main():
    setup_environment()
    
    # 1. Fetch Dữ liệu từ Google Sheet
    task = fetch_content()
    if not task: return
    
    data = task['data']
    eid = data['ID']
    row_idx = task['row_idx']
    worksheet = task['worksheet']

    # ====================================================================
    # --- LUỒNG VIDEO DÀI (16:9) ---
    # TẠM KHÓA: Mở lại bằng cách xóa dấu # ở đầu mỗi dòng
    # ====================================================================
    logger.info("🎬 --- LUỒNG VIDEO DÀI (16:9) ĐANG TẠM KHÓA TEST ---")
    
    # # BƯỚC 1: Tạo Script Dài
    # script_long = generate_long_script(data)
    
    # # BƯỚC 2: TTS Dài & Mix Audio
    # if script_long:
    #     tts_long = create_tts(script_long, eid, "long")
    #     if tts_long:
    #         audio_final = auto_music_sfx(tts_long, eid)
            
    # # BƯỚC 3: Tạo Video 16:9 & Upload
    #         if audio_final:
    #             vid_path = create_video(audio_final, eid)
    #             if vid_path:
    #                 upload_video(vid_path, data)
    # --------------------------------------------------------------------


    # ====================================================================
    # --- LUỒNG SHORTS (9:16) --- (ĐANG HOẠT ĐỘNG)
    # ====================================================================
    logger.info("📱 --- LUỒNG SHORTS (9:16) ĐANG CHẠY TEST ---")
    
    # 1. Generate Script Short (Trả về Script và Title Hook)
    result_shorts = generate_short_script(data)
    
    if result_shorts:
        script_short_path, title_short_path = result_shorts
        
        # Đọc nội dung Tiêu đề Hook từ file (cần cho TextClip)
        try:
            with open(title_short_path, 'r', encoding='utf-8') as f:
                hook_title = f.read().strip()
        except:
            hook_title = ""

        # 2. Tạo TTS cho phần nội dung (Chỉ TTS thô)
        tts_short = create_tts(script_short_path, eid, "short")
        
        if tts_short:
            # 3. Tạo Shorts (Có nhạc nền và Title động)
            shorts_path = create_shorts(tts_short, hook_title, eid)
            
            # 4. Upload Shorts (Nếu có file)
            if shorts_path:
                shorts_data = data.copy()
                # Thêm #Shorts vào tiêu đề
                shorts_data['Name'] = f"{data.get('Name')} | {hook_title} #Shorts" 
                
                # Hàm upload_video() sẽ tự xử lý việc upload lên YouTube
                upload_video(shorts_path, shorts_data)

    # 5. Update Sheet: Ghi Status khác để dễ dàng lọc kết quả test
    update_status_completed(worksheet, row_idx, 'COMPLETED_SHORTS_TEST')
    logger.info("🎉 HOÀN TẤT LUỒNG TEST SHORTS")

if __name__ == "__main__":
    main()
