# scripts/create_video.py
import logging
import os
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

def create_video(audio_path, episode_id):
    try:
        # 1. Load audio (voice+music)
        audio = AudioFileClip(audio_path)
        duration = audio.duration   # 🎯 Video phải EXACT theo audio

        # 2. Load background
        bg_video_path = get_path('assets', 'video', 'pp-podcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')

        if os.path.exists(bg_video_path):
            logger.info(f"🎥 Using background video: {bg_video_path}")

            clip = (
                VideoFileClip(bg_video_path)
                .set_audio(None)                        # tắt audio nguồn
                .resize((1920, 1080))
                .fx(vfx.loop, duration=duration)         # ⭐ FIX CHÍNH: loop chuẩn
            )

        elif os.path.exists(bg_image_path):
            logger.info("📷 No background video, using image.")
            clip = (
                ImageClip(bg_image_path)
                .set_duration(duration)
                .resize((1920, 1080))
            )

        else:
            logger.warning("⚠️ No assets, black background used.")
            clip = ColorClip(
                size=(1920, 1080),
                color=(0,0,0),
                duration=duration
            )

        # 3. Add microphone overlay
        mic_path = get_path('assets', 'images', 'microphone.png')
        if os.path.exists(mic_path):
            mic = (
                ImageClip(mic_path)
                .set_duration(duration)
                .resize(height=350)
                .set_pos(("center", "bottom"))
            )
            final = CompositeVideoClip([clip, mic])
        else:
            final = clip

        # 4. Attach audio (voice + music)
        final = final.set_audio(audio)

        # 5. Export
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        logger.info("🎬 Rendering final video...")

        final.write_videofile(
            output,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='superfast',
            logger=None
        )

        logger.info(f"✅ DONE: {output}")
        return output

    except Exception as e:
        logger.error(f"❌ Error creating video: {e}", exc_info=True)
        return None