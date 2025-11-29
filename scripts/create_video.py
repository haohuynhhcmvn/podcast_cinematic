# scripts/create_video.py
import logging
import os
from moviepy.editor import AudioFileClip, VideoFileClip, ImageClip, ColorClip, CompositeVideoClip
from utils import get_path

logger = logging.getLogger(__name__)

def create_video(audio_path, episode_id):
    try:
        # 1. Load Audio
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # 2. Load Background Video (Ưu tiên mp4)
        bg_video_path = get_path('assets', 'video', 'podcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')

        if os.path.exists(bg_video_path):
            logger.info(f"🎥 Sử dụng nền Video: {bg_video_path}")
            # Load video, resize về 1920x1080 chuẩn, và loop cho bằng độ dài audio
            clip = VideoFileClip(bg_video_path).resize((1920, 1080)).loop(duration=duration)
        
        elif os.path.exists(bg_image_path):
            logger.info("📷 Không thấy video nền, dùng ảnh tĩnh.")
            clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
        
        else:
            logger.warning("⚠️ Không có assets nền, dùng màn hình đen.")
            clip = ColorClip(size=(1920, 1080), color=(0,0,0), duration=duration)

        # 3. Thêm Micro (VỊ TRÍ MỚI)
        mic_path = get_path('assets', 'images', 'microphone.png')
        if os.path.exists(mic_path):
            # Resize micro nhỏ lại một chút (height=350) cho cân đối
            mic = ImageClip(mic_path).set_duration(duration).resize(height=350)
            
            # --- VỊ TRÍ MỚI ---
            # ('center', 'bottom'): Căn giữa theo chiều ngang, sát đáy theo chiều dọc
            # set_pos dùng từ khóa tiếng Anh là cách đơn giản và chính xác nhất.
            mic = mic.set_pos(('center', 'bottom'))
            
            # Ghép micro đè lên nền
            final = CompositeVideoClip([clip, mic])
        else:
            final = clip
            
        # 4. Gán Audio
        final = final.set_audio(audio)
        
        # 5. Xuất file
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        logger.info("🎬 Đang render Video 16:9...")
        
        # preset='fast' để render nhanh hơn, bitrate giữ chất lượng ổn
        final.write_videofile(output, fps=24, codec='libx264', audio_codec='aac', preset='fast', logger=None)
        
        logger.info(f"✅ Video 16:9 hoàn tất: {output}")
        return output

    except Exception as e:
        logger.error(f"❌ Lỗi tạo video 16:9: {e}")
        return None
