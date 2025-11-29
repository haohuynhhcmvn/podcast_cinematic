# File: ./scripts/create_video.py
# Chức năng: Tạo video 16:9 (video dài) bằng cách trộn audio, video nền lặp và ảnh tĩnh.

import os
import logging
import moviepy.editor as mp
import math
import random
# BỎ QUA SubtitlesClip và file_to_subtitles để tránh lỗi và không cần dùng

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)
BACKGROUND_VIDEO_LONG = 'podcast_loop_bg_long.mp4' # <-- Tên file video nền dài

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
        clip = mp.ImageClip(image_path).set_duration(duration)
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

# --- HÀM TẢI VIDEO LẶP NỀN --- (Giữ nguyên)
def load_looping_background_video(file_name, target_duration, width, height):
    """Tải video nền và lặp lại cho đến khi đạt độ dài mong muốn."""
    video_path = os.path.join('assets', 'video', file_name)
    if not os.path.exists(video_path):
        logging.warning(f"Không tìm thấy video nền tại: {video_path}. Dùng nền màu tĩnh.")
        return mp.ColorClip((width, height), color=COLOR_BACKGROUND, duration=target_duration)

    try:
        original_clip = mp.VideoFileClip(video_path)
        if original_clip.duration >= target_duration:
            clip = original_clip.subclip(0, target_duration)
        else:
            num_loops = math.ceil(target_duration / original_clip.duration)
            looped_clips = [original_clip] * num_loops
            final_loop = mp.concatenate_videoclips(looped_clips)
            clip = final_loop.subclip(0, target_duration)
        
        clip = clip.resize(newsize=(width, height))
        logging.info(f"Đã tạo video nền lặp thành công từ file: {file_name}")
        return clip
    except Exception as e:
        logging.error(f"Lỗi khi tải video nền {video_path}: {e}")
        return mp.ColorClip((width, height), color=COLOR_BACKGROUND, duration=target_duration)

# --- HÀM CHÍNH: CREATE_VIDEO ---
def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        logging.warning("CHẾ ĐỘ TẮT TÍNH NĂNG: Phụ đề và Sóng âm đã bị BỎ QUA để chạy thử pipeline.")

        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # 1. Bỏ qua xử lý Phụ đề
        
        # 2. Tải Nền Video Lặp (16:9)
        # SỬ DỤNG HẰNG SỐ ĐÃ ĐỊNH NGHĨA Ở TRÊN
        background_clip = load_looping_background_video(BACKGROUND_VIDEO_LONG, duration, VIDEO_WIDTH, VIDEO_HEIGHT)

        # 3. Tải Micro (Ảnh tĩnh)
        microphone_clip = load_asset_image('microphone.png', width=int(VIDEO_WIDTH * 0.15), duration=duration, position=("center", VIDEO_HEIGHT * 0.4))
        
        # 4. Bỏ qua tạo Sóng Âm Đa Thanh

        # 5. Ghép các thành phần
        # Chỉ bao gồm nền và micro (nếu có)
        elements = [background_clip]
        if microphone_clip:
            elements.append(microphone_clip) 

        final_clip = mp.CompositeVideoClip(elements, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # 6. Xuất Video
        output_dir = os.path.join('outputs', 'video')
        os.makedirs(output_dir, exist_ok=True)
        video_filename = f"{episode_id}_full_podcast_169.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu xuất Video 16:9 (Chỉ nền và micro)...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, logger='bar'
        )

        logging.info(f"Video 16:9 đã tạo thành công: {video_path}")
        return video_path

    except Exception as e:
        logging.error(f"Lỗi khi tạo video 16:9: {e}", exc_info=True)
        return None
