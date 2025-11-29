# scripts/create_shorts.py (Đã dùng VIDEO LẶP NỀN RIÊNG)
import os
import logging
from moviepy.editor import *
import math 
import random 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) 

# --- HÀM TẢI ẢNH AN TOÀN (GIỮ NGUYÊN) ---
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

# --- HÀM TẢI VIDEO LẶP NỀN MỚI (CHUNG) ---
def load_looping_background_video(file_name, target_duration, width, height):
    """
    Tải video nền, đảm bảo video lặp lại liên tục cho đến khi đạt được target_duration.
    """
    video_path = os.path.join('assets', 'video', file_name)
    if not os.path.exists(video_path):
        logging.warning(f"Không tìm thấy video nền tại: {video_path}. Sẽ dùng nền màu tĩnh.")
        return ColorClip((width, height), color=COLOR_BACKGROUND, duration=target_duration)

    try:
        # Tải video gốc
        original_clip = VideoFileClip(video_path)
        
        # Nếu video gốc đã dài hơn thời lượng mục tiêu, chỉ cần cắt
        if original_clip.duration >= target_duration:
            clip = original_clip.subclip(0, target_duration)
        else:
            # Tính toán số lần lặp cần thiết
            num_loops = math.ceil(target_duration / original_clip.duration)
            # Tạo danh sách các clip lặp lại và nối lại
            looped_clips = [original_clip] * num_loops
            final_loop = concatenate_videoclips(looped_clips)
            clip = final_loop.subclip(0, target_duration)
        
        # Đảm bảo clip được resize để vừa với khung hình mục tiêu
        clip = clip.resize(newsize=(width, height))

        logging.info(f"Đã tạo video nền lặp thành công. Độ dài: {clip.duration:.2f}s")
        return clip

    except Exception as e:
        logging.error(f"Lỗi khi tải hoặc lặp video nền {video_path}: {e}")
        return ColorClip((width, height), color=COLOR_BACKGROUND, duration=target_duration)


# --- BẮT ĐẦU CREATE_SHORTS ---
def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # --- 1. Tải Nền Dạng Video Lặp (SHORT) ---
        background_clip = load_looping_background_video('podcast_loop_bg_short.mp4', duration, SHORTS_WIDTH, SHORTS_HEIGHT)

        logging.warning("BỎ QUA PHỤ ĐỀ cho video Shorts để hoàn thành pipeline.")
        # Clip giữ chỗ cho phụ đề (opacity 0)
        subtitle_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)

        # Tải micro (Vị trí đã điều chỉnh xuống: SHORTS_HEIGHT // 2 + 180)
        microphone_clip = load_asset_image('microphone.png', width=int(SHORTS_WIDTH * 0.3), duration=duration, position=("center", SHORTS_HEIGHT // 2 + 180))
        
        # Ghép các thành phần (Chỉ gồm nền, micro và clip giữ chỗ phụ đề)
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
