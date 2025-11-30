# scripts/glue_pipeline.py
import logging
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

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

def update_status_completed(worksheet, row_idx, status):
    try:
        worksheet.update_cell(row_idx, 6, status)
        logger.info(f"✅ Đã cập nhật hàng {row_idx}: {status}")
    except Exception as e:
        logger.error(f"❌ Lỗi update sheet: {e}")

def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("Không có dữ liệu mới.")
        return

    data = task['data']
    eid = data['ID']
    row_idx = task['row_idx']
    worksheet = task['worksheet']

    logger.info("📱 --- LUỒNG SHORTS (9:16) ĐANG CHẠY ---")
    result_shorts = generate_short_script(data)

    if result_shorts:
        script_short_path, title_short_path = result_shorts

        try:
            with open(title_short_path, 'r', encoding='utf-8') as f:
                hook_title = f.read().strip()
        except:
            hook_title = ""

        tts_short = create_tts(script_short_path, eid, "short")

        if tts_short:
            shorts_path = create_shorts(tts_short, hook_title, eid, data['Name'])

            if shorts_path:
                short_title = f"{hook_title} – {data.get('Name')} | Bí mật chưa từng kể #Shorts"
                short_description = (
                    f"⚠️ Câu chuyện bạn sắp nghe có thể thay đổi góc nhìn về {data.get('Name')}.\n"
                    f"🔥 Chủ đề: {data.get('Core Theme', 'Huyền thoại – Bí mật chưa kể')}\n\n"
                    f"{data.get('Content/Input', 'Một lát cắt ngắn từ lịch sử – nghe hết để hiểu!')}\n\n"
                    "👉 Nếu phần này làm bạn nổi da gà — HÃY FOLLOW KÊNH NGAY!\n"
                    "📌 Xem full story dài ngay trên channel.\n"
                    "#shorts #podcast #viral #legendary #storytelling"
                )
                short_tags = [
                    "shorts", "viral", "podcast", "storytelling",
                    data.get("Core Theme", ""), data.get("Name", ""),
                    "history", "legend", "mysterious", "cinematic"
                ]
                upload_data = {'Title': short_title, 'Summary': short_description, 'Tags': short_tags}
                upload_video(shorts_path, upload_data)

    update_status_completed(worksheet, row_idx, 'COMPLETED_SHORTS_TEST')
    logger.info("🎉 HOÀN TẤT LUỒNG TEST SHORTS")

if __name__ == "__main__":
    main()
