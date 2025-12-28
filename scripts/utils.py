# === scripts/utils.py (ĐÃ TỐI ƯU + MỞ RỘNG AN TOÀN) ===
import os
import logging
import shutil  # Import cho cleanup
import hashlib # <-- [THÊM] cho cache waveform (KHÔNG PHÁ LOGIC CŨ)

# Thiết lập logger
logger = logging.getLogger(__name__)

# Xác định thư mục gốc của dự án
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def get_path(*args):
    """Trả về đường dẫn tuyệt đối an toàn."""
    return os.path.join(PROJECT_ROOT, *args)


def setup_environment():
    """Tạo đầy đủ cấu trúc thư mục đầu ra và log lại."""
    
    required_dirs = [
        'data/episodes', 
        'assets/images', 'assets/audio', 'assets/video', 
        'assets/intro_outro', 'assets/background_music',
        'assets/temp', 
        'outputs/audio', 'outputs/video', 'outputs/shorts',
        'outputs/thumbnails'
    ]
    
    for d in required_dirs:
        os.makedirs(get_path(d), exist_ok=True)
        
    logger.info(f"✅ Cấu trúc thư mục dự án đã sẵn sàng tại: {PROJECT_ROOT}")


# ============================================================
# 🔐 [THÊM MỚI – AN TOÀN] HASH FILE CHO CACHE (WAVEFORM)
# ============================================================
def file_md5(path: str, chunk_size: int = 8192) -> str:
    """
    Tính MD5 của file để làm cache key.
    → Dùng cho waveform video, KHÔNG ảnh hưởng logic cũ.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File không tồn tại để hash: {path}")

    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


# ============================================================
# 🗑️ CLEANUP (GIỮ NGUYÊN LOGIC CŨ 100%)
# ============================================================
def cleanup_temp_files(episode_id: str, text_hash: str):
    """
    Xóa các file tạm liên quan đến episode đã hoàn thành.
    """
    try:
        episode_id_str = str(episode_id)

        # 1. Xóa file tạm trong assets/temp
        temp_dir = get_path("assets", "temp")
        for f in os.listdir(temp_dir):
            if (
                f.startswith(episode_id_str)
                or f.startswith("char_blend_mix")
                or f.startswith("img_clip")
            ):
                os.remove(os.path.join(temp_dir, f))
        
        # 2. Xóa audio mix trung gian
        audio_mix_path = get_path('outputs', 'audio', f"{episode_id_str}_mixed.mp3")
        if os.path.exists(audio_mix_path):
            os.remove(audio_mix_path)

        # 3. Xóa thumbnail trung gian
        thumb_out = get_path("outputs", "thumbnails", f"{episode_id_str}_thumb.jpg")
        if os.path.exists(thumb_out):
            os.remove(thumb_out)
        
        # 4. Xóa thư mục assets theo text_hash
        asset_folder = get_path('assets', text_hash)
        if os.path.exists(asset_folder):
            if os.listdir(asset_folder):
                shutil.rmtree(asset_folder, ignore_errors=True)

        logger.info(f"🗑️ Dọn dẹp files tạm cho ID: {episode_id_str} hoàn tất.")
        
    except Exception as e:
        logger.error(f"⚠️ Lỗi dọn dẹp: {e}")
