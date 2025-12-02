# scripts/create_video.py  (PRO EDITION)
import logging
import os
import numpy as np
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, vfx, VideoClip
)
from utils import get_path

logger = logging.getLogger(__name__)


# ------------------------------------------
# ⭐ 1) Waveform Generator
# ------------------------------------------
def make_waveform(audio_clip, duration, width=1920, height=200):
    """
    Tạo waveform động chạy theo audio (dạng sóng đơn giản, clean).
    """
    fps = 30
    samples = audio_clip.to_soundarray(fps=fps)
    # Convert stereo → mono
    if len(samples.shape) == 2:
        samples = samples.mean(axis=1)

    # Chuẩn hóa amplitude
    max_amp = np.max(np.abs(samples))
    samples = samples / (max_amp + 1e-7)

    def make_frame(t):
        index = int(t * fps)
        if index >= len(samples):
            amp = 0
        else:
            amp = samples[index]

        # tạo ảnh waveform
        img = np.zeros((height, width, 3), dtype=np.uint8)

        mid = height // 2
        amp_px = int(amp * (height * 0.4))

        color = (255, 255, 255)  # white waveform

        # vẽ vertical line
        for x in range(width):
            img[mid - amp_px : mid + amp_px, x] = color

        return img

    return VideoClip(make_frame, duration=duration).set_fps(fps)


# ------------------------------------------
# ⭐ 2) Light Glow Overlay
# ------------------------------------------
def make_light_glow(duration):
    glow = ColorClip(size=(1920, 1080), color=(255, 255, 255))
    glow = glow.set_opacity(0.065)          # ánh sáng rất nhẹ
    glow = glow.set_duration(duration)
    glow = glow.fx(vfx.fadein, 1).fx(vfx.fadeout, 1)
    return glow


# ------------------------------------------
# ⭐ 3) Main Video Render
# ------------------------------------------
def create_video(audio_path, episode_id):
    try:
        # Load Audio
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # Background
        bg_video_path = get_path('assets', 'video', 'pp-podcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')

        if os.path.exists(bg_video_path):
            logger.info(f"🎥 Background video: {bg_video_path}")

            clip = (
                VideoFileClip(bg_video_path)
                .set_audio(None)
                .resize((1920, 1080))
                .fx(vfx.loop, duration=duration)         # fix chính
            )
        elif os.path.exists(bg_image_path):
            logger.info("📷 Using background image")
            clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
        else:
            logger.warning("⚠ No background asset → black screen")
            clip = ColorClip(size=(1920, 1080), color=(0,0,0), duration=duration)


        # ------------------------------------------
        # ⭐ ADD light glow layer
        # ------------------------------------------
        glow = make_light_glow(duration)

        # ------------------------------------------
        # ⭐ ADD waveform động phía dưới cùng
        # ------------------------------------------
        waveform = (
            make_waveform(audio, duration, width=1920, height=220)
            .set_position(("center", 780))  # dưới đáy video
            .set_opacity(0.85)
        )

        # ------------------------------------------
        # ⭐ Micro overlay (nếu có)
        # ------------------------------------------
        mic_path = get_path('assets', 'images', 'microphone.png')
        overlays = [clip, glow, waveform]

        if os.path.exists(mic_path):
            mic = (
                ImageClip(mic_path)
                .set_duration(duration)
                .resize(height=300)
                .set_pos(("center", "bottom"))
            )
            overlays.append(mic)

        # Composite
        final = CompositeVideoClip(overlays).set_audio(audio)

        # Output
        output = get_path("outputs", "video", f"{episode_id}_video.mp4")

        logger.info("🎬 Rendering enhanced video...")
        final.write_videofile(
            output,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            logger=None
        )

        logger.info(f"✅ Video ready: {output}")
        return output

    except Exception as e:
        logger.error(f"❌ VIDEO ERROR: {e}", exc_info=True)
        return None