import logging
import os
import numpy as np
from pydub import AudioSegment
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip, CompositeVideoClip, VideoClip
)
from utils import get_path

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# 🌟 WAVEFORM SAFE — không dùng MoviePy (tránh lỗi index âm)
# ------------------------------------------------------------
def make_waveform_safe(audio_path, duration, width=1920, height=220):
    fps = 30

    # 1. Load audio bằng pydub → luôn an toàn
    audio = AudioSegment.from_file(audio_path)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    # Stereo → mono
    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    # Chuẩn hóa
    if np.max(np.abs(samples)) > 0:
        samples = samples / np.max(np.abs(samples))

    # Resample theo frame video
    num_frames = int(duration * fps)
    idx = np.linspace(0, len(samples) - 1, num_frames).astype(int)
    waveform = samples[idx]

    # Vẽ waveform theo thời gian
    def make_frame(t):
        if t < 0:
            t = 0
        if t >= duration:
            t = duration - 0.0001

        frame_id = int(t * fps)
        frame_id = max(0, min(frame_id, len(waveform) - 1))
        amp = waveform[frame_id]

        img = np.zeros((height, width, 3), dtype=np.uint8)

        mid = height // 2
        amp_px = int(abs(amp) * (height * 0.45))

        color = (255, 255, 255)

        # Vẽ vertical line waveform
        for x in range(width):
            img[mid - amp_px: mid + amp_px, x] = color

        return img

    return VideoClip(make_frame, duration=duration).set_fps(fps)


# ------------------------------------------------------------
# 🌟 Hiệu ứng LIGHT GLOW cho nền
# ------------------------------------------------------------
def make_glow_layer(duration, width=1920, height=1080):
    import cv2

    glow = np.zeros((height, width, 3), dtype=np.uint8)

    # Vòng tròn ánh sáng ở giữa, mờ dần
    center = (width // 2, int(height * 0.45))
    radius = int(min(width, height) * 0.45)

    for y in range(height):
        for x in range(width):
            dist = ((x - center[0]) ** 2 + (y - center[1]) ** 2) ** 0.5
            intensity = max(0, 255 - (dist / radius) * 255)
            glow[y, x] = (intensity * 0.3, intensity * 0.3, intensity * 0.3)

    clip = ImageClip(glow).set_duration(duration)
    return clip.set_opacity(0.2)  # nhẹ nhàng, sang trọng


# ------------------------------------------------------------
# 🎬 FUNCTION TẠO VIDEO
# ------------------------------------------------------------
def create_video(audio_path, episode_id):
    try:
        # 1. Load audio
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"🎧 Audio final length: {duration:.2f}s")

        # 2. Load background
        bg_video_path = get_path('assets', 'video', 'podcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')

        if os.path.exists(bg_video_path):
            logger.info("🎥 Using background VIDEO")
            clip = VideoFileClip(bg_video_path).set_audio(None).resize((1920, 1080)).loop(duration=duration)
        elif os.path.exists(bg_image_path):
            logger.info("📷 Using background image")
            clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
        else:
            logger.warning("⚠ No BG asset found → using BLACK screen")
            clip = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=duration)

        # 3. Hiệu ứng Light Glow
        glow = make_glow_layer(duration)

        # 4. Microphone Icon
        mic_path = get_path('assets', 'images', 'microphone.png')
        mic = None
        if os.path.exists(mic_path):
            mic = (
                ImageClip(mic_path)
                .set_duration(duration)
                .resize(height=300)
                .set_pos(("center", "bottom"))
            )

        # 5. Waveform SAFE
        logger.info("📈 Rendering WAVEFORM…")
        waveform_clip = make_waveform_safe(audio_path, duration, width=1920, height=220)
        waveform_clip = waveform_clip.set_position(("center", "bottom"))

        # 6. Composite final video
        layers = [clip, glow, waveform_clip]
        if mic:
            layers.append(mic)

        final = CompositeVideoClip(layers).set_audio(audio)

        # 7. Output
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