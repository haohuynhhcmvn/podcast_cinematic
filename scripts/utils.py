import os
import sys

# Xác định thư mục gốc của dự án
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_path(*args):
    """Trả về đường dẫn tuyệt đối an toàn."""
    return os.path.join(PROJECT_ROOT, *args)

def setup_environment():
    """Tạo đầy đủ cấu trúc thư mục đầu ra."""
    required_dirs = [
        'data/episodes', 
        'assets/images', 'assets/audio', 'assets/video', 
        'assets/intro_outro', 'assets/background_music',
        'outputs/audio', 'outputs/video', 'outputs/shorts'
    ]
    for d in required_dirs:
        os.makedirs(get_path(d), exist_ok=True)
    print(f"✅ Môi trường đã sẵn sàng tại: {PROJECT_ROOT}")
