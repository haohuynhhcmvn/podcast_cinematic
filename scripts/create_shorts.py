# scripts/create_shorts.py
import logging
import os
from moviepy.editor import AudioFileClip, VideoFileClip, ImageClip, ColorClip, TextClip, CompositeVideoClip
from utils import get_path

logger = logging.getLogger(__name__)

# Cấu hình Shorts
SHORTS_SIZE = (1080, 1920)
MAX_DURATION = 60 # YouTube Shorts tối đa 60s

def create_shorts(audio_path, episode_id):
    try:
        # 1. Xử lý Audio (Cắt ngắn nếu quá 60s)
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        if duration > MAX_DURATION:
            audio = audio.subclip(0, MAX_DURATION)
            duration = MAX_DURATION

        # 2. Load Background Video (Ưu tiên mp4 dọc)
        bg_video_path = get_path('assets', 'video', 'podcast_loop_bg_short.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background_shorts.png')

        if os.path.exists(bg_video_path):
            logger.info(f"📱 Sử dụng nền Video Shorts: {bg_video_path}")
            # Load video, resize về 1080x1920, và loop
            clip = VideoFileClip(bg_video_path).resize(SHORTS_SIZE).loop(duration=duration)
            
        elif os.path.exists(bg_image_path):
            logger.info("📷 Dùng ảnh nền Shorts tĩnh.")
            clip = ImageClip(bg_image_path).set_duration(duration).resize(SHORTS_SIZE)
        
        else:
            clip = ColorClip(size=SHORTS_SIZE, color=(30, 30, 30), duration=duration)

        # 3. Tạo danh sách các lớp video (Layers)
        final_elements = [clip]

        # 4. Thêm Text Tiêu đề (Bọc trong try/except để tránh lỗi ImageMagick)
        try:
            # Lưu ý: Cần cài ImageMagick để chạy TextClip
            txt_clip = TextClip(
                "THEO DẤU CHÂN\nHUYỀN THOẠI", 
                fontsize=80, color='white', font='Arial-Bold', method='caption', 
                size=(900, None), stroke_color='black', stroke_width=2
            )
            # Đặt text ở phần trên của video
            txt_clip = txt_clip.set_position(('center', 250)).set_duration(duration)
            final_elements.append(txt_clip)
        except Exception as e:
            logger.warning(f"⚠️ Không thể tạo Text (ImageMagick chưa cài?). Bỏ qua text.")

        # 5. Thêm Micro (Nếu có)
        mic_path = get_path('assets', 'images', 'microphone.png')
        if os.path.exists(mic_path):
            # Micro nhỏ hơn chút cho vừa màn hình điện thoại
            mic = ImageClip(mic_path).set_duration(duration).resize(width=350).set_position(('center', 'center'))
            final_elements.append(mic)

        # 6. Render
        final = CompositeVideoClip(final_elements, size=SHORTS_SIZE).set_audio(audio)
        output_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        
        logger.info("📱 Đang render Shorts...")
        # Preset 'ultrafast' giúp render video ngắn cực nhanh
        final.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', logger=None)
        
        logger.info(f"✅ Shorts hoàn tất: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi tạo Shorts: {e}")
        return None
