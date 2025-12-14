# ===scripts/utils.py (Đã Tối Ưu)===
import os
import logging
import shutil # Import mới cho cleanup

# Thiết lập logger (tùy chọn, cần được cấu hình ở file chính)
logger = logging.getLogger(__name__)

# Xác định thư mục gốc của dự án
# Dùng os.path.realpath để xử lý symlink, làm cho đường dẫn ổn định hơn
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def get_path(*args):
    """Trả về đường dẫn tuyệt đối an toàn."""
    return os.path.join(PROJECT_ROOT, *args)

def setup_environment():
    """Tạo đầy đủ cấu trúc thư mục đầu ra và log lại."""
    
    # Thêm 'assets/temp' vì bạn dùng nó trong create_video.py
    required_dirs = [
        'data/episodes', 
        'assets/images', 'assets/audio', 'assets/video', 
        'assets/intro_outro', 'assets/background_music',
        'assets/temp', 
        'outputs/audio', 'outputs/video', 'outputs/shorts',
        'outputs/thumbnails' # <--- ĐÃ THÊM MỚI
    ]
    
    for d in required_dirs:
        os.makedirs(get_path(d), exist_ok=True)
        
    # Thay print bằng logger.info
    logger.info(f"✅ Cấu trúc thư mục dự án đã sẵn sàng tại: {PROJECT_ROOT}")

# --- HÀM DỌN DẸP (CLEANUP) MỚI ---
def cleanup_temp_files(episode_id: str, text_hash: str):
    """
    Xóa các file tạm liên quan đến episode đã hoàn thành (TTS chunks, video render, audio mix, v.v.).
    """
    try:
        # 1. Xóa các file trung gian (TTS chunks, ảnh AI raw, hybrid BG)
        temp_dir = get_path("assets", "temp")
        for f in os.listdir(temp_dir):
            if f.startswith(episode_id) or f.startswith("char_blend_mix") or f.startswith("img_clip"):
                os.remove(os.path.join(temp_dir, f))
        
        # 2. Xóa các file output trung gian (Audio Mix, Thumb)
        # Audio Mix
        audio_mix_path = get_path('outputs', 'audio', f"{episode_id}_mixed.mp3")
        if os.path.exists(audio_mix_path): os.remove(audio_mix_path)

        # Thumbnail 
        thumb_out = get_path("outputs", "thumbnails", f"{episode_id}_thumb.jpg")
        if os.path.exists(thumb_out): os.remove(thumb_out)
        
        # 3. Xóa thư mục Assets/Hash (chứa ảnh AI đã tải và script)
        asset_folder = get_path('assets', text_hash)
        if os.path.exists(asset_folder):
            if not os.listdir(asset_folder):
                 os.rmdir(asset_folder)
            else:
                 # Nếu không rỗng, xóa toàn bộ nội dung (chú ý: giữ lại các file credential)
                 shutil.rmtree(asset_folder, ignore_errors=True) 

        logger.info(f"🗑️ Dọn dẹp files tạm cho ID: {episode_id} hoàn tất.")
        
    except Exception as e:
        logger.error(f"⚠️ Lỗi dọn dẹp: {e}")
