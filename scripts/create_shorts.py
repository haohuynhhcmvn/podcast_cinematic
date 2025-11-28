# scripts/create_shorts.py (Đã loại bỏ sóng âm và sửa tiêu đề)
import os
import logging
from moviepy.editor import *
import math 
import random 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) 

# --- HÀM TẢI ẢNH AN TOÀN ---
def load_asset_image(file_name, width=None, height=None, duration=None, position=('center', 'center')):
    """Tải ảnh, resize và đặt vị trí an toàn."""
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
        logging.warning(f"Không tìm thấy file ảnh: {file_name} trong cả assets/images và assets/image. Trả về None.")
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
        logging.error(f"Lỗi khi tải hoặc resize ảnh {image_path}: {e}")
        return None

# LƯU Ý: HÀM create_multi_bar_visualizer ĐÃ BỊ LOẠI BỎ THEO YÊU CẦU

# --- BẮT ĐẦU CREATE_SHORTS ---
def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        MAX_SHORTS_DURATION = 60 
        if duration > MAX_SHORTS_DURATION:
            audio_clip = audio_clip.subclip(0, MAX_SHORTS_DURATION)
            duration = MAX_SHORTS_DURATION
        
        logging.warning("BỎ QUA PHỤ ĐỀ cho video Shorts để hoàn thành pipeline.")
        # Clip giữ chỗ cho phụ đề (opacity 0)
        subtitle_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)

        # Tải nền
        background_clip = load_asset_image('default_background_shorts.png', width=SHORTS_WIDTH, height=SHORTS_HEIGHT, duration=duration)
        if not background_clip:
            background_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
            
        # Tải micro (Vị trí đã điều chỉnh xuống: SHORTS_HEIGHT // 2 + 180)
        microphone_clip = load_asset_image('microphone.png', width=int(SHORTS_WIDTH * 0.3), duration=duration, position=("center", SHORTS_HEIGHT // 2 + 180))
        
        # Tiêu đề (ĐÃ SỬA: Loại bỏ chữ "podcast" thừa)
        # title_text = TextClip("THEO DẤU CHÂN HUYỀN THOẠI", fontsize=80, color='yellow', font='sans-bold', size=(SHORTS_WIDTH * 0.9, None), bg_color='black')
        # title_text = title_text.set_duration(duration).set_pos(('center', SHORTS_HEIGHT * 0.1))

        # Ghép các thành phần (ĐÃ LOẠI BỎ waveform_clip)
        elements = [background_clip, subtitle_clip.set_duration(duration).set_pos(('center', 'bottom')).margin(bottom=50)]
        if microphone_clip:
            elements.insert(1, microphone_clip)

        final_clip = CompositeVideoClip(elements, size=(SHORTS_WIDTH, SHORTS_HEIGHT)).set_audio(audio_clip)

        # Xuất Video 
        output_dir = os.path.join('outputs', 'shorts')
        video_filename = f"{episode_id}_shorts_916.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu xuất Video Shorts 9:16...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, logger='bar'
        )
        
        logging.info(f"Video Shorts 9:16 đã tạo thành công và lưu tại: {video_path}")
        return video_path 

    except Exception as e:
        logging.error(f"Lỗi khi tạo video Shorts: {e}", exc_info=True)
        return None
