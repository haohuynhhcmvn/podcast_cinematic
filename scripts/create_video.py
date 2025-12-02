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
# 🌟 SPOTIFY WAVEFORM – Dạng thanh bar đều, nhảy theo âm lượng
# ============================================================
def make_spotify_waveform(audio_path, duration, width=1920, height=220):
    fps = 30
    bars = 120  # số lượng cột giống Spotify
    bar_width = width // bars

    audio = AudioSegment.from_file(audio_path)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples = samples / max_val

    # Chia audio thành "bars" đoạn
    chunk_len = len(samples) // bars
    bar_heights = []

    for i in range(bars):
        chunk = samples[i * chunk_len: (i + 1) * chunk_len]
        amp = float(np.mean(np.abs(chunk)))
        bar_heights.append(amp)

    bar_heights = np.array(bar_heights)

    mid = height // 2

    def make_frame(t):
        img = np.zeros((height, width, 3), dtype=np.uint8)

        for i, amp in enumerate(bar_heights):
            h = int(amp * (height * 0.9))
            x1 = i * bar_width
            x2 = x1 + bar_width - 1
            img[mid - h//2 : mid + h//2, x1:x2] = (255, 255, 255)

        return img

    return VideoClip(make_frame, duration=duration).set_fps(fps)


# ============================================================
# 🌟 Light Glow – minimal sexy
# ============================================================
def make_glow_layer(duration, width=1920, height=1080):
    y = np.linspace(0, height - 1, height)
    x = np.linspace(0, width - 1, width)
    xx, yy = np.meshgrid(x, y)

    cx, cy = width // 2, int(height * 0.45)
    radius = int(min(width, height) * 0.45)

    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    intensity = np.clip(255 - (dist / radius) * 255, 0, 255)

    glow = np.zeros((height, width, 3), dtype=np.uint8)
    glow[:, :, :] = (intensity * 0.25).astype(np.uint8).reshape(height, width, 1)

    return ImageClip(glow).set_duration(duration).set_opacity(0.18)


# ============================================================
# 🎬 CREATE VIDEO – KHÔNG BAO GIỜ TỰ KÉO DÀI VIDEO
# ============================================================
def create_video(audio_path, episode_id):
    try:
        # 🔥 Video chỉ được dài bằng TTS
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"🎧 Audio duration = {duration:.2f}s (video sẽ đúng bằng thời gian này)")

        # Background
        bg_video_path = get_path('assets', 'video', 'podcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')

        if os.path.exists(bg_video_path):
            clip = VideoFileClip(bg_video_path).set_audio(None).resize((1920, 1080)).loop(duration=duration)
        elif os.path.exists(bg_image_path):
            clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
        else:
            clip = ColorClip(size=(1920, 1080), color=(0,0,0), duration=duration)

        # Light glow
        glow = make_glow_layer(duration)

        # Spotify Waveform
        waveform = make_spotify_waveform(audio_path, duration, width=1920, height=200)
        waveform = waveform.set_position(("center", "bottom"))

        # Micro icon (optional)
        mic_path = get_path('assets', 'images', 'microphone.png')
        mic = None
        if os.path.exists(mic_path):
            mic = (
                ImageClip(mic_path)
                .set_duration(duration)
                .resize(height=260)
                .set_pos(("center", "bottom"))
            )

        layers = [clip, glow, waveform]
        if mic:
            layers.append(mic)

        final = CompositeVideoClip(layers).set_audio(audio)

        # Export
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")

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