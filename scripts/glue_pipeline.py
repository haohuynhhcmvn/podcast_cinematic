# === scripts/glue_pipeline.py ===
import logging
import sys
import os
from time import sleep
from concurrent.futures import ThreadPoolExecutor

# Đảm bảo đường dẫn hệ thống
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils import setup_environment, get_path, cleanup_temp_files 
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_short_script
from auto_music_sfx import auto_music_sfx
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video
from generate_image import generate_character_image
from create_thumbnail import add_text_to_thumbnail

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =========================================================
# 📊 HÀM CẬP NHẬT TRẠNG THÁI (BACK FROM OLD VERSION)
# =========================================================
def safe_update_status(ws, row_idx, status):
    """Cập nhật cột Status trên Google Sheets để theo dõi realtime"""
    try:
        if not ws: return
        header = ws.row_values(1)
        if "Status" in header:
            col_idx = header.index("Status") + 1
            ws.update_cell(row_idx, col_idx, status)
            logger.info(f"📊 SHEET_UPDATE: Row {row_idx} -> {status}")
    except Exception as e:
        logger.error(f"❌ Lỗi update status: {e}")

# =========================================================
# 🚀 GIAI ĐOẠN 1: CHUẨN BỊ NGUYÊN LIỆU SONG SONG
# =========================================================
def prepare_assets_parallel(data, episode_id, ws, row_idx):
    logger.info("⚡ Đang chuẩn bị kịch bản, giọng đọc và hình ảnh SONG SONG...")
    safe_update_status(ws, row_idx, "PROCESSING: Assets Generation")
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        # 1. Tạo kịch bản cùng lúc
        f_long_script = executor.submit(generate_long_script, data)
        f_short_script = executor.submit(generate_short_script, data)
        
        long_res = f_long_script.result()
        short_res = f_short_script.result()

        if not long_res or not short_res:
            return None

        # 2. Tạo TTS và Ảnh nhân vật đồng thời
        f_tts_long = executor.submit(create_tts, long_res["script_path"], episode_id, "long")
        f_tts_short = executor.submit(create_tts, short_res[0], episode_id, "short")
        
        raw_img_path = get_path("assets", "temp", f"{episode_id}_raw_ai.png")
        f_image = executor.submit(generate_character_image, data['Name'], raw_img_path)

        return {
            "long_script_path": long_res["script_path"],
            "long_meta": long_res.get("metadata", {}),
            "short_script_path": short_res[0],
            "short_title_path": short_res[1],
            "long_audio": f_tts_long.result(),
            "short_audio": f_tts_short.result(),
            "character_image": f_image.result()
        }

# =========================================================
# 🎬 GIAI ĐOẠN 2: XỬ LÝ CHÍNH (MAIN PROCESS)
# =========================================================
def process_task(data, task_meta):
    eid = str(data.get('ID'))
    row_idx = task_meta['row_idx']
    ws = task_meta['worksheet']
    
    try:
        # BƯỚC 1: Chuẩn bị nguyên liệu
        assets = prepare_assets_parallel(data, eid, ws, row_idx)
        if not assets or not assets["long_audio"]:
            safe_update_status(ws, row_idx, "FAILED: Assets")
            return False

        # BƯỚC 2: Audio Mix
        safe_update_status(ws, row_idx, "PROCESSING: Audio Mixing")
        mixed_long_audio = auto_music_sfx(assets["long_audio"], eid)

        # BƯỚC 3: RENDER VIDEO LONG (FPS 12, CRF 32)
        safe_update_status(ws, row_idx, "PROCESSING: Rendering Long Video")
        youtube_title = assets["long_meta"].get("youtube_title", f"{data['Name']} Story")
        video_long_path = create_video(mixed_long_audio, eid, assets["character_image"], youtube_title)

        # BƯỚC 4: THUMBNAIL
        thumb_out = get_path("outputs", "thumbnails", f"{eid}_thumb.jpg")
        add_text_to_thumbnail(assets["character_image"], youtube_title, thumb_out)

        # BƯỚC 5: RENDER SHORTS
        safe_update_status(ws, row_idx, "PROCESSING: Rendering Shorts")
        with open(assets["short_title_path"], "r", encoding="utf-8") as f:
            hook_title = f.read().strip()
        video_short_path = create_shorts(assets["short_audio"], hook_title, eid, data['Name'], assets["short_script_path"], assets["character_image"])

        # BƯỚC 6: UPLOAD
        safe_update_status(ws, row_idx, "PROCESSING: Uploading to YouTube")
        if video_long_path:
            upload_video(video_long_path, {"Title": youtube_title}, thumbnail_path=thumb_out)
        if video_short_path:
            upload_video(video_short_path, {"Title": f"{hook_title} #Shorts"})

        # BƯỚC 7: HOÀN THÀNH
        safe_update_status(ws, row_idx, "DONE: Uploaded All")
        cleanup_temp_files(eid, data.get("text_hash"))
        return True

    except Exception as e:
        logger.error(f"❌ Lỗi Pipeline: {e}")
        safe_update_status(ws, row_idx, f"ERROR: {str(e)[:50]}")
        return False

def main():
    setup_environment()
    task = fetch_content()
    if task:
        process_task(task["data"], {"row_idx": task["row_idx"], "worksheet": task["worksheet"]})

if __name__ == "__main__":
    main()
