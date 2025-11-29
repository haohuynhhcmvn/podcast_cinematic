# scripts/create_shorts.py (PHIÊN BẢN TẠM THỜI: TẮT PHỤ ĐỀ VÀ SÓNG ÂM)
import os
import logging
from moviepy.editor import *
import math 
import random 
# BỎ QUA SubtitlesClip và file_to_subtitles

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) 

# --- HÀM TẢI ẢNH AN TOÀN --- (Giữ nguyên)
def load_asset_image(file_name, width=None, height=None, duration=None, position=('center', 'center')):
    """Tải ảnh từ thư mục assets/images, resize và đặt vị trí an toàn."""
    paths_to_check = [
        os.path.join('assets', 'images', file_name), 
        os.path.join('assets', 'image', file_name)
    ]
    
    image_path = None
    for path in paths_to_check:
        if os.path.exists(path):
            image_path = path
            break
            
    if not image_path:
        logging.warning(f"Không tìm thấy file ảnh: {file_name}. Trả về None.")
        return None

    try:
        clip = ImageClip(image_path).set_duration(duration)
        
        if width and height:
            clip = clip.resize(newsize=(width, height))
        elif width:
            clip = clip.resize(width=width)
        elif height:
            clip = clip.resize(height=height)
            
        return clip.set_pos(position)
    except Exception as e:
        logging.error(f"Lỗi khi tải ảnh {image_path}: {e}")
        return None

# --- BẮT ĐẦU CREATE_SHORTS ---
def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        # THÔNG BÁO CHẾ ĐỘ TẮT TÍNH NĂNG
        logging.warning("CHẾ ĐỘ TẮT TÍNH NĂNG: Phụ đề và Sóng âm đã bị BỎ QUA để chạy thử pipeline.")

        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        MAX_SHORTS_DURATION = 60 
        if duration > MAX_SHORTS_DURATION:
            audio_clip = audio_clip.subclip(0, MAX_SHORTS_DURATION)
            duration = audio_clip.duration
        
        # 1. Bỏ qua xử lý Phụ đề và Sóng âm

        # 2. Tải Nền (Ảnh tĩnh)
        background_clip = load_asset_image('default_background_shorts.png', width=SHORTS_WIDTH, height=SHORTS_HEIGHT, duration=duration)
        if not background_clip:
            background_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
            
        # 3. Tải Micro (Ảnh tĩnh)
        microphone_clip = load_asset_image('microphone.png', width=int(SHORTS_WIDTH * 0.3), duration=duration, position=("center", SHORTS_HEIGHT * 0.55)) 
        
        # 4. Tiêu đề tĩnh
        title_text = TextClip("THEO DẤU CHÂN HUYỀN THOẠI", fontsize=80, color='yellow', font='sans-bold', size=(SHORTS_WIDTH * 0.9, None), bg_color='black')
        title_text = title_text.set_duration(duration).set_pos(('center', SHORTS_HEIGHT * 0.1))

        # 5. Ghép các thành phần
        # Chỉ bao gồm nền, tiêu đề và micro (nếu có)
        elements = [background_clip, title_text]
        if microphone_clip:
            elements.append(microphone_clip) 

        final_clip = CompositeVideoClip(elements, size=(SHORTS_WIDTH, SHORTS_HEIGHT)).set_audio(audio_clip)

        # 6. Xuất Video 
        output_dir = os.path.join('outputs', 'shorts')
        os.makedirs(output_dir, exist_ok=True)
        video_filename = f"{episode_id}_shorts_916.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu xuất Video Shorts 9:16 (Chỉ nền, tiêu đề và micro)...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, logger='bar'
        )
        
        logging.info(f"Video Shorts 9:16 đã tạo thành công và lưu tại: {video_path}")
        return video_path 

    except Exception as e:
        logging.error(f"Lỗi khi tạo video Shorts: {e}", exc_info=True)
        return None
