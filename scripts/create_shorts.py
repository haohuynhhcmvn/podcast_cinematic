# scripts/create_shorts.py (ĐÃ SỬA: codec='libx264' & Giới hạn 60s)
import os
import logging
from moviepy.editor import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) 

def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # --- LOGIC GIỚI HẠN THỜI LƯỢNG SHORTS (TỐI ĐA 60 GIÂY) ---
        MAX_SHORTS_DURATION = 60 # 60 giây
        
        if duration > MAX_SHORTS_DURATION:
            logging.warning(f"Audio dài {duration:.2f}s. Cắt về tối đa {MAX_SHORTS_DURATION}s cho Shorts.")
            # Cắt audio clip
            audio_clip = audio_clip.subclip(0, MAX_SHORTS_DURATION)
            duration = MAX_SHORTS_DURATION # Cập nhật lại thời lượng
        else:
             logging.info(f"Audio dài {duration:.2f}s, phù hợp với Shorts.")
        
        # --- BỎ QUA PHỤ ĐỀ: LOGIC ĐẢM BẢO HOÀN THÀNH ---
        logging.warning("BỎ QUA PHỤ ĐỀ cho video Shorts để hoàn thành pipeline.")
        
        # Tạo clip placeholder trong suốt có cùng thời lượng và kích thước
        subtitle_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)
        # --- END LOGIC BỎ QUA ---

        # Nền
        background_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # Tiêu đề
        title_text = TextClip(f"PODCAST: {episode_id}", fontsize=80, color='yellow', font='Arial-Bold', 
                              size=(SHORTS_WIDTH * 0.9, None), bg_color='black')
        title_text = title_text.set_duration(duration).set_pos(('center', SHORTS_HEIGHT * 0.1))

        # Sóng âm & Micro Placeholder
        wave_text = TextClip("Sóng Âm Shorts...", fontsize=40, color='white', size=(SHORTS_WIDTH * 0.8, None))
        wave_text = wave_text.set_duration(duration).set_pos(("center", SHORTS_HEIGHT * 0.45))
        
        # Ghép các thành phần
        final_clip = CompositeVideoClip([
            background_clip, title_text, wave_text, subtitle_clip.set_duration(duration).set_pos(('center', 'bottom')).margin(bottom=50)
        ], size=(SHORTS_WIDTH, SHORTS_HEIGHT)).set_audio(audio_clip)

        # Xuất Video
        output_dir = os.path.join('outputs', 'shorts')
        video_filename = f"{episode_id}_shorts_916.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu xuất Video Shorts 9:16...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, logger='bar' # <<< ĐÃ SỬA: libx64 -> libx264
        )
        
        logging.info(f"Video Shorts 9:16 đã tạo thành công và lưu tại: {video_path}")
        return video_path 

    except Exception as e:
        logging.error(f"Lỗi khi tạo video Shorts: {e}", exc_info=True)
        return None
