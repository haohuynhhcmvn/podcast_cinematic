# scripts/create_shorts.py (ĐÃ SỬA: Thêm chuyển động sóng âm)
import os
import logging
from moviepy.editor import *
from moviepy.tools import time_to_seconds # Dùng cho việc tính toán
import math # Cần import math cho hàm sin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) 

# ... (Phần create_shorts function bắt đầu)

        # ... (Phần Giới hạn thời lượng và Nền giữ nguyên)
        
        # Tiêu đề
        title_text = TextClip(f"PODCAST: {episode_id}", fontsize=80, color='yellow', 
                              font='sans-bold', 
                              size=(SHORTS_WIDTH * 0.9, None), bg_color='black')
        title_text = title_text.set_duration(duration).set_pos(('center', SHORTS_HEIGHT * 0.1))

        # Sóng âm ĐỘNG (Animated Visual Placeholder)
        WAVE_COLOR = (0, 200, 0)
        WAVE_HEIGHT = 10 
        WAVE_WIDTH = int(SHORTS_WIDTH * 0.7)
        
        # Tạo clip cơ sở (thanh sóng âm tĩnh)
        base_waveform_clip = ColorClip((WAVE_WIDTH, WAVE_HEIGHT), color=WAVE_COLOR, duration=duration)

        # THÊM HIỆU ỨNG ĐỘNG
        MAX_HEIGHT_MULTIPLIER = 3.0
        PULSE_SPEED = 10

        def resize_func(t):
            # Hàm sin tạo ra sự dao động mượt mà
            scale_factor = 1.0 + (MAX_HEIGHT_MULTIPLIER - 1.0) * (0.5 * (1 + math.sin(t * PULSE_SPEED)))
            return scale_factor
        
        # Áp dụng hiệu ứng resize động
        waveform_clip = base_waveform_clip.fx(vfx.resize, height=lambda t: WAVE_HEIGHT * resize_func(t))
        
        # Đặt clip vào vị trí
        waveform_clip = waveform_clip.set_pos(("center", SHORTS_HEIGHT * 0.45))
        
        # Ghép các thành phần
        final_clip = CompositeVideoClip([
            background_clip, title_text, waveform_clip, subtitle_clip.set_duration(duration).set_pos(('center', 'bottom')).margin(bottom=50)
        ], size=(SHORTS_WIDTH, SHORTS_HEIGHT)).set_audio(audio_clip)

        # ... (Phần Xuất Video giữ nguyên)
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
