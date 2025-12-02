# scripts/create_video.py
import logging
import os
import math
import numpy as np
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip,
    ColorClip, CompositeVideoClip, VideoClip, vfx
)
from utils import get_path

logger = logging.getLogger(__name__)


def _make_vignette_image(w, h, strength=0.55):
    """
    Tạo ảnh vignette (RGBA) với vùng giữa sáng, mép tối.
    strength: 0..1 (0 none, 1 full black at edges)
    Trả về numpy array uint8 (H, W, 4)
    """
    # Tạo lưới tọa độ
    x = np.linspace(-1, 1, w)[None, :].repeat(h, axis=0)
    y = np.linspace(-1, 1, h)[:, None].repeat(w, axis=1)
    # radius từ trung tâm (0 center -> 1 corners)
    r = np.sqrt(x**2 + y**2)
    # gradient (0 center -> 1 edges)
    mask = np.clip((r - 0.5) / 0.5, 0, 1)  # adjust softness
    alpha = (mask * strength * 255).astype(np.uint8)
    # tạo lớp màu đen với alpha
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., 3] = alpha
    return rgba


def _make_grain_frame(t, w, h, intensity=0.06):
    """
    Trả về frame nhiễu (H,W,3) uint8 với giá trị gần trung tính.
    intensity: 0..0.2 (độ mạnh nhiễu)
    """
    # seed deterministic by time to avoid flicker artifacts too random (but ok)
    rnd = np.random.RandomState(int((t * 1000) % 4294967295))
    # gaussian noise centered 128
    noise = rnd.normal(loc=128, scale=30, size=(h, w, 1))
    noise = np.clip(noise, 0, 255).astype(np.uint8)
    frame = np.concatenate([noise, noise, noise], axis=2)
    # scale toward neutral 128 by intensity (so it's subtle)
    frame = (128 + (frame.astype(np.float32) - 128) * intensity).astype(np.uint8)
    return frame


def create_video(audio_path, episode_id, cinematic=True):
    """
    Create a 16:9 video synchronized with audio, with optional cinematic effects.
    cinematic=True -> add slow zoom, vignette and film grain.
    """
    try:
        # 1. LOAD AUDIO
        audio = AudioFileClip(audio_path)
        duration = float(audio.duration)

        if duration < 1:
            logger.error("❌ Audio too short or invalid.")
            return None

        # video/ image assets
        bg_video_path = get_path('assets', 'video', 'pp-podcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')
        mic_path = get_path('assets', 'images', 'microphone.png')

        clip = None

        # 2. LOAD BACKGROUND (VIDEO PREFERRED)
        if os.path.exists(bg_video_path):
            logger.info(f"🎥 Using background video: {bg_video_path}")
            try:
                base = VideoFileClip(bg_video_path).set_audio(None).resize((1920, 1080))
                clip = base.loop(duration=duration)
            except Exception as e:
                logger.warning(f"⚠️ Background video error, falling back to image. Reason: {e}")
                clip = None

        if clip is None:
            if os.path.exists(bg_image_path):
                logger.info("📷 Using background image.")
                clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
            else:
                logger.info("⚫ No background assets found; using black background.")
                clip = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=duration)

        # 3. CINEMATIC EFFECTS: slow zoom + color grade
        if cinematic:
            # slow gentle zoom-in (Ken Burns): scale from 1.0 -> 1.03 over duration
            try:
                zoom_factor = 1.03  # final zoom factor
                clip = clip.resize(lambda t: 1.0 + (zoom_factor - 1.0) * (t / max(duration, 1.0)))
            except Exception as e:
                logger.debug(f"Zoom effect failed: {e}")

            # slight color grade: reduce brightness a tiny bit then lift contrast
            try:
                clip = clip.fx(vfx.colorx, 0.98)  # slightly darker
            except Exception:
                pass

        # 4. Overlay microphone icon (bottom center)
        layers = [clip]
        if os.path.exists(mic_path):
            try:
                mic = (
                    ImageClip(mic_path)
                    .resize(height=320)
                    .set_duration(duration)
                    .set_position(("center", "bottom"))
                )
                layers.append(mic)
            except Exception as e:
                logger.debug(f"Mic overlay failed: {e}")

        # 5. Vignette overlay (soft black edges)
        if cinematic:
            try:
                w, h = 1920, 1080
                vignette_arr = _make_vignette_image(w, h, strength=0.65)
                vignette_clip = ImageClip(vignette_arr, ismask=False).set_duration(duration).set_pos(("center", "center"))
                vignette_clip = vignette_clip.set_opacity(0.75)  # adjust darkness
                layers.append(vignette_clip)
            except Exception as e:
                logger.debug(f"Vignette creation failed: {e}")

        # 6. Film grain overlay as a dynamic small-noise VideoClip
        if cinematic:
            try:
                w, h = 1920, 1080
                fps = 24

                def make_frame(t):
                    frame = _make_grain_frame(t, w, h, intensity=0.08)
                    return frame

                grain_clip = VideoClip(make_frame=make_frame, ismask=False).set_duration(duration).set_fps(fps)
                # convert to ImageClip-like overlay with low opacity
                grain_clip = grain_clip.set_opacity(0.06)  # very subtle
                layers.append(grain_clip)
            except Exception as e:
                logger.debug(f"Film grain creation failed: {e}")

        # 7. Compose final video and set audio
        final = CompositeVideoClip(layers, size=(1920, 1080))
        final = final.set_duration(duration)  # ENSURE exact sync with audio
        final = final.set_audio(audio)

        # 8. Export
        output_path = get_path("outputs", "video", f"{episode_id}_video.mp4")
        logger.info("🎬 Rendering cinematic video (no dead-time)...")

        final.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None
        )

        logger.info(f"✅ Video rendered successfully: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Error while creating video: {e}")
        return None