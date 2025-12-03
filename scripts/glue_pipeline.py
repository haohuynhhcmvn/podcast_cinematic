#=== script/glue_pipeline.py==

import logging
import sys
import os
from time import sleep

# ensure project scripts folder is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils import setup_environment, get_path
from fetch_content import fetch_content
from generate_script import generate_long_script, generate_short_script
from auto_music_sfx import auto_music_sfx
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =========================================================
#  SAFE UPDATE STATUS
# =========================================================
def safe_update_status(ws, row_idx, col_idx, status):
    try:
        if not ws:
            logger.warning("Không có worksheet để update status.")
            return
        if col_idx and isinstance(col_idx, int):
            ws.update_cell(row_idx, col_idx, status)
        else:
            header = ws.row_values(1)
            idx = header.index("Status") + 1 if "Status" in header else 6
            ws.update_cell(row_idx, idx, status)
        logger.info(f"Đã cập nhật row {row_idx} -> {status}")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật status: {e}")


def try_update_youtube_id(ws, row_idx, video_id):
    if not ws or not video_id:
        return
    try:
        header = ws.row_values(1)
        cols = ['YouTubeID', 'VideoID', 'youtube_id', 'video_id']
        for name in cols:
            if name in header:
                col = header.index(name) + 1
                ws.update_cell(row_idx, col, video_id)
                logger.info(f"Ghi YouTube ID vào cột {name}")
                return
    except Exception:
        pass


# =========================================================
#  FULL VIDEO PROCESSING (LONG)
# =========================================================
def process_long_video(data, task_meta):
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')

    eid = data.get('ID')
    name = data.get('Name')

    logger.info(f"🎬 BẮT ĐẦU VIDEO DÀI: {eid} – {name}")

    try:
        # 1) Generate Script Long
        long_res = generate_long_script(data)
        if not long_res:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_GEN_LONG')
            return False

        script_path = long_res["script_path"]
        meta = long_res.get("metadata", {})

        youtube_title = meta.get("youtube_title", f"{name} – The Untold Story")
        youtube_description = meta.get("youtube_description", "")
        yt_tags = meta.get("youtube_tags", "")
        youtube_tags = yt_tags.split(",") if isinstance(yt_tags, str) else yt_tags

        # 2) TTS Long
        tts = None
        for i in range(3):
            tts = create_tts(script_path, eid, "long")
            if tts:
                break
            logger.warning(f"TTS long attempt {i+1} failed.")
            sleep(2)
        if not tts:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_TTS_LONG')
            return False

        # 3) Mix audio
        mixed = auto_music_sfx(tts, eid)
        if not mixed:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_MIX_LONG')
            return False

        # 4) Make full video
        video_path = create_video(mixed, eid)
        if not video_path:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_RENDER_LONG')
            return False

        # 5) Upload YouTube
        upload_payload = {
            "Title": youtube_title,
            "Summary": youtube_description,
            "Tags": youtube_tags
        }

        upload_result = None
        for i in range(2):
            upload_result = upload_video(video_path, upload_payload)
            if upload_result and upload_result != "FAILED":
                break
            logger.warning(f"Upload long attempt {i+1} failed.")
            sleep(3)

        if not upload_result or upload_result == "FAILED":
            safe_update_status(ws, row_idx, col_idx, 'FAILED_UPLOAD_LONG')
            return False

        # Ghi YouTube ID
        if isinstance(upload_result, dict):
            vid = upload_result.get("video_id") or upload_result.get("id")
            try_update_youtube_id(ws, row_idx, vid)

        safe_update_status(ws, row_idx, col_idx, 'UPLOADED_LONG')
        logger.info("🎉 LONG VIDEO OK")
        return True

    except Exception as e:
        logger.error(f"ERROR LONG VIDEO: {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'ERROR_LONG')
        return False


# =========================================================
#  SHORTS
# =========================================================
def process_shorts(data, task_meta):
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')

    eid = data.get('ID')

    logger.info(f"🎬 BẮT ĐẦU SHORTS: {eid}")

    try:
        script_path, title_path = generate_short_script(data)
        with open(title_path, "r", encoding="utf-8") as f:
            hook_title = f.read().strip()

        # TTS
        tts = None
        for i in range(3):
            tts = create_tts(script_path, eid, "short")
            if tts:
                break
            sleep(2)
        if not tts:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_TTS_SHORT')
            return False

        # Render
        shorts_path = create_shorts(tts, hook_title, eid, data.get("Name", ""))
        if not shorts_path:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_RENDER_SHORTS')
            return False

        # Upload
        upload_data = {
            "Title": f"{hook_title} – {data.get('Name')} | Bí mật chưa từng kể #Shorts",
            "Summary": f"Short story about {data.get('Name')}.\nFull story on channel.",
            "Tags": ["shorts", "podcast", "history"]
        }

        upload_result = upload_video(shorts_path, upload_data)
        if not upload_result or upload_result == 'FAILED':
            safe_update_status(ws, row_idx, col_idx, 'FAILED_UPLOAD_SHORTS')
            return False

        safe_update_status(ws, row_idx, col_idx, 'UPLOADED_SHORTS')
        logger.info("🎉 SHORTS OK")
        return True

    except Exception as e:
        logger.error(f"ERROR SHORTS: {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'ERROR_SHORTS')
        return False


# =========================================================
#  MAIN
# =========================================================
def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("Không có task pending.")
        return

    data = task["data"]
    task_meta = {
        "row_idx": task["row_idx"],
        "col_idx": task["col_idx"],
        "worksheet": task["worksheet"]
    }

    logger.info(f"▶️ ĐANG XỬ LÝ TASK ID={data.get('ID')} – {data.get('Name')}")

    long_ok = process_long_video(data, task_meta)
    short_ok = process_shorts(data, task_meta)

    if long_ok and short_ok:
        logger.info("🎉 FULL SUCCESS!")
    elif long_ok:
        logger.info("⚠️ Long OK – Shorts FAILED")
    elif short_ok:
        logger.info("⚠️ Shorts OK – Long FAILED")
    else:
        logger.info("❌ BOTH FAILED")


if __name__ == "__main__":
    main()