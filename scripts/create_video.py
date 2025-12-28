# === scripts/create_video.py ===
# PHIÊN BẢN PRODUCTION – NO WAVEFORM
# - Bỏ waveform (giảm CPU/RAM, tăng ổn định)
# - Cache static background image (B2)
# - Giữ cinematic output
# - CI-safe, scale tốt

import logging
import os
import hashlib
import numpy as np

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
    TextClip,
    vfx
)

from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

# ============================================================
# 🧠 B2. CACHE STATIC BACKGROUND IMAGE
# ============================================================
def get_cached_background_image(bg_image_path, width, height):
    """
    Cache background image sau resize để tái sử dụng.
    NON-BREAKING – không đổi cinematic output.
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

        # --- STATIC IMAGE BACKGROUND (CACHED) ---
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

        return CompositeVideoClip(
            layers,
            size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)
        ).set_duration(duration)

    except Exception as e:
        logger.error(f"❌ Background error: {e}", exc_info=True)
        return ColorClip(
            (OUTPUT_WIDTH, OUTPUT_HEIGHT),
            (15, 15, 15),
            duration=duration
        )


# ============================================================
# ✨ 3. GLOW LAYER (NHẸ – TẠO CHIỀU SÂU)
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
# 🎬 4. MAIN PIPELINE
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"Audio duration: {duration:.2f}s")

        # --- STATIC ASSETS ---
        char_overlay = create_static_overlay_image(custom_image_path)

        bg_video = get_path("assets", "video", "long_background.mp4")
        bg_image = get_path("assets", "images", "default_background.png")

        background = make_hybrid_video_background(
            bg_video,
            bg_image,
            char_overlay,
            duration
        )

        glow = make_glow_layer(duration)

        # --- TITLE ---
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

        # --- LOGO ---
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

        # --- COMPOSE ---
        layers = [background, glow]
        if title_layer:
            layers.append(title_layer)
        if logo_layer:
            layers.append(logo_layer)

        final = CompositeVideoClip(
            layers,
            size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)
        ).set_audio(audio)

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

        # --- CLEANUP ---
        final.close()
        audio.close()
        background.close()
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
