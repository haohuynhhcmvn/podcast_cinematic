# === scripts/create_video.py ===
import logging
import os
import numpy as np
import math
from pydub import AudioSegment
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageChops
import PIL.Image

# --- [FIX QUAN TRỌNG] VÁ LỖI TƯƠNG THÍCH PILLOW/MOVIEPY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling') and hasattr(PIL.Image.Resampling, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    elif hasattr(PIL.Image, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# -----------------------------------------------------------

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, VideoClip, TextClip, concatenate_videoclips,
    vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT (DOUBLE EXPOSURE BLEND)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info("   (LOG-BG): Bắt đầu xử lý ảnh nhân vật (Double Exposure Mix)...")
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
            new_char_h = height 
            new_char_w = int(char_img.width * (new_char_h / char_img.height))
            char_img = char_img.resize((new_char_w, new_char_h), Image.LANCZOS)
            
            original_alpha = char_img.getchannel("A")
            shrink_radius = 25
            eroded_mask = original_alpha.filter(ImageFilter.MinFilter(shrink_radius))
            
            blur_radius = 45 
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(blur_radius))
            
            blend_opacity = 190 
            opacity_layer = Image.new("L", soft_edge_mask.size, blend_opacity)
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            paste_x = (width - new_char_w) // 2 
            paste_y = height - new_char_h       
            
            final_overlay.paste(char_img, (paste_x, paste_y), mask=final_mask)
            logger.info(f"   (LOG-BG): ✅ Nhân vật đã Blend xong.")
            
        except Exception as e:
            logger.error(f"   (LOG-BG): ❌ Lỗi xử lý nhân vật: {e}")

    overlay_path = get_path('assets', 'temp', "char_blend_mix.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

# ============================================================
# 🎥 HÀM 2: TẠO NỀN "CINEMATIC" (PHỐI CẢNH LỚP)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    try:
        layers_to_composite = []

        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            img_clip = img_clip.resize(height=height)
            img_clip = img_clip.crop(x_center=img_clip.w/2, y_center=img_clip.h/2, width=width, height=height)
            img_clip = img_clip.fx(vfx.colorx, factor=0.9).fx(vfx.lum_contrast, contrast=0.2)
            layers_to_composite.append(img_clip)

        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers_to_composite.append(char_clip)

        try:
            temp_clip = VideoFileClip(video_path)
            if temp_clip.duration < duration:
                num_loops = math.ceil(duration / temp_clip.duration)
                final_video = concatenate_videoclips([temp_clip] * num_loops, method="compose")
            else:
                final_video = temp_clip
            
            video_layer = final_video.subclip(0, duration).resize(height=height)
            video_layer = video_layer.crop(x_center=video_layer.w/2, y_center=video_layer.h/2, width=width, height=height)
            video_layer = video_layer.set_opacity(0.35).fx(vfx.colorx, factor=1.1)
            layers_to_composite.append(video_layer)
        except Exception:
            pass

        if not layers_to_composite:
            return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)
            
        return CompositeVideoClip(layers_to_composite, size=(width, height)).set_duration(duration)
    except Exception as e:
        logger.error(f"❌ Lỗi tổng hợp nền: {e}")
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)

# ============================================================
# ✨ HÀM 3: LỚP GLOW (HIỆU ỨNG SÁNG TÂM)
# ============================================================
def make_glow_layer(duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    low_w, low_h = 320, 180
    y, x = np.ogrid[:low_h, :low_w]
    lcx, lcy = low_w // 2, int(low_h * 0.45) 
    dist = np.sqrt((x - lcx)**2 + (y - lcy)**2)
    intensity = np.clip(255 - (dist / (low_h * 0.45)) * 255, 0, 255)
    
    glow_low = np.zeros((low_h, low_w, 3), dtype=np.uint8)
    glow_low[:, :, 0] = (intensity * 0.7).astype(np.uint8) 
    glow_low[:, :, 1] = (intensity * 0.5).astype(np.uint8) 
    
    return ImageClip(glow_low).resize((width, height)).set_duration(duration).set_opacity(0.3)

# ============================================================
# 🎬 HÀM CHÍNH: TẠO VIDEO (MAIN PIPELINE)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        char_overlay_path = create_static_overlay_image(custom_image_path)
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        static_bg_path = get_path('assets', 'images', 'default_background.png')
        
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)
        glow_layer = make_glow_layer(duration)

        title_layer = None
        if title_text:
            try:
                title_layer = TextClip(
                    title_text.upper(),
                    fontsize=55, font='DejaVu-Sans-Bold', color='#FFD700', 
                    stroke_color='black', stroke_width=3,
                    method='caption', align='West', size=(800, None)       
                ).set_position((50, 50)).set_duration(duration)
            except Exception as e:
                logger.warning(f"⚠️ Title Error: {e}")

        logo_path = get_path('assets', 'images', 'channel_logo.png')
        logo_layer = None
        if os.path.exists(logo_path):
            logo_layer = ImageClip(logo_path).set_duration(duration).resize(height=100).set_position(("right", "top")).margin(right=20, top=20, opacity=0)

        # ĐÃ LOẠI BỎ WAVEFORM_LAYER TẠI ĐÂY
        final_layers = [background_clip, glow_layer]
        if title_layer: final_layers.append(title_layer)
        if logo_layer: final_layers.append(logo_layer)
        
        final_video = CompositeVideoClip(final_layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final_video.write_videofile(
            output_path, fps=20, codec="libx264", audio_codec="aac", 
            preset="ultrafast", threads=4, ffmpeg_params=["-crf", "28"], logger=None 
        )
        
        final_video.close()
        audio.close()
        return output_path

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
        return False
