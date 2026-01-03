# === scripts/glue_pipeline.py ===

import logging
import sys
import os
from time import sleep
from datetime import datetime, timedelta # <--- Import thư viện thời gian

# Đảm bảo Python tìm thấy các module trong thư mục scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import các module chức năng
from utils import setup_environment, get_path, cleanup_temp_files
from fetch_content import fetch_content
from generate_script import generate_long_script, split_long_script_to_5_shorts
from auto_music_sfx import auto_music_sfx
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video

# Import module xử lý hình ảnh
try:
    from generate_image import generate_character_image
    from create_thumbnail import add_text_to_thumbnail
except ImportError:
    logging.warning("⚠️ Module tạo ảnh/thumbnail chưa được cài đặt đầy đủ.")
    generate_character_image = None
    add_text_to_thumbnail = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =========================================================
#  HÀM HỖ TRỢ CẬP NHẬT TRẠNG THÁI GOOGLE SHEET
# =========================================================
def safe_update_status(ws, row_idx, col_idx, status):
    """Cập nhật trạng thái lên Sheet một cách an toàn."""
    try:
        if not ws: return
        if col_idx and isinstance(col_idx, int):
            ws.update_cell(row_idx, col_idx, status)
    except Exception as e:
        logger.warning(f"⚠️ Không thể cập nhật Google Sheet: {e}")


# =========================================================
#  XỬ LÝ TỪNG VIDEO SHORTS (TUẦN TỰ + HẸN GIỜ)
# =========================================================
def process_one_short_sequential(short_cfg, data, background_image_path, publish_time):
    """
    Xử lý 1 video short và upload với chế độ hẹn giờ (Scheduled).
    """
    idx = short_cfg["index"]
    logger.info(f"▶️ [SHORT {idx}/5] Đang xử lý...")

    try:
        # 1. Đọc nội dung script và tiêu đề
        script_content = open(short_cfg["script"], encoding="utf-8").read().strip()
        title_content = open(short_cfg["title"], encoding="utf-8").read().strip()

        # 2. Tạo giọng đọc (TTS)
        tts_audio = create_tts(short_cfg["script"], data["ID"], f"short_{idx}")
        if not tts_audio:
            logger.error(f"❌ Short {idx}: Lỗi tạo TTS.")
            return False

        # 3. Dựng Video (Dọc 9:16)
        video_path = create_shorts(
            audio_path=tts_audio,
            text_script=script_content, 
            episode_id=f"{data['ID']}_{idx}",
            character_name=data["Name"],
            hook_title=title_content,
            custom_image_path=background_image_path 
        )

        if not video_path:
            logger.error(f"❌ Short {idx}: Lỗi dựng video.")
            return False

        # 4. Upload lên YouTube (HẸN GIỜ)
        upload_meta = {
            "Title": f"{title_content} #Shorts",
            "Summary": f"Subscribe for more history facts about {data['Name']}!\n\n#shorts #history #facts",
            "Tags": ["shorts", "history", "facts", "education"]
        }
        
        logger.info(f"📅 Short {idx} sẽ công chiếu lúc: {publish_time} (Server Time)")
        
        # Gọi hàm upload với tham số publish_at
        result = upload_video(video_path, upload_meta, publish_at=publish_time)
        
        if result == "FAILED":
            logger.error(f"❌ Short {idx}: Upload thất bại.")
            return False
            
        logger.info(f"✅ [SHORT {idx}/5] ĐÃ LÊN LỊCH THÀNH CÔNG!")
        return True

    except Exception as e:
        logger.error(f"❌ Short {idx} Crash: {e}", exc_info=True)
        return False


