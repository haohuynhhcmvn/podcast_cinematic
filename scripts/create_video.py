# === scripts/create_video.py ===
import logging
import os
import numpy as np
import math
import random
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageChops
import PIL.Image

# --- [VÁ LỖI TƯƠNG THÍCH PILLOW/MOVIEPY] ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling') and hasattr(PIL.Image.Resampling, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    elif hasattr(PIL.Image, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# -----------------------------------------------------------

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, TextClip, vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

# ============================================================
# 🎭 HÀM HIỆU ỨNG ĐỘNG (ANIMATION HELPERS)
# ============================================================
def zoom_in_effect(t, duration):
    return 1 + 0.12 * (t / duration)

def mic_vibration(t):
    base_y = OUTPUT_HEIGHT - 170
    return base_y + 3 * math.sin(2 * math.pi * 0.5 * t)

def pick_video_background(theme_text):
    theme_text = str(theme_text).lower()
    mapping = {
        "warrior": "theme_warrior.mp4",
        "visionary": "theme_visionary.mp4",
        "mystery": "theme_mystery.mp4"
    }
    fallback_video = "long_background.mp4"
    selected_file = fallback_video
    
    for key, filename in mapping.items():
        if key in theme_text:
            path = get_path('assets', 'video', filename)
            if os.path.exists(path):
                selected_file = filename
                break
    return get_path('assets', 'video', selected_file)

# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info(f"   (LOG-BG): Xử lý nhân vật AI từ nguồn: {char_path}")
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
            target_h = int(height * 0.9)
            char_img.thumbnail((width, target_h), Image.LANCZOS)
            
            offset_x = (width - char_img.width) // 2
            offset_y = (height - char_img.height) // 2

            alpha = char_img.getchannel("A")
            eroded_mask = alpha.filter(ImageFilter.MinFilter(5)) 
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(25))
            
            opacity_layer = Image.new("L", soft_edge_mask.size, 220) 
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            final_overlay.paste(char_img, (offset_x, offset_y), mask=final_mask)
            
        except Exception as e:
            logger.error(f"❌ Lỗi Pillow xử lý nhân vật: {e}")
    else:
        logger.warning("⚠️ Không tìm thấy ảnh nhân vật.")

    overlay_path = get_path('assets', 'temp', "char_blend_full.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

# ============================================================
# 🎥 HÀM 2: TẠO NỀN HYBRID
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    try:
        layers = []
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            img_clip = img_clip.resize(width=width, height=height)
            img_clip = img_clip.resize(lambda t: zoom_in_effect(t, duration))
            img_clip = img_clip.set_position(('center', 'center'))
            img_clip = img_clip.fx(vfx.colorx, factor=0.85).fx(vfx.lum_contrast, contrast=0.35)
            layers.append(img_clip)

        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            char_clip = char_clip.resize(lambda t: zoom_in_effect(t, duration))
            char_clip = char_clip.set_position(('center', 'center'))
            layers.append(char_clip)

        try:
            if os.path.exists(video_path):
                temp_clip = VideoFileClip(video_path, audio=False, target_resolution=(height, width))
                if temp_clip.duration < duration:
                    temp_clip = temp_clip.fx(vfx.loop, duration=duration)
                video_layer = temp_clip.subclip(0, duration).set_opacity(0.30).fx(vfx.colorx, factor=1.1)
                layers.append(video_layer)
        except: pass

        return CompositeVideoClip(layers, size=(width, height)).set_duration(duration)
    except Exception as e:
        logger.error(f"❌ Lỗi tạo nền Hybrid: {e}")
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)

# ============================================================
# 🎬 HÀM CHÍNH: CREATE VIDEO
# ============================================================
def create_video(audio_path, episode_id, image_path=None, title_text="", theme=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        
        char_overlay_path = create_static_overlay_image(image_path)
        base_video_path = pick_video_background(theme) 
        
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)
        final_layers = [background_clip]

        if title_text:
            try:
                title_layer = TextClip(
                    title_text.upper(), 
                    fontsize=50, font='DejaVu-Sans-Bold', color='#FFD700', 
                    stroke_color='black', stroke_width=2,
                    method='caption', align='West', size=(OUTPUT_WIDTH * 0.7, None)
                ).set_position((50, 40)).set_duration(duration)
                final_layers.append(title_layer)
            except: pass

        mic_path = get_path('assets', 'images', 'microphone.png')
        if os.path.exists(mic_path):
            mic_clip = ImageClip(mic_path).set_duration(duration)
            mic_clip = mic_clip.resize(height=160)
            mic_clip = mic_clip.set_position(lambda t: ('center', mic_vibration(t)))
            final_layers.append(mic_clip)

        logo_path = get_path('assets', 'images', 'logo.png')
        if os.path.exists(logo_path):
            logo_clip = ImageClip(logo_path).set_duration(duration)
            logo_clip = logo_clip.resize(height=90)
            l_pos_x = OUTPUT_WIDTH - logo_clip.w - 40
            l_pos_y = OUTPUT_HEIGHT - logo_clip.h - 40
            
            # --- FIX LỖI: Sử dụng .fl để thay đổi opacity theo thời gian thay vì .set_opacity ---
            # Công thức nhịp thở: 0.7 + 0.3 * sin(...)
            logo_clip = logo_clip.set_position((l_pos_x, l_pos_y))
            logo_clip = logo_clip.fl(lambda gf, t: gf(t) * (0.7 + 0.3 * math.sin(math.pi * 0.3 * t)))
            
            final_layers.append(logo_clip)
            logger.info("✅ Đã thêm Logo với hiệu ứng Breathing (Fixed).")
        
        logger.info(f"🚀 Bắt đầu Render video {episode_id}...")
        final_video = CompositeVideoClip(final_layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final_video.write_videofile(
            output_path, fps=15, codec="libx264", audio_codec="aac", 
            preset="ultrafast", threads=4, ffmpeg_params=["-crf", "26"], logger='bar' 
        )
        
        final_video.close()
        audio.close()
        return output_path

    except Exception as e:
        logger.error(f"❌ LỖI RENDER: {e}", exc_info=True)
        return False
