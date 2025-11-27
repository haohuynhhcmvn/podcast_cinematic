#utils.py
import os

def setup_environment():
    """Kiểm tra và tạo các thư mục cần thiết cho dự án."""
    required_dirs = [
        'data/episodes', 'inputs/images', 'outputs/audio', 'outputs/subtitle',
        'outputs/video', 'outputs/shorts', 'assets/intro_outro', 'assets/background_music'
    ]
    
    for dir_path in required_dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    print("Môi trường và cấu trúc thư mục đã được thiết lập.")

def load_template_file(filepath):
    """Tải nội dung từ một file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file template tại {filepath}")
        return None
