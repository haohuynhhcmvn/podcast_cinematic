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
    """Tạo tỷ lệ zoom nhẹ từ 1.0 đến 1.1"""
    return 1 + 0.10 * (t / duration)

def mic_vibration(t):
    """Tạo độ rung nhẹ cho micro (lên xuống 3px)"""
    base_y = OUTPUT_HEIGHT - 170
    return base_y + 3 * math.sin(2 * math.pi * 0.5 * t)

def logo_breathing(t):
    """Hiệu ứng nhịp thở cho Logo (Opacity)"""
    return 0.7 + 0.3 * math.sin(math.pi * 0.3 * t)

# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT (GIỮ LOGIC CŨ CỦA BẠN)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info("   (LOG-BG): Xử lý nhân vật AI (Logic Gốc: Phủ kín & Ultra Soft)...")
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
            
            # --- GIỮ NGUYÊN BƯỚC 1: RESIZE & CROP (PHỦ KÍN) ---
            img_ratio = char_img.width / char_img.height
            target_ratio = width / height

            if img_ratio > target_ratio:
                new_h = height
                new_w = int(new_h * img_ratio)
                char_img = char_img.resize((new_w, new_h), Image.LANCZOS)
                left = (new_w - width) // 2
                char_img = char_img.crop((left, 0, left + width, height))
            else:
                new_w = width
                new_h = int(new_w / img_ratio)
                char_img = char_img.resize((new_w, new_h), Image.LANCZOS)
                top = (new_h - height) // 2
                char_img = char_img.crop((0, top, width, top + height))

            # --- GIỮ NGUYÊN BƯỚC 2: LÀM MỜ VIỀN TỐI ĐA ---
            alpha = char_img.getchannel("A")
            eroded_mask = alpha.filter(ImageFilter.MinFilter(35)) 
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(90))
            
            opacity_layer = Image.new("L", soft_edge_mask.size, 180)
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            final_overlay.paste(char_img, (0, 0), mask=final_mask)
            
        except Exception as e:
            logger.error(f"❌ Lỗi Pillow xử lý nhân vật: {e}")

    overlay_path = get_path('assets', 'temp', "char_blend_full.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

# ============================================================
# 🎥 HÀM 2: TẠO NỀN HYBRID (PHỐI CẢNH 3 LỚP + ZOOM)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    try:
        layers = []
        # Lớp 1: Ảnh nền tĩnh (SỬA LỖI HIỂN THỊ 16:9 + ZOOM)
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            # Resize khít khung hình trước khi zoom để không bị viền đen
            img_clip = img_clip.resize(width=width, height=height)
            img_clip = img_clip.resize(lambda t: zoom_in_effect(t, duration))
            img_clip = img_clip.set_position('center')
            img_clip = img_clip.fx(vfx.colorx, factor=0.85).fx(vfx.lum_contrast, contrast=0.35)
            layers.append(img_clip)

        # Lớp 2: Nhân vật (Dùng ảnh Overlay đã xử lý bằng logic cũ + ZOOM đồng bộ)
        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            char_clip = char_clip.resize(lambda t: zoom_in_effect(t, duration))
            char_clip = char_clip.set_position('center')
            layers.append(char_clip)

        # Lớp 3: Video Overlay (Khói/Bụi)
        try:
            temp_clip = VideoFileClip(video_path, audio=False, target_resolution=(height, width))
            if temp_clip.duration < duration:
                temp_clip = temp_clip.fx(vfx.loop, duration=duration)
            video_layer = temp_clip.subclip(0, duration).set_opacity(0.35).fx(vfx.colorx, factor=1.1)
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
        
        # Smart Picker nền tĩnh
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        
        char_overlay_path = create_static_overlay_image(image_path)
        
        # Chọn video nền dựa trên theme (nếu có hệ thống theme)
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)

        final_layers = [background_clip]

        # 🖋️ LỚP TIÊU ĐỀ
        if title_text:
            try:
                title_layer = TextClip(
                    title_text.upper(), 
                    fontsize=50, font='DejaVu-Sans-Bold', color='#FFD700', 
                    stroke_color='black', stroke_width=2,
                    method='caption', align='West', size=(OUTPUT_WIDTH * 0.6, None)
                ).set_position((50, 40)).set_duration(duration)
                final_layers.append(title_layer)
            except: pass

        # 🎙️ LỚP MICROPHONE (Animation Rung)
        mic_f = get_path('assets', 'images', 'microphone.png')
        if os.path.exists(mic_f):
            mic_clip = ImageClip(mic_f).set_duration(duration).resize(height=150)
            mic_clip = mic_clip.set_position(lambda t: ('center', mic_vibration(t)))
            final_layers.append(mic_clip)

        # 🏷️ LỚP LOGO (Animation Nhịp thở)
        logo_f = get_path('assets', 'images', 'logo.png')
        if os.path.exists(logo_f):
            logo_clip = ImageClip(logo_f).set_duration(duration).resize(height=80)
            l_pos = (OUTPUT_WIDTH - logo_clip.w - 40, OUTPUT_HEIGHT - logo_clip.h - 40)
            # Sử dụng fl_image để fix lỗi TypeError nhân function với float ở bản trước
            logo_clip = logo_clip.set_position(l_pos).fl(lambda gf, t: gf(t) * (logo_breathing(t)))
            final_layers.append(logo_clip)

        # RENDER CHỐT
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
        logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
        return False
