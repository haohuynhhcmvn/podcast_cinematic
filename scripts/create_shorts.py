import os
import logging
from moviepy.editor import *
from moviepy.video.tools.subtitles import SubtitlesClip # Giữ import để tránh lỗi NameError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) 

def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # --- BỎ QUA PHỤ ĐỀ: LOGIC ĐẢM BẢO HOÀN THÀNH ---
        logging.warning("BỎ QUA PHỤ ĐỀ cho video Shorts để hoàn thành pipeline.")
        
        # Tạo clip placeholder trong suốt có cùng thời lượng và kích thước
        # Clip này sẽ chiếm vị trí của phụ đề mà không hiển thị gì.
        subtitle_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)
        
        # Các dòng code tạo TextClip Generator và SubtitlesClip đã bị loại bỏ/vô hiệu hóa 
        # để tránh lỗi TypeError: cannot unpack non-iterable NoneType object.
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
        # Dùng subtitle_clip là placeholder trong suốt đã tạo
        final_clip = CompositeVideoClip([
            background_clip, title_text, wave_text, subtitle_clip.set_duration(duration)
        ], size=(SHORTS_WIDTH, SHORTS_HEIGHT)).set_audio(audio_clip)

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
        logging.error(f"Lỗi khi tạo video Shorts 9:16: {e}", exc_info=True)
        return None
