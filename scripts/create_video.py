# scripts/create_video.py
import os
import logging
# Import này bây giờ sẽ HOẠT ĐỘNG nhờ requirements.txt đã sửa
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        if not os.path.exists(final_audio_path):
            logging.error(f"Không tìm thấy file audio: {final_audio_path}")
            return None

        logging.info(f"Đang xử lý audio: {final_audio_path}")
        
        # Tải Audio
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Cấu hình Subtitle (Dùng ImageMagick backend của MoviePy 1.0.3)
        # Lưu ý: Font 'Arial-Bold' có thể cần thay bằng đường dẫn font cụ thể nếu lỗi trên Linux
        # Nếu lỗi font, thử thay 'Arial-Bold' bằng 'DejaVu-Sans-Bold' (có sẵn trên Ubuntu)
        generator = lambda txt: mp.TextClip(txt, fontsize=50, color='white', font='DejaVu-Sans-Bold', 
                                         stroke_color='black', stroke_width=2)
        
        subtitle_clip = SubtitlesClip(subtitle_path, generator)
        subtitle_clip = subtitle_clip.set_pos(('center', 'bottom')).margin(bottom=50)

        # Tạo Nền
        background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # Tạo Text Sóng âm giả lập
        wave_text = mp.TextClip("PODCAST ON AIR", fontsize=60, color='white', font='DejaVu-Sans-Bold',
                             size=(VIDEO_WIDTH * 0.8, None), bg_color='transparent')
        waveform_clip = wave_text.set_duration(duration).set_pos("center")
        
        # Ghép Video
        final_clip = mp.CompositeVideoClip([
            background_clip, waveform_clip, subtitle_clip.set_duration(duration)
        ], size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # Xuất file
        output_dir = os.path.join('outputs', 'video')
        os.makedirs(output_dir, exist_ok=True)
        
        video_filename = f"{episode_id}_full_podcast_169.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu render video 16:9 xuống: {video_path}")
        # preset='ultrafast' giúp render nhanh hơn trên CI/CD
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, preset='ultrafast', logger='bar'
        )
        
        logging.info(f"Render thành công: {video_path}")
        return video_path
        
    except Exception as e:
        logging.error(f"Lỗi nghiêm trọng khi tạo video: {e}", exc_info=True)
        return None
