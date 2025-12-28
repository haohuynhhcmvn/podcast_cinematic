# === scripts/create_video.py ===
# PHIÊN BẢN NÂNG CẤP – PHASE B + B2
# - Waveform pre-render + cache
# - Cache static background image
# - Giảm CPU / RAM / CI timeout
# - Giữ nguyên cinematic output

import logging
import os
import math
import hashlib
import numpy as np
from pydub import AudioSegment

from PIL import Image, ImageFilter, ImageChops
import PIL.Image

# ===== FIX PILLOW / MOVIEPY =====
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    else:
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# =================================

from moviepy.editor import (
    AudioFileClip,
    VideoFileClip,
    ImageClip,
    ColorClip,
    CompositeVideoClip,
    VideoClip,
    TextClip,
    vfx
)

from utils import get_path, file_md5

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

# ============================================================
# 🧠 B2. CACHE STATIC BACKGROUND IMAGE
# ============================================================
def get_cached_background_image(bg_image_path, width, height):
    """
    Cache background image sau resize để tái sử dụng.
    NON-BREAKING – không đổi output.
    """
    cache_dir = get_path("assets", "temp", "bg_cache")
    os.makedirs(cache_dir, exist_ok=True)

    key_raw = f"{bg_image_path}_{width}x{height}"
    cache_key = hashlib.md5(key_raw.encode()).hexdigest()
    cache_path = os.path.join(cache_dir, f"bg_{cache_key}.png")

    if os.path.exists(cache_path):
        logger.info("🎯 BG cache hit")
        return cache_path

    logger.info("🆕 Creating BG cache")
    img = Image.open(bg_image_path).convert("RGB")
    img = img.resize((width, height), Image.LANCZOS)
    img.save(cache_path, "PNG")

    return cache_path


# ============================================================
# 🎨 1. CREATE CHARACTER OVERLAY (DOUBLE EXPOSURE)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info("   (BG): Processing character overlay...")
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")

            new_h = height
            new_w = int(char_img.width * (new_h / char_img.height))
            char_img = char_img.resize((new_w, new_h), Image.LANCZOS)

            alpha = char_img.getchannel("A")
            eroded = alpha.filter(ImageFilter.MinFilter(25))
            soft_mask = eroded.filter(ImageFilter.GaussianBlur(45))

            opacity_layer = Image.new("L", soft_mask.size, 190)
            final_mask = ImageChops.multiply(soft_mask, opacity_layer)

            x = (width - new_w) // 2
            y = height - new_h
            final_overlay.paste(char_img, (x, y), mask=final_mask)

        except Exception as e:
            logger.error(f"❌ Character overlay error: {e}")

    out_path = get_path("assets", "temp", "char_overlay.png")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    final_overlay.save(out_path, "PNG")
    return out_path


# ============================================================
# 🎥 2. HYBRID CINEMATIC BACKGROUND
# ============================================================
def make_hybrid_video_background(video_path, bg_image_path, char_overlay_path, duration):
    try:
        layers = []

        # --- STATIC IMAGE BACKGROUND (B2 CACHE) ---
        if bg_image_path and os.path.exists(bg_image_path):
            cached_bg = get_cached_background_image(
                bg_image_path,
                OUTPUT_WIDTH,
                OUTPUT_HEIGHT
            )

            bg = (
                ImageClip(cached_bg)
                .set_duration(duration)
                .fx(vfx.colorx, 0.9)
                .fx(vfx.lum_contrast, contrast=0.2)
            )
            layers.append(bg)

        # --- CHARACTER OVERLAY ---
        if char_overlay_path and os.path.exists(char_overlay_path):
            layers.append(ImageClip(char_overlay_path).set_duration(duration))

        # --- VIDEO OVERLAY ---
        if video_path and os.path.exists(video_path):
            overlay = VideoFileClip(video_path)
            overlay = (
                overlay.fx(vfx.loop, duration=duration)
                .resize(height=OUTPUT_HEIGHT)
                .crop(
                    x_center=OUTPUT_WIDTH / 2,
                    y_center=OUTPUT_HEIGHT / 2,
                    width=OUTPUT_WIDTH,
                    height=OUTPUT_HEIGHT
                )
                .set_opacity(0.35)
                .fx(vfx.colorx, 1.1)
            )
            layers.append(overlay)

        if not layers:
            return ColorClip(
                size=(OUTPUT_WIDTH, OUTPUT_HEIGHT),
                color=(15, 15, 15),
                duration=duration
            )

        return CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_duration(duration)

    except Exception as e:
        logger.error(f"❌ Background error: {e}", exc_info=True)
        return ColorClip((OUTPUT_WIDTH, OUTPUT_HEIGHT), (15, 15, 15), duration=duration)


