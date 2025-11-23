# scripts/create_video.py (Đã sửa lỗi gọi hàm MoviePy)
import os
import logging
import moviepy.editor as mp # Dòng này vẫn OK

# SỬA: Phải import các hàm từ moviepy.editor MÀ KHÔNG DÙNG mp.
# Nếu bạn dùng `from moviepy.editor import *` cũ, các hàm này sẽ hoạt động
# Vì bạn dùng `import moviepy.editor as mp`, bạn phải gọi chúng qua `mp.`
# Chúng ta sẽ import trực tiếp những gì không cần gọi qua mp.

# Bổ sung: Tự động import các hàm cần thiết từ thư viện đã được import là 'mp'
from moviepy.video.tools.subtitles import SubtitlesClip
# CHÚ Ý: BẠN CẦN THAY THẾ TOÀN BỘ CÁC HÀM CŨ BẰNG HÀM CÓ TIỀN TỐ MP.
# Dưới đây là giả định các hàm bạn dùng (từ snippet): AudioFileClip, TextClip, ColorClip, CompositeVideoClip

# ĐỊNH NGHĨA LẠI CÁC HÀM DÙNG MP.
AudioFileClip = mp.AudioFileClip
TextClip = mp.TextClip
ColorClip = mp.ColorClip
CompositeVideoClip = mp.CompositeVideoClip
# --- KẾT THÚC CÁC SỬA ĐỔI ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        # SỬA LỖI Ở ĐÂY: Dùng AudioFileClip (đã được định nghĩa lại ở trên)
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Generator cho Subtitle (font cho 16:9)
        generator = lambda txt: TextClip(txt, fontsize=50, color='white', font='Arial-Bold', 
                                         stroke_color='black', stroke_width=2)
        subtitle_clip = SubtitlesClip(subtitle_path, generator)
        subtitle_clip = subtitle_clip.set_pos(('center', 'bottom')).margin(bottom=50)

        # Nền (Background)
        background_clip = ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # Sóng âm & Micro (Dùng Placeholder đơn giản để tránh dependency phức tạp)
        wave_text = TextClip("Sóng Âm Đang Chạy...", fontsize=40, color='white', 
                             size=(VIDEO_WIDTH * 0.8, None), bg_color='black')
        waveform_clip = wave_text.set_duration(duration).set_pos(("center", VIDEO_HEIGHT // 2 - 50))
        
        # Ghép các thành phần
        final_clip = CompositeVideoClip([
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
        logging.error(f"Lỗi khi tạo video 16:9: {e}")
        return None
