# scripts/glue_pipeline_v3.py
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


def safe_update_status(ws, row_idx, col_idx, status):
    """Cập nhật trạng thái lên Google Sheet (bảo vệ lỗi)."""
    try:
        if not ws:
            logger.warning("Không có worksheet để update status.")
            return
        if col_idx and isinstance(col_idx, int):
            ws.update_cell(row_idx, col_idx, status)
        else:
            # fallback: tìm cột "Status" ở header
            try:
                header = ws.row_values(1)
                idx = header.index("Status") + 1
            except Exception:
                idx = 6
            ws.update_cell(row_idx, idx, status)
        logger.info(f"Đã cập nhật row {row_idx} -> {status}")
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật status lên sheet: {e}")


def try_update_youtube_id(ws, row_idx, video_id):
    """Nếu sheet có cột YouTubeID (hoặc VideoID), ghi video id vào."""
    if not ws or not video_id:
        return
    try:
        header = ws.row_values(1)
        candidate_cols = ['YouTubeID', 'VideoID', 'youtube_id', 'video_id']
        for name in candidate_cols:
            if name in header:
                col = header.index(name) + 1
                ws.update_cell(row_idx, col, video_id)
                logger.info(f"Ghi YouTube ID vào cột '{name}' (col {col}).")
                return
    except Exception as e:
        logger.debug(f"Không thể ghi YouTube ID: {e}")


