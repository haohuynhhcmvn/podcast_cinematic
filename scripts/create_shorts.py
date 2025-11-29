# File: ./scripts/create_shorts.py
# Chức năng: Tạo video Shorts 9:16 bằng cách trộn audio, video nền (hoặc ảnh tĩnh) và ảnh micro.

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
BACKGROUND_VIDEO_SHORT = 'podcast_loop_bg_short.mp4' # <-- Tên file video nền ngắn

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

# --- HÀM TẢI VIDEO LẶP NỀN (TỪ create_video.py) ---
def load_looping_background_video(file_name, target_duration, width, height):
    """Tải video nền và lặp lại cho đến khi đạt độ dài mong muốn."""
    video_path = os.path.join('assets', 'video', file_name)
    if not os.path.exists(video_path):
        logging.warning(f"Không tìm thấy video nền tại: {video_path}. Dùng nền màu tĩnh.")
        return ColorClip((width, height), color=COLOR_BACKGROUND, duration=target_duration)

    try:
        original_clip = VideoFileClip(video_path)
        if original_clip.duration >= target_duration:
            clip = original_clip.subclip(0, target_duration)
        else:
            num_loops = math.ceil(target_duration / original_clip.duration)
            looped_clips = [original_clip] * num_loops
            final_loop = concatenate_videoclips(looped_clips)
            clip = final_loop.subclip(0, target_duration)
        
        clip = clip.resize(newsize=(width, height))
        logging.info(f"Đã tạo video nền lặp thành công từ file: {file_name}")
        return clip
    except Exception as e:
        logging.error(f"Lỗi khi tải video nền {video_path}: {e}")
        return ColorClip((width, height), color=COLOR_BACKGROUND, duration=target_duration)


# --- BẮT ĐẦU CREATE_SHORTS ---
def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        logging.warning("CHẾ ĐỘ TẮT TÍNH NĂNG: Phụ đề và Sóng âm đã bị BỎ QUA để chạy thử pipeline.")

        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        MAX_SHORTS_DURATION = 60 
        if duration > MAX_SHORTS_DURATION:
            audio_clip = audio_clip.subclip(0, MAX_SHORTS_DURATION)
            duration = audio_clip.duration
        
        # 1. Bỏ qua xử lý Phụ đề và Sóng âm

        # 2. Tải Nền Video Lặp (9:16)
        # SỬ DỤNG HÀM TẢI VIDEO LẶP VÀ HẰNG SỐ ĐÃ ĐỊNH NGHĨA Ở TRÊN
        background_clip = load_looping_background_video(BACKGROUND_VIDEO_SHORT, duration, SHORTS_WIDTH, SHORTS_HEIGHT)
            
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
