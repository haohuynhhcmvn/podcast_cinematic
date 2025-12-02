import logging
import os
import numpy as np
from pydub import AudioSegment
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip, CompositeVideoClip, VideoClip
)
from utils import get_path

logger = logging.getLogger(__name__)


# ============================================================
# 🌟 WAVEFORM SAFE — Không dùng MoviePy để đọc âm thanh
# ============================================================
def make_waveform_safe(audio_path, duration, width=1920, height=220):
    fps = 30

    # Load audio bằng pydub → an toàn
    audio = AudioSegment.from_file(audio_path)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    # Stereo → Mono
    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    # Normal hóa
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples = samples / max_val

    # Resample theo khung waveform
    num_frames = int(duration * fps)
    idx = np.linspace(0, len(samples) - 1, num_frames).astype(int)
    waveform = samples[idx]

    # Precompute pixel array để vẽ nhanh
    mid = height // 2

    def make_frame(t):
        t = max(0, min(t, duration))
        frame_id = int(t * fps)
        frame_id = max(0, min(frame_id, len(waveform) - 1))

        amp = abs(waveform[frame_id])
        amp_px = int(amp * (height * 0.45))

        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[mid - amp_px: mid + amp_px, :] = (255, 255, 255)

        return img

    return VideoClip(make_frame, duration=duration).set_fps(fps)


# ============================================================
# 🌟 Hiệu ứng LIGHT GLOW — tối ưu bản nhanh
# ============================================================
def make_glow_layer(duration, width=1920, height=1080):
    y = np.linspace(0, height - 1, height)
    x = np.linspace(0, width - 1, width)
    xx, yy = np.meshgrid(x, y)

    cx, cy = width // 2, int(height * 0.45)
    radius = int(min(width, height) * 0.45)

    distance = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    intensity = np.clip(255 - (distance / radius) * 255, 0, 255)

    glow = np.zeros((height, width, 3), dtype=np.uint8)
    glow[:, :, 0] = (intensity * 0.3).astype(np.uint8)
    glow[:, :, 1] = (intensity * 0.3).astype(np.uint8)
    glow[:, :, 2] = (intensity * 0.3).astype(np.uint8)

    clip = ImageClip(glow).set_duration(duration)
    return clip.set_opacity(0.22)


# ============================================================
# 🎬 FUNCTION TẠO VIDEO
# ============================================================
def create_video(audio_path, episode_id):
    try:
        # 1. Load audio
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"🎧 Audio final length: {duration:.2f}s")

        # 2. Load background asset
        bg_video_path = get_path('assets', 'video', 'podcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')

        if os.path.exists(bg_video_path):
            logger.info("🎥 Using background VIDEO")
            clip = VideoFileClip(bg_video_path).set_audio(None).resize((1920, 1080)).loop(duration=duration)
        elif os.path.exists(bg_image_path):
            logger.info("📷 Using background image")
            clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
        else:
            logger.warning("⚠ No BG asset → black screen")
            clip = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=duration)

        # 3. Light Glow
        glow = make_glow_layer(duration)

        # 4. Micro icon
        mic_path = get_path('assets', 'images', 'microphone.png')
        mic = None
        if os.path.exists(mic_path):
            mic = (
                ImageClip(mic_path)
                .set_duration(duration)
                .resize(height=280)
                .set_pos(("center", "bottom"))
            )

        # 5. Waveform SAFE
        logger.info("📈 Rendering SAFE WAVEFORM…")
        waveform = make_waveform_safe(audio_path, duration, width=1920, height=200)
        waveform = waveform.set_position(("center", "bottom"))

        # 6. Composite layers
        layers = [clip, glow, waveform]
        if mic:
            layers.append(mic)

        final = CompositeVideoClip(layers).set_audio(audio)

        # 7. Export
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        logger.info("🎬 Rendering final video…")

        final.write_videofile(
            output,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="superfast",
            threads=4,
            logger=None,
        )

        logger.info(f"✅ DONE: {output}")
        return output

    except Exception as e:
        logger.error(f"❌ VIDEO ERROR: {e}", exc_info=True)
        return None