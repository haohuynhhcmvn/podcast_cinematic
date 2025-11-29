# scripts/glue_pipeline.py
import logging
import sys
import os

# Setup Path (Dùng để import các file ngang hàng)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 1. IMPORT CÁC MODULE CƠ BẢN VÀ DATA
from utils import setup_environment
from fetch_content import fetch_content # Lấy dữ liệu từ Sheet
from generate_script import generate_long_script, generate_short_script # Tạo script
from auto_music_sfx import auto_music_sfx # Trộn nhạc

# 2. IMPORT MODULE XUẤT BẢN & VIDEO
from create_tts import create_tts # Tạo giọng nói
from create_video import create_video # Dựng video 16:9
from create_shorts import create_shorts # Dựng video 9:16 (BẬT)
from upload_youtube import upload_video # Upload YouTube (BẬT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# --- HÀM HỖ TRỢ: CẬP NHẬT TRẠNG THÁI ---
def update_status_completed(worksheet, row_idx, status):
    """Cập nhật trạng thái cuối cùng trên Google Sheet."""
    try:
        # Giả định cột Status là cột 6 (F)
        worksheet.update_cell(row_idx, 6, status) 
        logger.info(f"✅ Đã cập nhật hàng {row_idx}: {status}")
    except Exception as e:
        logger.error(f"❌ Lỗi update sheet: {e}")

# --- HÀM CHÍNH: ORCHESTRATOR ---

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
    # KHÓA TẠM THỜI: Mở lại bằng cách xóa dấu # ở đầu mỗi dòng
    # ====================================================================
    logger.info("🎬 --- LUỒNG VIDEO DÀI (16:9) ĐANG TẠM KHÓA TEST ---")
    
    # # BƯỚC 1: Tạo Script Dài (Gọi AI)
    # script_long = generate_long_script(data)
    
    # # BƯỚC 2: TTS Dài & Mix Audio
    # if script_long:
    #     tts_long = create_tts(script_long, eid, "long")
    #     if tts_long:
    #         audio_final = auto_music_sfx(tts_long, eid) # Thêm nhạc nền và Outro
            
    # # BƯỚC 3: Tạo Video 16:9 & Upload
    #         if audio_final:
    #             vid_path = create_video(audio_final, eid)
    #             if vid_path:
    #                 upload_video(vid_path, data) # Upload Video Dài
    # --------------------------------------------------------------------


    # ====================================================================
    # --- LUỒNG SHORTS (9:16) --- (ĐANG HOẠT ĐỘNG VÀ UPLOAD)
    # ====================================================================
    logger.info("📱 --- LUỒNG SHORTS (9:16) ĐANG CHẠY VÀ UPLOAD YOUTUBE ---")
    
    # 1. Generate Script Short (Tạo nội dung và Tiêu đề Hook)
    result_shorts = generate_short_script(data)
    
    if result_shorts:
        # Hứng 2 giá trị: đường dẫn script và đường dẫn tiêu đề
        script_short_path, title_short_path = result_shorts
        
        # Đọc nội dung Tiêu đề Hook
        try:
            with open(title_short_path, 'r', encoding='utf-8') as f:
                hook_title = f.read().strip()
        except:
            hook_title = ""

        # 2. Tạo TTS cho phần nội dung (Chỉ TTS thô)
        tts_short = create_tts(script_short_path, eid, "short")
        
        if tts_short:
            # 3. TẠO SHORTS: Dựng video 9:16
            shorts_path = create_shorts(tts_short, hook_title, eid)
            
            # 4. UPLOAD SHORTS
            if shorts_path:
                shorts_data = data.copy()
                # Ghi đè Title và thêm tag #Shorts
                shorts_data['Name'] = f"{data.get('Name')} | {hook_title} #Shorts" 
                
                # Gọi hàm upload để đẩy Shorts lên YouTube
                upload_video(shorts_path, shorts_data)

    # 5. Update Sheet: Ghi Status để đánh dấu quá trình test Shorts hoàn tất
    update_status_completed(worksheet, row_idx, 'COMPLETED_SHORTS_TEST')
    logger.info("🎉 HOÀN TẤT LUỒNG TEST SHORTS")

if __name__ == "__main__":
    main()
