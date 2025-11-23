# scripts/create_video.py (Tối ưu cho MoviePy 1.0.3 trên Linux)
import os
import logging
# Import đúng cho phiên bản 1.0.3
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        if not os.path.exists(final_audio_path):
            logging.error(f"File audio không tồn tại: {final_audio_path}")
            return None

        logging.info("Đang tải Audio...")
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Cấu hình Font chữ: Dùng 'DejaVu-Sans-Bold' có sẵn trên Ubuntu/Linux
        # Nếu dùng 'Arial', ImageMagick có thể báo lỗi không tìm thấy font.
        font_name = 'DejaVu-Sans-Bold' 
        
        # Generator cho Subtitle
        generator = lambda txt: mp.TextClip(txt, fontsize=50, color='white', font=font_name, 
                                         stroke_color='black', stroke_width=2)
        
        logging.info("Đang xử lý Subtitle...")
        subtitle_clip = SubtitlesClip(subtitle_path, generator)
        subtitle_clip = subtitle_clip.set_pos(('center', 'bottom')).margin(bottom=50)

        # Nền (Background)
        background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # Text Sóng âm giả lập (Placeholder)
        wave_text = mp.TextClip("PODCAST ON AIR", fontsize=60, color='white', font=font_name,
                             size=(VIDEO_WIDTH * 0.8, None), bg_color='transparent')
        waveform_clip = wave_text.set_duration(duration).set_pos("center")
        
        # Ghép Video
        logging.info("Đang ghép video (Composite)...")
        final_clip = mp.CompositeVideoClip([
            background_clip, waveform_clip, subtitle_clip.set_duration(duration)
        ], size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # Xuất file
        output_dir = os.path.join('outputs', 'video')
        os.makedirs(output_dir, exist_ok=True)
        video_filename = f"{episode_id}_full_podcast_169.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu Render video: {video_path}")
        # preset='ultrafast' để render nhanh, threads=4 để tận dụng CPU
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, 
            preset='ultrafast', threads=4, logger='bar'
        )
        
        logging.info(f"Hoàn tất render: {video_path}")
        return video_path
        
    except Exception as e:
        logging.error(f"Lỗi Render Video: {e}", exc_info=True)
        return None
