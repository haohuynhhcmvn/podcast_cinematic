# scripts/create_video.py (ĐÃ SỬA LỖI CUỐI CÙNG: SRT Parsing)
import os
import logging
import moviepy.editor as mp
# Cần import file_to_subtitles để bọc hàm parse an toàn
from moviepy.video.tools.subtitles import SubtitlesClip, file_to_subtitles 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

def file_to_subtitles_safe(filename):
    """Hàm an toàn để đọc file SRT và trả về list phụ đề."""
    try:
        # Sử dụng hàm chuẩn của moviepy để phân tích cú pháp
        subtitles = file_to_subtitles(filename)
        # Bắt trường hợp hàm trả về None hoặc list rỗng
        if not subtitles:
            logging.warning(f"File SRT rỗng hoặc không có dữ liệu tại {filename}. Sử dụng phụ đề trống.")
            return []
        return subtitles
    except Exception as e:
        # Bắt các lỗi cú pháp và trả về list rỗng
        logging.error(f"Lỗi phân tích cú pháp file SRT ({filename}): {e}. Sử dụng phụ đề trống.", exc_info=True)
        return []

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        # Đảm bảo tất cả các hàm MoviePy đều được gọi bằng tiền tố mp.
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Generator cho Subtitle (font cho 16:9)
        generator = lambda txt: mp.TextClip(txt, fontsize=50, color='white', font='Arial-Bold',
                                         stroke_color='black', stroke_width=2)
        
        # --- KHU VỰC SỬA LỖI: Sử dụng hàm an toàn để lấy phụ đề ---
        subtitles_data = file_to_subtitles_safe(subtitle_path)
        
        if not subtitles_data:
             # Nếu phụ đề rỗng/lỗi, tạo clip trong suốt/trống để tránh crash
             # Đảm bảo clip có duration và có kích thước
             subtitle_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)
        else:
             # Truyền trực tiếp dữ liệu phụ đề đã parse (list of tuples)
            subtitle_clip = SubtitlesClip(subtitles_data, generator)
            
        subtitle_clip = subtitle_clip.set_pos(('center', 'bottom')).margin(bottom=50)

        # Nền (Background)
        background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # Sóng âm & Micro (Dùng Placeholder đơn giản để tránh dependency phức tạp)
        wave_text = mp.TextClip("Sóng Âm Đang Chạy...", fontsize=40, color='white',
                             size=(VIDEO_WIDTH * 0.8, None), bg_color='black')
        waveform_clip = wave_text.set_duration(duration).set_pos(("center", VIDEO_HEIGHT // 2 - 50))
        
        # Ghép các thành phần
        final_clip = mp.CompositeVideoClip([
            background_clip, waveform_clip, subtitle_clip.set_duration(duration)
        ], size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

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
