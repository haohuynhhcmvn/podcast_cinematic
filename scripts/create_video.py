# scripts/create_video.py (ĐÃ SỬA LỖI LỌC NONE)
import os
import logging
import moviepy.editor as mp
# Import SubtitlesClip và file_to_subtitles từ đường dẫn chính xác của moviepy
from moviepy.video.tools.subtitles import SubtitlesClip, file_to_subtitles 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

def file_to_subtitles_safe(filename):
    """
    Hàm an toàn để đọc file SRT. Chú trọng LỌC BỎ các phần tử None trong danh sách phụ đề 
    mà moviepy có thể chèn vào khi parsing thất bại một khối.
    """
    try:
        # Sử dụng hàm chuẩn của moviepy để phân tích cú pháp
        # Kết quả raw_subtitles CÓ THỂ là một list chứa các phần tử None
        raw_subtitles = file_to_subtitles(filename)
        
        # 💡 SỬA LỖI CHỦ YẾU: Lọc bỏ tất cả các phần tử None.
        subtitles_filtered = [sub for sub in raw_subtitles if sub is not None]
        
        if not subtitles_filtered:
            logging.warning(f"File SRT rỗng hoặc không có dữ liệu hợp lệ tại {filename}. Trả về list rỗng.")
            return []
        
        return subtitles_filtered
    except Exception as e:
        # Bắt các lỗi cú pháp tổng thể
        logging.error(f"Lỗi phân tích cú pháp file SRT ({filename}): {e}. Trả về list rỗng.", exc_info=True)
        return []

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Generator cho Subtitle (font cho 16:9)
        generator = lambda txt: mp.TextClip(txt, fontsize=50, color='white', font='Arial-Bold',
                                         stroke_color='black', stroke_width=2)
        
        # Lấy dữ liệu phụ đề đã được xử lý an toàn
        subtitles_data = file_to_subtitles_safe(subtitle_path)
        
        # Dòng 53 (SubtitlesClip) trong log của bạn.
        if not subtitles_data:
             logging.warning("Phụ đề rỗng hoặc bị lỗi. Tạo clip video không phụ đề.")
             # Tạo một clip trong suốt để tránh lỗi CompositeVideoClip
             subtitle_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)
        else:
             # Truyền danh sách phụ đề đã được lọc sạch None
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
