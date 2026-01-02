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
# 🛠️ HÀM BỔ TRỢ (HELPERS)
# ============================================================
def zoom_in_effect(t, duration):
    """Tạo tỷ lệ zoom từ 1.0 đến 1.12 trong suốt video"""
    return 1 + 0.12 * (t / duration)

def pick_video_background(theme_text):
    """Chọn video nền dựa trên phân loại từ AI"""
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
            if os.path.exists(get_path('assets', 'video', filename)):
                selected_file = filename
                break
    return get_path('assets', 'video', selected_file)

# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT (FIT KHUNG HÌNH & SOFT BLEND)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info("   (LOG-BG): Xử lý nhân vật AI (Fit 16:9 & Ultra Soft Blend)...")
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
            
            # --- FIX: RESIZE FIT (KHÔNG CROP) ---
            char_img.thumbnail((width, height), Image.LANCZOS)
            
            # Căn giữa nhân vật trên canvas
            offset_x = (width - char_img.width) // 2
            offset_y = (height - char_img.height) // 2

            # Xử lý làm mờ viền
            alpha = char_img.getchannel("A")
            eroded_mask = alpha.filter(ImageFilter.MinFilter(15)) 
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(60))
            
            opacity_layer = Image.new("L", soft_edge_mask.size, 190)
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            final_overlay.paste(char_img, (offset_x, offset_y), mask=final_mask)
            
        except Exception as e:
            logger.error(f"❌ Lỗi Pillow: {e}")

    overlay_path = get_path('assets', 'temp', "char_blend_full.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

# ============================================================
# 🎥 HÀM 2: TẠO NỀN HYBRID (ZOOM & SMART PICKER)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    try:
        layers = []
        # Lớp 1: Ảnh nền tĩnh (ZOOM EFFECT)
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            # Fix hiển thị 100% khung hình
            img_clip = img_clip.resize(width=width, height=height)
            # Áp dụng Ken Burns
            img_clip = img_clip.resize(lambda t: zoom_in_effect(t, duration))
            img_clip = img_clip.set_position(('center', 'center'))
            img_clip = img_clip.fx(vfx.colorx, factor=0.85).fx(vfx.lum_contrast, contrast=0.35)
            layers.append(img_clip)

        # Lớp 2: Nhân vật (Cùng ZOOM với nền để tạo độ sâu)
        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            char_clip = char_clip.resize(lambda t: zoom_in_effect(t, duration))
            char_clip = char_clip.set_position(('center', 'center'))
            layers.append(char_clip)

        # Lớp 3: Video Overlay (Mây/Khói)
        try:
            temp_clip = VideoFileClip(video_path, audio=False, target_resolution=(height, width))
            if temp_clip.duration < duration:
                temp_clip = temp_clip.fx(vfx.loop, duration=duration)
            
            video_layer = temp_clip.subclip(0, duration).set_opacity(0.30).fx(vfx.colorx, factor=1.1)
            layers.append(video_layer)
        except: pass

        return CompositeVideoClip(layers, size=(width, height)).set_duration(duration)
    except Exception as e:
        logger.error(f"❌ Lỗi tạo nền: {e}")
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)

# ============================================================
# 🎬 HÀM CHÍNH: CREATE VIDEO
# ============================================================
def create_video(audio_path, episode_id, image_path=None, title_text="", theme=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # 1. Chọn ảnh nền tĩnh
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        
        # 2. Xử lý overlay nhân vật
        char_overlay_path = create_static_overlay_image(image_path)
        
        # 3. Chọn video nền động dựa trên Theme
        base_video_path = pick_video_background(theme) 
        
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)

        # 4. Lớp tiêu đề
        title_layer = None
        if title_text:
            try:
                title_layer = TextClip(
                    title_text.upper(), 
                    fontsize=50, font='DejaVu-Sans-Bold', color='#FFD700', 
                    stroke_color='black', stroke_width=2,
                    method='caption', align='West', size=(OUTPUT_WIDTH * 0.6, None)
                ).set_position((50, 40)).set_duration(duration)
            except: pass

        final_layers = [background_clip]
        if title_layer: final_layers.append(title_layer)
        
        final_video = CompositeVideoClip(final_layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # RENDER (Optimized for 10-15min videos)
        final_video.write_videofile(
            output_path, fps=15, codec="libx264", audio_codec="aac", 
            preset="ultrafast", threads=4, ffmpeg_params=["-crf", "26"], logger='bar' 
        )
        
        final_video.close()
        audio.close()
        return output_path

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
        return False
