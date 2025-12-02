# scripts/create_video.py
import logging
import os
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip,
    ColorClip, CompositeVideoClip
)
from utils import get_path

logger = logging.getLogger(__name__)


def create_video(audio_path, episode_id):
    try:
        # 1. LOAD AUDIO
        audio = AudioFileClip(audio_path)
        duration = float(audio.duration)

        if duration < 1:
            logger.error("❌ Audio quá ngắn hoặc lỗi.")
            return None

        # 2. LOAD BACKGROUND + AUTO LOOP SAFE
        bg_video_path = get_path('assets', 'video', 'pp-podcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')

        clip = None

        if os.path.exists(bg_video_path):
            logger.info(f"🎥 Dùng video nền: {bg_video_path}")
            try:
                base = VideoFileClip(bg_video_path).set_audio(None).resize((1920, 1080))
                # Auto loop chính xác bằng audio.duration
                clip = base.loop(duration=duration)
            except Exception as e:
                logger.error(f"⚠️ Lỗi video nền, fallback dùng ảnh. Lý do: {e}")
                clip = None

        # Fallback nếu video nền lỗi hoặc không có
        if clip is None:
            if os.path.exists(bg_image_path):
                logger.info("📷 Dùng ảnh nền tĩnh.")
                clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
            else:
                logger.warning("⚫ Không có nền -> tạo nền đen.")
                clip = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=duration)

        # 3. LAYER MICROPHONE ICON
        mic_path = get_path('assets', 'images', 'microphone.png')
        layers = [clip]

        if os.path.exists(mic_path):
            mic = (
                ImageClip(mic_path)
                .resize(height=330)
                .set_position(("center", "bottom"))
                .set_duration(duration)
            )
            layers.append(mic)

        # 4. GHÉP ÂM THANH
        final_video = CompositeVideoClip(layers)
        final_video = final_video.set_duration(duration)  # tránh frame chết
        final_video = final_video.set_audio(audio)

        # 5. EXPORT VIDEO (ĐÃ TỐI ƯU)
        output_path = get_path("outputs", "video", f"{episode_id}_video.mp4")
        logger.info("🎬 Render video (clean, no dead-time)...")

        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None
        )

        logger.info(f"✅ Video 16:9 hoàn tất: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi tạo video 16:9: {e}")
        return None