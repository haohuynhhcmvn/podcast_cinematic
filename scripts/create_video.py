# === scripts/create_video.py ===
import logging
import os
import numpy as np
import math
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageChops
import PIL.Image

# --- [VÁ LỖI TƯƠNG THÍCH PILLOW/MOVIEPY] ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling') and hasattr(PIL.Image.Resampling, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
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
# 🎭 HIỆU ỨNG ĐỘNG
# ============================================================
def zoom_in_effect(t, duration):
    return 1 + 0.12 * (t / duration)

def mic_vibration(t):
    return (OUTPUT_HEIGHT - 170) + 3 * math.sin(2 * math.pi * 0.5 * t)

def logo_breathing(t):
    return 0.7 + 0.3 * math.sin(math.pi * 0.3 * t)

# ============================================================
# 🎨 HÀM XỬ LÝ NHÂN VẬT (GIỮ LOGIC PHỦ KÍN 16:9 CỦA BẠN)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
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

            # Mờ biên siêu mềm (90)
            alpha = char_img.getchannel("A")
            eroded_mask = alpha.filter(ImageFilter.MinFilter(30)) 
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(90))
            
            final_overlay.paste(char_img, (0, 0), mask=soft_edge_mask)
        except Exception as e:
            logger.error(f"❌ Pillow Error: {e}")

    overlay_path = get_path('assets', 'temp', "char_blend_full.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

# ============================================================
# 🎬 HÀM CHÍNH: CREATE VIDEO (BỐ TRÍ THEO LỚP CHIẾN THUẬT)
# ============================================================
def create_video(audio_path, episode_id, image_path=None, title_text="", theme=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # 1. CHUẨN BỊ CÁC LỚP
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        char_overlay_path = create_static_overlay_image(image_path)
        video_overlay_path = get_path('assets', 'video', 'long_background.mp4')

        layers = []

        # --- LỚP 0: NỀN TĨNH (DƯỚI CÙNG) ---
        if os.path.exists(static_bg_path):
            bg_clip = ImageClip(static_bg_path).set_duration(duration)
            bg_clip = bg_clip.resize(width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT)
            bg_clip = bg_clip.resize(lambda t: zoom_in_effect(t, duration)).set_position('center')
            bg_clip = bg_clip.fx(vfx.colorx, 0.8).fx(vfx.lum_contrast, contrast=0.2)
            layers.append(bg_clip)

        # --- LỚP 1: NHÂN VẬT (GIỮA) ---
        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            char_clip = char_clip.resize(lambda t: zoom_in_effect(t, duration)).set_position('center')
            layers.append(char_clip)

        # --- LỚP 2: VIDEO NỀN/KHÓI (PHỦ LÊN NHÂN VẬT ĐỂ HÒA QUYỆN) ---
        if os.path.exists(video_overlay_path):
            v_clip = VideoFileClip(video_overlay_path, audio=False, target_resolution=(OUTPUT_HEIGHT, OUTPUT_WIDTH))
            if v_clip.duration < duration:
                v_clip = v_clip.fx(vfx.loop, duration=duration)
            # Giảm opacity xuống 0.35 để tạo hiệu ứng ma mị xuyên thấu
            v_clip = v_clip.subclip(0, duration).set_opacity(0.35).fx(vfx.colorx, 1.1)
            layers.append(v_clip)

        # --- LỚP 3: MICRO & LOGO & TIÊU ĐỀ (TRÊN CÙNG) ---
        # Micro
        mic_f = get_path('assets', 'images', 'microphone.png')
        if os.path.exists(mic_f):
            mic = ImageClip(mic_f).set_duration(duration).resize(height=160)
            mic = mic.set_position(lambda t: ('center', mic_vibration(t)))
            layers.append(mic)

        # Logo
        logo_f = get_path('assets', 'images', 'logo.png')
        if os.path.exists(logo_f):
            logo = ImageClip(logo_f).set_duration(duration).resize(height=90)
            l_pos = (OUTPUT_WIDTH - logo.w - 40, OUTPUT_HEIGHT - logo.h - 40)
            # Sửa lỗi opacity bằng fl_image
            logo = logo.set_position(l_pos).fl(lambda gf, t: gf(t) * (logo_breathing(t)))
            layers.append(logo)

        # Tiêu đề
        if title_text:
            txt = TextClip(title_text.upper(), fontsize=50, font='DejaVu-Sans-Bold', color='gold', 
                           stroke_color='black', stroke_width=2, method='caption', size=(OUTPUT_WIDTH*0.6, None))
            layers.append(txt.set_position((50, 40)).set_duration(duration))

        # RENDER
        logger.info(f"🚀 Đang render video {episode_id} với bố cục ma mị...")
        final_video = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final_video.write_videofile(output_path, fps=15, codec="libx264", preset="ultrafast", threads=4, logger='bar')
        
        final_video.close()
        audio.close()
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi: {e}", exc_info=True)
        return False
