# scripts/create_video.py (ĐÃ KÍCH HOẠT HÌNH ẢNH NỀN VÀ MICRO)
import os
import logging
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip, file_to_subtitles 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

# Đường dẫn TĨNH đến file ảnh trong thư mục assets/images
ASSET_DIR = 'assets/images'
BACKGROUND_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'background.jpg'), os.path.join(ASSET_DIR, 'background.png')]
MICRO_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'microphone.png'), os.path.join(ASSET_DIR, 'microphone.jpg')]

def file_to_subtitles_safe(filename):
    """
    HÀM BỎ QUA TẠM THỜI: Luôn trả về list rỗng để bỏ qua phụ đề trong CompositeVideoClip.
    """
    logging.warning(f"Bỏ qua phụ đề cho video 16:9 để hoàn thành pipeline.")
    return []

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Generator cho Subtitle (vẫn cần được định nghĩa)
        generator = lambda txt: mp.TextClip(txt, fontsize=50, color='white', font='Arial-Bold',
                                         stroke_color='black', stroke_width=2)
        
        subtitles_data = file_to_subtitles_safe(subtitle_path)
        subtitle_clip_to_use = None
        
        # Vì subtitles_data là rỗng, ta tạo một clip trong suốt để placeholder
        if not subtitles_data:
             logging.info("Tạo placeholder trong suốt thay cho SubtitlesClip.")
             subtitle_clip_to_use = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)
        else:
             subtitle_clip = SubtitlesClip(subtitles_data, generator)
             subtitle_clip_to_use = subtitle_clip.set_pos(('center', 'bottom')).margin(bottom=50)
             subtitle_clip_to_use = subtitle_clip_to_use.set_duration(duration)

        # Nền (Background) - KÍCH HOẠT IMAGECLIP
        background_path = next((p for p in BACKGROUND_IMAGE_PATHS if os.path.exists(p)), None)
        if background_path:
             logging.info(f"Sử dụng ảnh nền từ: {background_path}")
             background_clip = mp.ImageClip(background_path, duration=duration).resize(newsize=(VIDEO_WIDTH, VIDEO_HEIGHT))
        else:
             logging.warning("Không tìm thấy ảnh nền. Sử dụng nền đen.")
             background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)

        # Sóng âm & Micro CLIP (KÍCH HOẠT MICRO VÀ PLACEHOLDER SÓNG ÂM)
        micro_path = next((p for p in MICRO_IMAGE_PATHS if os.path.exists(p)), None)
        if micro_path:
             logging.info(f"Sử dụng ảnh micro từ: {micro_path}")
             # Resize micro_clip, margin(bottom=50, left=50) là các tham số hợp lý
             micro_clip = mp.ImageClip(micro_path, duration=duration).set_pos(('left', 'bottom')).resize(height=VIDEO_HEIGHT * 0.15).margin(bottom=50, left=50)
        else:
             logging.warning("Không tìm thấy ảnh Micro. Sử dụng Placeholder Text.")
             micro_clip = mp.TextClip("Micro Placeholder", fontsize=40, color='red').set_duration(duration).set_pos(('left', 'bottom'))
             
        # Sóng Âm (Vẫn là Placeholder Text)
        waveform_placeholder = mp.TextClip("SÓNG ÂM THANH CHƯA TÍCH HỢP", fontsize=40, color='white', size=(VIDEO_WIDTH * 0.8, None))
        waveform_clip = waveform_placeholder.set_duration(duration).set_pos(("center", VIDEO_HEIGHT * 0.7)) 
        
        # Ghép các thành phần
        final_clip = mp.CompositeVideoClip([
            background_clip, 
            micro_clip,              # THÊM CLIP MICRO
            waveform_clip, 
            subtitle_clip_to_use
        ], size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # Xuất Video
        output_dir = os.path.join('outputs', 'video')
        os.makedirs(output_dir, exist_ok=True) # Đảm bảo thư mục tồn tại
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