def process_long_video(data, task_meta):
    """
    Luồng FULL VIDEO PODCAST 16:9
    Script dài → TTS → Mix audio → Render Video → Upload → Update Sheet
    """
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')

    eid = data.get('ID')
    name = data.get('Name')

    logger.info(f"🎬 BẮT ĐẦU LUỒNG VIDEO DÀI CHO TẬP {eid} – {name}")

    try:
        # 1) Generate Script Long
        long_result = generate_long_script(data)
        if not long_result:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_GEN_LONG')
            return False

        script_path = long_result.get('script_path')
        meta_json = long_result.get('metadata', {})

        # Dữ liệu upload (fallback hợp lý)
        youtube_title = meta_json.get("youtube_title") or f"{name} – Podcast Huyền Thoại"
        youtube_description = meta_json.get("youtube_description") or ""
        yt_tags_raw = meta_json.get("youtube_tags") or ""
        if isinstance(yt_tags_raw, str):
            youtube_tags = [t.strip() for t in yt_tags_raw.split(',') if t.strip()]
        elif isinstance(yt_tags_raw, list):
            youtube_tags = yt_tags_raw
        else:
            youtube_tags = []

        # 2) TTS LONG (retry nhỏ)
        tts_long = None
        for attempt in range(3):
            tts_long = create_tts(script_path, eid, "long")
            if tts_long:
                break
            logger.warning(f"TTS long attempt {attempt+1} failed, retrying...")
            sleep(2)

        if not tts_long:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_TTS_LONG')
            return False

        # 3) Mix nhạc + voice
        mixed_audio = auto_music_sfx(tts_long, eid)
        if not mixed_audio:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_MIX_LONG')
            return False

        # 4) Render Video 16:9
        video_path = create_video(mixed_audio, eid)
        if not video_path:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_RENDER_LONG')
            return False

        # 5) Upload YouTube
        upload_info = {
            "Title": youtube_title,
            "Summary": youtube_description,
            "Tags": youtube_tags
        }

        upload_result = None
        for attempt in range(2):
            upload_result = upload_video(video_path, upload_info)
            if upload_result and upload_result != 'FAILED':
                break
            logger.warning(f"Upload long attempt {attempt+1} failed, retrying...")
            sleep(3)

        if not upload_result or upload_result == 'FAILED':
            safe_update_status(ws, row_idx, col_idx, 'FAILED_UPLOAD_LONG')
            return False

        # If upload returns dict with video_id, write it
        if isinstance(upload_result, dict):
            vid = upload_result.get('video_id') or upload_result.get('id')
            safe_update_status(ws, row_idx, col_idx, 'UPLOADED_LONG')
            if vid:
                try_update_youtube_id(ws, row_idx, vid)
        elif isinstance(upload_result, str) and upload_result.upper() == 'UPLOADED':
            safe_update_status(ws, row_idx, col_idx, 'UPLOADED_LONG')
        else:
            safe_update_status(ws, row_idx, col_idx, 'UNKNOWN_UPLOAD_LONG')

        logger.info(f"🎉 HOÀN TẤT VIDEO DÀI: {eid}")
        return True

    except Exception as e:
        logger.error(f"❌ Lỗi luồng FULL VIDEO: {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'ERROR_LONG')
        return False


def process_shorts(data, task_meta):
    """Thực hiện luồng Shorts (script -> tts -> render -> upload)."""
    row_idx = task_meta.get('row_idx')
    col_idx = task_meta.get('col_idx')
    ws = task_meta.get('worksheet')

    eid = data.get('ID')
    try:
        result = generate_short_script(data)
        if not result:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_GEN_SHORT')
            return False
        script_short_path, title_short_path = result

        try:
            with open(title_short_path, 'r', encoding='utf-8') as f:
                hook_title = f.read().strip()
        except Exception:
            hook_title = ""

        # TTS (với retry nhỏ)
        tts_short = None
        for attempt in range(3):
            tts_short = create_tts(script_short_path, eid, "short")
            if tts_short:
                break
            logger.warning(f"TTS short attempt {attempt+1} failed, retrying...")
            sleep(2)

        if not tts_short:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_TTS_SHORT')
            return False

        # Render Shorts
        shorts_path = create_shorts(tts_short, hook_title, eid, data.get('Name', ''))
        if not shorts_path:
            safe_update_status(ws, row_idx, col_idx, 'FAILED_RENDER_SHORTS')
            return False

        # Prepare upload metadata
        short_title = f"{hook_title} – {data.get('Name')} | Bí mật chưa từng kể #Shorts"
        short_description = (
            f"⚠️ Câu chuyện: {data.get('Name')}\n"
            f"🔥 Chủ đề: {data.get('Core Theme', 'Huyền thoại')}\n\n"
            f"{data.get('Content/Input', '')}\n\n"
            "👉 Follow kênh để xem full story."
        )
        short_tags = [
            "shorts", "viral", "podcast", "storytelling",
            data.get("Core Theme", ""), data.get("Name", ""),
        ]
        upload_data = {'Title': short_title, 'Summary': short_description, 'Tags': short_tags}

        # Upload (cố gắng 2 lần nếu gặp lỗi tạm thời)
        upload_result = None
        for attempt in range(2):
            upload_result = upload_video(shorts_path, upload_data)
            if upload_result and upload_result != 'FAILED':
                break
            logger.warning(f"Upload short attempt {attempt+1} failed, retrying...")
            sleep(3)

        if not upload_result or upload_result == 'FAILED':
            safe_update_status(ws, row_idx, col_idx, 'FAILED_UPLOAD_SHORTS')
            return False

        # Nếu upload trả về dict với video_id, ghi vào sheet; nếu chỉ trả về 'UPLOADED' thì đánh dấu thành công.
        if isinstance(upload_result, dict):
            vid = upload_result.get('video_id') or upload_result.get('id')
            safe_update_status(ws, row_idx, col_idx, 'UPLOADED_SHORTS')
            if vid:
                try_update_youtube_id(ws, row_idx, vid)
        elif isinstance(upload_result, str) and upload_result.upper() == 'UPLOADED':
            safe_update_status(ws, row_idx, col_idx, 'UPLOADED_SHORTS')
        else:
            safe_update_status(ws, row_idx, col_idx, 'UNKNOWN_UPLOAD_RESULT')

        return True

    except Exception as e:
        logger.error(f"Lỗi luồng Shorts: {e}", exc_info=True)
        safe_update_status(ws, row_idx, col_idx, 'ERROR_SHORTS')
        return False


def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("Không có task pending. Kết thúc.")
        return

    data = task.get('data', {})
    task_meta = {
        'row_idx': task.get('row_idx'),
        'col_idx': task.get('col_idx'),
        'worksheet': task.get('worksheet')
    }

    logger.info("Bắt đầu xử lý task ID=%s, Name=%s", data.get('ID'), data.get('Name'))

    # 1) Chạy Full Video
    long_ok = process_long_video(data, task_meta)

    # 2) Nếu Full Video OK thì hoặc dù sao vẫn chạy Shorts theo yêu cầu (bạn chọn 3: both)
    # Chúng ta sẽ cố gắng chạy Shorts bất kể long_ok hay không — nhưng sẽ đánh dấu trạng thái khác nhau.
    if not long_ok:
        logger.warning("Luồng Full Video gặp lỗi — vẫn cố gắng chạy Shorts.")

    short_ok = process_shorts(data, task_meta)

    # Kết luận trạng thái tổng quan
    if long_ok and short_ok:
        logger.info("🎉 Hoàn tất cả hai luồng (LONG + SHORTS) cho task %s", data.get('ID'))
    elif long_ok and not short_ok:
        logger.info("✅ LONG thành công, SHORTS gặp lỗi.")
    elif not long_ok and short_ok:
        logger.info("✅ SHORTS thành công, LONG gặp lỗi.")
    else:
        logger.info("❌ Cả hai luồng đều gặp lỗi cho task %s", data.get('ID'))


if __name__ == "__main__":
    main()
