# scripts/create_video.py
import os
import logging
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip, file_to_subtitles 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

def file_to_subtitles_safe(filename):
    """
    Tải phụ đề từ file, trả về list rỗng nếu có lỗi phân tích file SRT (ví dụ: trả về None).
    """
    try:
        data = file_to_subtitles(filename) 
        if data is None:
            # Bắt trường hợp moviepy trả về None khi phân tích lỗi
            logging.error(f"Lỗi phân tích file SRT tại {filename}: file_to_subtitles() trả về None. Bỏ qua phụ đề.")
            return []
        return data
    except Exception as e:
        # Bắt các lỗi I/O hoặc lỗi phân tích khác
        logging.error(f"Lỗi khi đọc file phụ đề {filename}: {e}. Bỏ qua phụ đề.")
        return []

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Generator cho Subtitle (vẫn cần được định nghĩa)
        generator = lambda txt: mp.TextClip(txt, fontsize=50, color='white', font='Arial-Bold',
                                         stroke_color='black', stroke_width=2)
        
        # Lấy dữ liệu phụ đề ĐÃ ĐƯỢC XỬ LÝ AN TOÀN
        subtitles_data = file_to_subtitles_safe(subtitle_path) 
        
        # Xử lý phụ đề
        # Tạo clip placeholder mặc định (trong suốt)
        subtitle_clip_to_use = mp.ColorClip((1, 1), color=(0, 0, 0), duration=duration).set_opacity(0)
        
        if subtitles_data:
             # CHỈ CHẠY KHI CÓ DỮ LIỆU PHỤ ĐỀ HỢP LỆ (subtitles_data không phải là [] hoặc None)
             logging.info("Đang tạo SubtitlesClip...")
             subtitle_clip = SubtitlesClip(subtitles_data, generator)
             subtitle_clip_to_use = subtitle_clip.set_pos(('center', 'bottom')).margin(bottom=50)
             subtitle_clip_to_use = subtitle_clip_to_use.set_duration(duration)

        # Nền (Background)
        background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # Sóng âm & Micro Placeholder
        wave_text = mp.TextClip("Sóng Âm Đang Chạy...", fontsize=40, color='white',
                             size=(VIDEO_WIDTH * 0.8, None), bg_color='black')
        waveform_clip = wave_text.set_duration(duration).set_pos(("center", VIDEO_HEIGHT // 2 - 50))
        
        # Ghép các thành phần
        final_clip = mp.CompositeVideoClip([
            background_clip, waveform_clip, subtitle_clip_to_use
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
