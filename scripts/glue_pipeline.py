# scripts/glue_pipeline.py
import logging
import sys
import os

# Setup Path 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 1. IMPORT CÁC MODULE CƠ BẢN VÀ DATA
from utils import setup_environment
from fetch_content import fetch_content, authenticate_google_sheet 
from generate_script import generate_long_script, generate_short_script 
from auto_music_sfx import auto_music_sfx 

# 2. IMPORT MODULE XUẤT BẢN & VIDEO
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
    # KHÓA TẠM THỜI: Giữ nguyên trạng thái khóa để test shorts
    # ====================================================================
    logger.info("🎬 --- LUỒNG VIDEO DÀI (16:9) ĐANG TẠM KHÓA TEST ---")
    
    # # BƯỚC 1: TẠO SCRIPT DÀI (Nhận dictionary chứa path và metadata)
    # long_script_result = generate_long_script(data)
    
    # # BƯỚC 2: TTS Dài & Mix Audio
    # if long_script_result:
    #     script_long = long_script_result['script_path']
    #     metadata_long = long_script_result['metadata'] # Lấy metadata từ AI
        
    #     if script_long:
    #         tts_long = create_tts(script_long, eid, "long")
    #         if tts_long:
    #             audio_final = auto_music_sfx(tts_long, eid) # Thêm nhạc nền và Outro
                
    # # BƯỚC 3: Tạo Video 16:9 & Upload
    #             if audio_final:
    #                 vid_path = create_video(audio_final, eid)
    #                 if vid_path:
    #                     # TRUYỀN METADATA MỚI CHO UPLOAD
    #                     upload_data = {
    #                         # Map key AI (youtube_title) sang key upload_youtube.py (Title)
    #                         'Title': metadata_long.get('youtube_title', data.get('Name')), 
    #                         'Summary': metadata_long.get('youtube_description', 'Mô tả video dài.'),
    #                         'Tags': metadata_long.get('youtube_tags', 'podcast, story, viral')
    #                     }
    #                     upload_video(vid_path, upload_data) # Sử dụng metadata do AI tạo
    # --------------------------------------------------------------------


    # ====================================================================
    # --- LUỒNG SHORTS (9:16) --- (ĐANG HOẠT ĐỘNG VÀ UPLOAD)
    # ====================================================================
    logger.info("📱 --- LUỒNG SHORTS (9:16) ĐANG CHẠY VÀ UPLOAD YOUTUBE ---")
    
    # 1. Generate Script Short (Tạo nội dung và Tiêu đề Hook)
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
            
            # 4. UPLOAD SHORTS (SỬA LỖI KEY MISMATCH)
            if shorts_path:
                
                # --- XÂY DỰNG METADATA CHUẨN CHO SHORTS ---
                # Title: HOOK TITLE + Tên tập + #Shorts
                short_title = f"{hook_title} | {data.get('Name')} #Shorts"
                
                # Summary (Mô tả): Lấy Core Theme và thêm CTA Viral
                short_description = f"🔥 Vén màn bí mật: {data.get('Core Theme', '')}\n\nXem toàn bộ câu chuyện và nhiều huyền thoại khác trên kênh Podcast Theo Dấu Chân Huyền Thoại!\n#shorts #viral #podcast"
                
                # Tags: Lấy Tags mặc định
                short_tags = 'shorts, viral, podcast, storytelling, ' + data.get('Core Theme', '')

                # TẠO DICTIONARY VỚI KEY CHÍNH XÁC
                upload_data = {
                    'Title': short_title, 
                    'Summary': short_description, 
                    'Tags': short_tags 
                }
                
                # Gọi hàm upload
                upload_video(shorts_path, upload_data)

    # 5. Update Sheet: Ghi Status
    update_status_completed(worksheet, row_idx, 'COMPLETED_SHORTS_TEST')
    logger.info("🎉 HOÀN TẤT LUỒNG TEST SHORTS")

if __name__ == "__main__":
    main()
