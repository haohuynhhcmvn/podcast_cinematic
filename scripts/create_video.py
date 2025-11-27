# scripts/create_video.py (Đã loại bỏ sóng âm)
import os
import logging
import moviepy.editor as mp
import math
import random 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
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
        clip = mp.ImageClip(image_path).set_duration(duration)
        
        # Resize
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

# --- BẮT ĐẦU CREATE_VIDEO ---
def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        logging.warning("BỎ QUA HOÀN TOÀN TẠO PHỤ ĐỀ (SubtitleClip) cho video 16:9 để hoàn thành pipeline.")
        
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Clip giữ chỗ cho phụ đề (opacity 0)
        subtitle_clip_to_use = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)

        # Tải nền
        background_clip = load_asset_image('default_background.png', width=VIDEO_WIDTH, height=VIDEO_HEIGHT, duration=duration)
        if not background_clip:
            background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
            
        # Tải micro (Vị trí đã điều chỉnh xuống: VIDEO_HEIGHT // 2 + 80)
        microphone_clip = load_asset_image('microphone.png', width=int(VIDEO_WIDTH * 0.2), duration=duration, position=("center", VIDEO_HEIGHT // 2 + 80))
        
        # Ghép các thành phần (Chỉ gồm nền, micro và clip giữ chỗ phụ đề)
        elements = [background_clip, subtitle_clip_to_use]
        if microphone_clip:
            elements.insert(1, microphone_clip)

        final_clip = mp.CompositeVideoClip(elements, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # Xuất Video
        output_dir = os.path.join('outputs', 'video')
        video_filename = f"{episode_id}_full_podcast_169.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu xuất Video 16:9...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, logger='bar'
        )

        logging.info(f"Video 16:9 đã tạo thành công và lưu tại: {video_path}")
        return video_path

    except Exception as e:
        logging.error(f"Lỗi khi tạo video 16:9: {e}", exc_info=True)
        return None
