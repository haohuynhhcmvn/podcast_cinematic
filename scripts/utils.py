# ===scripts/utils.py (Đã Tối Ưu)===
import os
import logging

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
        'assets/temp', # Đã thêm
        'outputs/audio', 'outputs/video', 'outputs/shorts'
    ]
    
    for d in required_dirs:
        os.makedirs(get_path(d), exist_ok=True)
        
    # Thay print bằng logger.info
    logger.info(f"✅ Cấu trúc thư mục dự án đã sẵn sàng tại: {PROJECT_ROOT}")

# Nếu bạn chọn dùng logging, bạn cần đảm bảo logging được cấu hình ở nơi gọi setup_environment.
