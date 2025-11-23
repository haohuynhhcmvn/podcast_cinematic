# scripts/create_shorts.py (ĐÃ KÍCH HOẠT HÌNH ẢNH NỀN VÀ MICRO)
import os
import logging
from moviepy.editor import *
from moviepy.video.tools.subtitles import SubtitlesClip 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) 

# Đường dẫn TĨNH đến file ảnh trong thư mục assets/images
ASSET_DIR = 'assets/images'
BACKGROUND_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'background.jpg'), os.path.join(ASSET_DIR, 'background.png')]
MICRO_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'microphone.png'), os.path.join(ASSET_DIR, 'microphone.jpg')]

def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # --- BỎ QUA PHỤ ĐỀ: LOGIC ĐẢM BẢO HOÀN THÀNH ---
        logging.warning("BỎ QUA PHỤ ĐỀ cho video Shorts để hoàn thành pipeline.")
        subtitle_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)
        # --- END LOGIC BỎ QUA ---

        # Nền - KÍCH HOẠT IMAGECLIP (Sử dụng ảnh đã lưu tại assets/images)
        background_path = next((p for p in BACKGROUND_IMAGE_PATHS if os.path.exists(p)), None)
        if background_path:
             logging.info(f"Sử dụng ảnh nền Shorts từ: {background_path}")
             background_clip = ImageClip(background_path, duration=duration).resize(newsize=(SHORTS_WIDTH, SHORTS_HEIGHT))
        else:
             logging.warning("LỖI: Không tìm thấy ảnh nền trong assets/images/. Sử dụng nền đen.")
             background_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # Tiêu đề
        title_text = TextClip(f"PODCAST: {episode_id}", fontsize=80, color='yellow', font='Arial-Bold', 
                              size=(SHORTS_WIDTH * 0.9, None), bg_color='black')
        title_text = title_text.set_duration(duration).set_pos(('center', SHORTS_HEIGHT * 0.1))

        # Micro (Kích hoạt lại logic hình ảnh micro)
        micro_path = next((p for p in MICRO_IMAGE_PATHS if os.path.exists(p)), None)
        if micro_path:
             logging.info(f"Sử dụng ảnh micro từ: {micro_path}")
             micro_clip = ImageClip(micro_path, duration=duration).set_pos(('center', SHORTS_HEIGHT * 0.8)).resize(height=SHORTS_HEIGHT * 0.10)
        else:
             logging.warning("LỖI: Không tìm thấy ảnh Micro trong assets/images/. Sử dụng Placeholder Text.")
             micro_clip = TextClip("Micro", fontsize=40, color='red').set_duration(duration).set_pos(('center', SHORTS_HEIGHT * 0.8))

        # Sóng âm (Vẫn là Placeholder cho đến khi logic vẽ sóng được thêm)
        wave_placeholder = TextClip("SÓNG ÂM THANH CHƯA TÍCH HỢP", fontsize=40, color='white', size=(SHORTS_WIDTH * 0.8, None))
        wave_text = wave_placeholder.set_duration(duration).set_pos(("center", SHORTS_HEIGHT * 0.45))
        
        # Ghép các thành phần
        final_clip = CompositeVideoClip([
            background_clip, 
            title_text, 
            wave_text, 
            micro_clip, 
            subtitle_clip.set_duration(duration)
        ], size=(SHORTS_WIDTH, SHORTS_HEIGHT)).set_audio(audio_clip)

        # Xuất Video
        output_dir = os.path.join('outputs', 'shorts')
        os.makedirs(output_dir, exist_ok=True) # Đảm bảo thư mục tồn tại
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