# =========================================================
#  LUỒNG CHÍNH (MAIN PIPELINE)
# =========================================================
def main():
    setup_environment()
    
    # 1. Lấy nhiệm vụ từ Google Sheet
    task = fetch_content()
    if not task:
        logger.info("💤 Không có nhiệm vụ 'pending'. Hệ thống nghỉ.")
        return

    data = task["data"]
    row_idx = task["row_idx"]
    col_idx = task["col_idx"]
    ws = task["worksheet"]
    
    # Ép kiểu ID sang chuỗi để an toàn
    eid = str(data.get('ID'))
    text_hash = data.get("text_hash")

    logger.info(f"🚀 BẮT ĐẦU TASK ID={eid} | Name={data.get('Name')}")
    safe_update_status(ws, row_idx, col_idx, 'PROCESSING')

    # =====================================================
    # 🕒 TÍNH TOÁN LỊCH TRÌNH CÔNG CHIẾU (SCHEDULING)
    # =====================================================
    now = datetime.now()
    # Mốc bắt đầu: 2 tiếng kể từ bây giờ
    start_schedule_time = now + timedelta(hours=2)
    
    logger.info(f"⏰ THỜI GIAN SERVER HIỆN TẠI: {now}")
    logger.info(f"⏰ LỊCH CÔNG CHIẾU BẮT ĐẦU LÚC: {start_schedule_time}")

    try:
        # =========================================================
        # GIAI ĐOẠN 1: TẠO ASSETS (ẢNH & SCRIPT)
        # =========================================================
        
        # 1.1 Tạo ảnh minh họa (DALL-E 3)
        img_path = None
        if generate_character_image:
            img_path = generate_character_image(data.get("Name"), eid)
        else:
            logger.warning("⚠️ Bỏ qua bước tạo ảnh (Module thiếu).")

        # 1.2 Tạo kịch bản chi tiết (Long Script)
        logger.info("📝 Đang viết kịch bản chi tiết...")
        long_res = generate_long_script(data)
        if not long_res:
            raise Exception("Lỗi tạo kịch bản.")

        # =========================================================
        # GIAI ĐOẠN 2: XỬ LÝ VIDEO DÀI (HẸN GIỜ: T + 2H)
        # =========================================================
        logger.info("🎬 === BẮT ĐẦU XỬ LÝ VIDEO DÀI ===")

        # 2.1 Tạo giọng đọc
        logger.info("🔊 Đang tạo giọng đọc (TTS)...")
        long_audio_path = create_tts(long_res["script_path"], eid, "long")
        
        if long_audio_path:
            # 2.2 Ghép nhạc nền
            logger.info("🎵 Đang phối nhạc nền...")
            final_audio_path = auto_music_sfx(long_audio_path, eid)
            
            # 2.3 Dựng Video
            logger.info("🎥 Đang Render Video...")
            long_video_path = create_video(
                audio_path=final_audio_path, 
                episode_id=eid,
                image_path=img_path, 
                title_text=data.get("Name")
            )

            # 2.4 Tạo Thumbnail
            thumb_path = None
            if add_text_to_thumbnail and img_path:
                thumb_path = get_path("outputs", "thumbnails", f"{eid}_thumb.jpg")
                add_text_to_thumbnail(img_path, data.get("Name").upper(), thumb_path)

            # 2.5 Upload Video Dài (HẸN GIỜ)
            if long_video_path and os.path.exists(long_video_path):
                logger.info(f"📅 Long Video sẽ công chiếu lúc: {start_schedule_time}")
                
                upload_video(
                    long_video_path, 
                    long_res["metadata"], 
                    thumbnail_path=thumb_path,
                    publish_at=start_schedule_time # <--- TRUYỀN THỜI GIAN VÀO
                )
                logger.info("✅ VIDEO DÀI ĐÃ LÊN LỊCH.")
            else:
                logger.error("❌ Lỗi: Không tìm thấy file video dài để upload.")
        else:
            logger.error("❌ Lỗi: Không tạo được TTS cho video dài.")

        # =========================================================
        # GIAI ĐOẠN 3: XỬ LÝ SHORTS (HẸN GIỜ: +2H, +6H, +10H...)
        # =========================================================
        logger.info("📱 === BẮT ĐẦU XỬ LÝ 5 SHORTS ===")
        
        shorts_list = split_long_script_to_5_shorts(data, long_res["script_path"])
        
        if shorts_list:
            success_count = 0
            
            for i, short_cfg in enumerate(shorts_list):
                # Tính toán thời gian cho từng Short
                # Short 1 (i=0): start_time + 0 (Tức là T+2h, cùng lúc Video dài)
                # Short 2 (i=1): start_time + 4h
                # Short 3 (i=2): start_time + 8h
                # ...
                hours_offset = i * 22
                short_publish_time = start_schedule_time + timedelta(hours=hours_offset)
                
                # Gọi hàm xử lý (truyền thêm tham số thời gian)
                result = process_one_short_sequential(short_cfg, data, img_path, short_publish_time)
                
                if result: 
                    success_count += 1
                
                logger.info("⏳ Nghỉ 5 giây để hồi phục tài nguyên...")
                sleep(5)
            
            logger.info(f"✅ Hoàn thành và Lên lịch cho {success_count}/5 Shorts.")
        else:
            logger.error("❌ Không thể cắt kịch bản Shorts.")

        # =========================================================
        # KẾT THÚC
        # =========================================================
        safe_update_status(ws, row_idx, col_idx, 'DONE')
        
        logger.info("🧹 Đang dọn dẹp file tạm...")
        cleanup_temp_files(eid, text_hash)
        
        logger.info("🎉 QUY TRÌNH HOÀN TẤT! 🎉")

    except Exception as e:
        logger.error(f"❌ LỖI NGHIÊM TRỌNG TRONG PIPELINE: {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'FAILED')

if __name__ == "__main__":
    main()
