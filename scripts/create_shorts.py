# scripts/create_shorts.py (ĐÃ SỬA: Thêm Background và Micro từ Assets)
import os
import logging
from moviepy.editor import *
import math 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) # Màu dự phòng
MICROPHONE_IMAGE_PATH = os.path.join('assets', 'images', 'microphone.png')
BACKGROUND_IMAGE_DEFAULT_PATH = os.path.join('assets', 'images', 'default_background_shorts.png') # Ảnh nền mặc định cho shorts

def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # --- LOGIC GIỚI HẠN THỜI LƯỢNG SHORTS ---
        MAX_SHORTS_DURATION = 60 
        
        if duration > MAX_SHORTS_DURATION:
            logging.warning(f"Audio dài {duration:.2f}s. Cắt về tối đa {MAX_SHORTS_DURATION}s cho Shorts.")
            audio_clip = audio_clip.subclip(0, MAX_SHORTS_DURATION)
            duration = MAX_SHORTS_DURATION
        else:
             logging.info(f"Audio dài {duration:.2f}s, phù hợp với Shorts.")
        
        # --- BỎ QUA PHỤ ĐỀ ---
        logging.warning("BỎ QUA PHỤ ĐỀ cho video Shorts để hoàn thành pipeline.")
        subtitle_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)

        # --- NỀN (BACKGROUND IMAGE) ---
        background_image_path = BACKGROUND_IMAGE_DEFAULT_PATH # Sử dụng ảnh nền mặc định
        
        if not os.path.exists(background_image_path):
            logging.warning(f"Ảnh nền mặc định cho Shorts không tìm thấy tại {background_image_path}. Dùng ColorClip làm nền.")
            background_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        else:
            background_clip = ImageClip(background_image_path).set_duration(duration)
            background_clip = background_clip.resize(newsize=(SHORTS_WIDTH, SHORTS_HEIGHT))

        # --- MICROPHONE IMAGE ---
        microphone_clip = None
        if os.path.exists(MICROPHONE_IMAGE_PATH):
            microphone_clip = ImageClip(MICROPHONE_IMAGE_PATH).set_duration(duration)
            microphone_clip = microphone_clip.resize(width=int(SHORTS_WIDTH * 0.3)) # Kích thước micro cho Shorts
            microphone_clip = microphone_clip.set_pos(("center", SHORTS_HEIGHT // 2 + 150)) # Đặt phía dưới sóng âm
        
        # Tiêu đề
        title_text = TextClip(f"PODCAST: {episode_id}", fontsize=80, color='yellow', 
                              font='sans-bold', 
                              size=(SHORTS_WIDTH * 0.9, None), bg_color='black')
        title_text = title_text.set_duration(duration).set_pos(('center', SHORTS_HEIGHT * 0.1))

        # Sóng âm ĐỘNG
        WAVE_COLOR = (0, 200, 0)
        WAVE_HEIGHT = 10 
        WAVE_WIDTH = int(SHORTS_WIDTH * 0.7)
        
        base_waveform_clip = ColorClip((WAVE_WIDTH, WAVE_HEIGHT), color=WAVE_COLOR, duration=duration)

        MAX_HEIGHT_MULTIPLIER = 3.0
        PULSE_SPEED = 10

        def resize_func(t):
            scale_factor = 1.0 + (MAX_HEIGHT_MULTIPLIER - 1.0) * (0.5 * (1 + math.sin(t * PULSE_SPEED)))
            return scale_factor
        
        waveform_clip = base_waveform_clip.fx(vfx.resize, height=lambda t: WAVE_HEIGHT * resize_func(t))
        waveform_clip = waveform_clip.set_pos(("center", SHORTS_HEIGHT * 0.45))
        
        # Ghép các thành phần
        elements = [background_clip, title_text, waveform_clip, subtitle_clip.set_duration(duration).set_pos(('center', 'bottom')).margin(bottom=50)]
        if microphone_clip:
            elements.insert(1, microphone_clip) # Chèn micro phía trên background, dưới tiêu đề/sóng âm

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
