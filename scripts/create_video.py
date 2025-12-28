# === scripts/create_video.py ===
import logging
import os
import numpy as np
import math
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageChops
import PIL.Image
from rembg import remove 

# --- [FIX QUAN TRỌNG] VÁ LỖI TƯƠNG THÍCH PILLOW/MOVIEPY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', None))
# -----------------------------------------------------------

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, TextClip, vfx
)
from utils import get_path

logger = logging.getLogger(__name__)
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info("🎨 Đang tách nền AI và tạo hiệu ứng hòa quyện...")
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            raw_img = Image.open(char_path).convert("RGBA")
            char_no_bg = remove(raw_img) # Xóa nền bằng AI
            
            # Resize & Crop phủ kín 16:9
            img_w, img_h = char_no_bg.size
            img_ratio = img_w / img_h
            target_ratio = width / height

            if img_ratio > target_ratio:
                new_h = height
                new_w = int(new_h * img_ratio)
                char_no_bg = char_no_bg.resize((new_w, new_h), Image.LANCZOS)
                left = (new_w - width) // 2
                char_no_bg = char_no_bg.crop((left, 0, left + width, height))
            else:
                new_w = width
                new_h = int(new_w / img_ratio)
                char_no_bg = char_no_bg.resize((new_w, new_h), Image.LANCZOS)
                top = (new_h - height) // 2
                char_no_bg = char_no_bg.crop((0, top, width, top + height))

            # TÍNH TOÁN FILTER AN TOÀN ĐỂ TRÁNH LỖI "bad filter size"
            alpha = char_no_bg.getchannel("A")
            min_dim = min(char_no_bg.size)
            safe_erode = min(25, min_dim // 15)
            safe_blur = min(70, min_dim // 8) # Đảm bảo không quá lớn gây lỗi CPU

            eroded_mask = alpha.filter(ImageFilter.MinFilter(safe_erode)) 
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(safe_blur))
            
            opacity_layer = Image.new("L", soft_edge_mask.size, 185)
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            final_overlay.paste(char_no_bg, (0, 0), mask=final_mask)
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý ảnh AI: {e}")
            # Dự phòng nếu AI lỗi
            raw_img = Image.open(char_path).convert("RGBA").resize((width, height), Image.LANCZOS)
            final_overlay.paste(raw_img, (0, 0))

    overlay_path = get_path('assets', 'temp', "char_final_cinematic.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

def create_video(audio_path, episode_id, custom_image_path=None, title_text=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Chọn nền tĩnh thông minh
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        
        char_overlay_path = create_static_overlay_image(custom_image_path)
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        
        # Tạo 3 lớp phối cảnh
        layers = []
        if os.path.exists(static_bg_path):
            bg = ImageClip(static_bg_path).set_duration(duration).resize(height=OUTPUT_HEIGHT)
            bg = bg.crop(x_center=bg.w/2, width=OUTPUT_WIDTH).fx(vfx.colorx, 0.8).fx(vfx.lum_contrast, 0.3)
            layers.append(bg)

        char_clip = ImageClip(char_overlay_path).set_duration(duration)
        layers.append(char_clip)

        if os.path.exists(base_video_path):
            video_ov = VideoFileClip(base_video_path, audio=False, target_resolution=(OUTPUT_HEIGHT, OUTPUT_WIDTH))
            video_ov = video_ov.fx(vfx.loop, duration=duration).set_opacity(0.35)
            layers.append(video_ov)

        # Chữ góc trái trên
        if title_text:
            title = TextClip(title_text.upper(), fontsize=50, font='DejaVu-Sans-Bold', color='#FFD700', 
                             stroke_color='black', stroke_width=2, method='caption', align='West', size=(750, None)
                             ).set_position((50, 40)).set_duration(duration)
            layers.append(title)

        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        out_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        
        # Render tối ưu cho CPU GitHub (15 FPS)
        final.write_videofile(out_path, fps=15, codec="libx264", preset="ultrafast", 
                             threads=4, ffmpeg_params=["-crf", "26"], logger=None)
        
        final.close()
        audio.close()
        return out_path
    except Exception as e:
        logger.error(f"❌ Render Error: {e}")
        return False
