import logging
import sys
import os
from time import sleep
from concurrent.futures import ThreadPoolExecutor

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from utils import setup_environment, cleanup_temp_files
from fetch_content import fetch_content
from generate_script import generate_long_script, split_long_script_to_5_shorts
from create_tts import create_tts
from create_video import create_video
from create_shorts import create_shorts
from upload_youtube import upload_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_one_short(short_cfg, data, image_path):
    idx = short_cfg["index"]
    logger.info(f"▶️ SHORT {idx}/5 START")

    script = short_cfg["script"]
    title = open(short_cfg["title"], encoding="utf-8").read().strip()

    tts = create_tts(script, data["ID"], f"short_{idx}")
    video = create_shorts(
        tts,
        title,
        f"{data['ID']}_{idx}",
        data["Name"],
        script,
        custom_image_path=image_path
    )

    upload_video(video, {
        "Title": f"{title} | #Shorts",
        "Summary": title,
        "Tags": ["shorts", "history"]
    })

    logger.info(f"✅ SHORT {idx} DONE")


# === FILE: scripts/glue_pipeline.py ===

def main():
    setup_environment()
    task = fetch_content()
    if not task:
        logger.info("No task.")
        return

    data = task["data"]
    eid = str(data["ID"])

    logger.info("🎬 START LONG VIDEO")
    
    # 1. Tạo Kịch bản
    long_res = generate_long_script(data)
    
    # --- [ĐOẠN CẦN SỬA Ở ĐÂY] ---
    
    # SAI (Cũ): Bạn truyền thẳng file text vào hàm tạo video
    # video = create_video(long_res["script_path"], eid) 

    # ĐÚNG (Mới): Phải tạo Audio từ Text trước!
    
    # B1: Đọc nội dung từ file text
    with open(long_res["script_path"], "r", encoding="utf-8") as f:
        script_content = f.read()

    # B2: Tạo giọng đọc (TTS)
    logger.info("🔊 Generating TTS for Long Video...")
    audio_path = create_tts(script_content, eid, "long")

    # B3: Kiểm tra nếu có Audio thì mới làm Video
    if audio_path:
        logger.info("🎥 Rendering Long Video...")
        # Truyền đường dẫn AUDIO vào, không phải đường dẫn Text
        video_path = create_video(audio_path, eid) 
        
        # B4: Upload (Chỉ upload nếu tạo video thành công)
        if video_path and os.path.exists(video_path):
            upload_video(video_path, long_res["metadata"])
        else:
            logger.error("❌ Lỗi: Không tạo được Video dài.")
    else:
        logger.error("❌ Lỗi: Không tạo được giọng đọc (TTS).")

    # ----------------------------

    logger.info("✅ LONG VIDEO DONE")

    logger.info("📱 GENERATING 5 SHORTS FROM LONG SCRIPT")
    # ... (Phần shorts giữ nguyên vì bạn đã làm đúng trong hàm process_one_short)
    shorts = split_long_script_to_5_shorts(data, long_res["script_path"])
    # ...
    image_path = f"assets/temp/{eid}_raw_ai.png"

    logger.info("📱 GENERATING 5 SHORTS (SEQUENTIAL MODE)...")
    
    for short_cfg in shorts:
        try:
            # Truyền thêm image_path từ long_video vào để làm background
            # Nếu long_res không có image_path, hãy đảm bảo logic lấy ảnh đúng
            bg_image = long_res.get("image_path") 
            process_one_short(short_cfg, data, bg_image)
            
            # Nghỉ 2 giây giữa các video để giải phóng RAM
            sleep(2) 
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo Short {short_cfg['index']}: {e}")

    logger.info("✅ ALL SHORTS PROCESSED")

if __name__ == "__main__":
    main()