# ============================================================
# 🌊 3. PRE-RENDER WAVEFORM VIDEO (CACHEABLE)
# ============================================================
def render_waveform_video(audio_path, duration, output_path):
    fps = 20
    logger.info("   (WF): Rendering waveform (cached)...")

    audio = AudioSegment.from_file(audio_path)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    frames = int(duration * fps) + 1
    step = max(1, len(samples) // frames)

    envelope = [
        np.mean(np.abs(samples[i:i + step]))
        for i in range(0, len(samples), step)
    ][:frames]

    envelope = np.array(envelope)
    envelope /= np.max(envelope) if np.max(envelope) > 0 else 1

    size = 500
    waves = 8
    center = size // 2
    yy, xx = np.ogrid[:size, :size]
    dist = np.sqrt((xx - center) ** 2 + (yy - center) ** 2)

    def make_frame(t):
        idx = min(int(t * fps), len(envelope) - 1)
        amp = envelope[idx]

        frame = np.zeros((size, size, 3), dtype=np.uint8)
        base_radius = 40 + amp * 60

        for i in range(waves):
            r = base_radius + i * 25
            opacity = max(0, 1 - i * 0.12)
            if opacity <= 0:
                continue
            ring = (dist >= r - 0.3) & (dist <= r + 0.3)
            frame[ring] = (255, 215, 0)

        return frame

    clip = (
        VideoClip(make_frame, duration=duration)
        .set_fps(fps)
        .resize((OUTPUT_WIDTH, OUTPUT_HEIGHT))
    )

    clip.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        preset="ultrafast",
        threads=2,
        audio=False,
        logger=None
    )

    clip.close()
    audio.close()


# ============================================================
# ✨ 4. GLOW LAYER
# ============================================================
def make_glow_layer(duration):
    low_w, low_h = 320, 180
    y = np.linspace(0, low_h - 1, low_h)
    x = np.linspace(0, low_w - 1, low_w)
    xx, yy = np.meshgrid(x, y)

    cx, cy = low_w // 2, int(low_h * 0.45)
    radius = int(min(low_w, low_h) * 0.45)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    intensity = np.clip(255 - (dist / radius) * 255, 0, 255)

    glow = np.zeros((low_h, low_w, 3), dtype=np.uint8)
    glow[..., 0] = (intensity * 0.7).astype(np.uint8)
    glow[..., 1] = (intensity * 0.5).astype(np.uint8)

    return (
        ImageClip(glow)
        .resize((OUTPUT_WIDTH, OUTPUT_HEIGHT))
        .set_duration(duration)
        .set_opacity(0.3)
    )


# ============================================================
# 🎬 5. MAIN PIPELINE
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"Audio duration: {duration:.2f}s")

        char_overlay = create_static_overlay_image(custom_image_path)

        bg_video = get_path("assets", "video", "long_background.mp4")
        bg_image = get_path("assets", "images", "default_background.png")

        background = make_hybrid_video_background(
            bg_video, bg_image, char_overlay, duration
        )

        glow = make_glow_layer(duration)

        audio_hash = file_md5(audio_path)
        waveform_path = get_path("assets", "temp", f"waveform_{audio_hash}.mp4")
        os.makedirs(os.path.dirname(waveform_path), exist_ok=True)

        if not os.path.exists(waveform_path):
            render_waveform_video(audio_path, duration, waveform_path)

        waveform = (
            VideoFileClip(waveform_path)
            .set_duration(duration)
            .set_position(("center", 50))
        )

        title_layer = None
        if title_text:
            try:
                title_layer = (
                    TextClip(
                        title_text.upper(),
                        fontsize=55,
                        font="DejaVu-Sans-Bold",
                        color="#FFD700",
                        stroke_color="black",
                        stroke_width=3,
                        method="caption",
                        align="West",
                        size=(800, None)
                    )
                    .set_position((50, 50))
                    .set_duration(duration)
                )
            except Exception as e:
                logger.warning(f"Title error: {e}")

        logo_layer = None
        logo_path = get_path("assets", "images", "channel_logo.png")
        if os.path.exists(logo_path):
            logo_layer = (
                ImageClip(logo_path)
                .resize(height=100)
                .set_position(("right", "top"))
                .margin(right=20, top=20, opacity=0)
                .set_duration(duration)
            )

        layers = [background, glow, waveform]
        if title_layer:
            layers.append(title_layer)
        if logo_layer:
            layers.append(logo_layer)

        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT))
        final = final.set_audio(audio)

        out_path = get_path("outputs", "video", f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        logger.info("🚀 Rendering video...")
        final.write_videofile(
            out_path,
            fps=20,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            ffmpeg_params=["-crf", "28"],
            logger="bar"
        )

        # ===== CLEANUP =====
        final.close()
        audio.close()
        background.close()
        waveform.close()
        glow.close()
        if title_layer:
            title_layer.close()
        if logo_layer:
            logo_layer.close()

        logger.info("✅ Render success")
        return out_path

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
        return False
