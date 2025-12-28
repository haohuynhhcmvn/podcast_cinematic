# === scripts/create_video.py ===
import logging
import os
import math
from PIL import Image, ImageEnhance, ImageFilter, ImageChops
import PIL.Image

# --- FIX TƯƠNG THÍCH PILLOW/MOVIEPY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', None))

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, TextClip, concatenate_videoclips, vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

# ============================================================
# 🎨 TỐI ƯU 1: TIỀN XỬ LÝ ẢNH (CHỈ LÀM 1 LẦN DUY NHẤT)
# ============================================================
def process_static_image(path, width, height, is_bg=False):
    """Xử lý resize/crop/contrast bằng Pillow trước khi đưa vào MoviePy"""
    img = Image.open(path).convert("RGBA")
    # Resize & Crop chuẩn 16:9 bằng Pillow (nhanh hơn MoviePy gấp 10 lần)
    img_ratio = img.width / img.height
    target_ratio = width / height
    
    if img_ratio > target_ratio:
        new_w = int(height * img_ratio)
        img = img.resize((new_w, height), Image.LANCZOS)
        left = (new_w - width) // 2
        img = img.crop((left, 0, left + width, height))
    else:
        new_h = int(width / img_ratio)
        img = img.resize((width, new_h), Image.LANCZOS)
        top = (new_h - height) // 2
        img = img.crop((0, top, width, top + height))

    if is_bg:
        # Áp dụng colorx (0.9) và contrast (0.2) ngay trên Pillow
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2) # contrast 0.2
        brightness = ImageEnhance.Brightness(img)
        img = brightness.enhance(0.9) # factor 0.9
        
    return img

def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    # (Giữ nguyên logic Double Exposure của bạn nhưng dùng Pillow tối ưu)
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if char_path and os.path.exists(char_path):
        char_img = Image.open(char_path).convert("RGBA")
        new_h = height
        new_w = int(char_img.width * (new_h / char_img.height))
        char_img = char_img.resize((new_w, new_h), Image.LANCZOS)
        
        mask = char_img.getchannel("A")
        mask = mask.filter(ImageFilter.MinFilter(25)).filter(ImageFilter.GaussianBlur(45))
        
        opacity_layer = Image.new("L", mask.size, 190)
        final_mask = ImageChops.multiply(mask, opacity_layer)
        
        final_overlay.paste(char_img, ((width - new_w) // 2, height - new_h), mask=final_mask)
    
    path = get_path('assets', 'temp', "char_blend_mix.png")
    final_overlay.save(path)
    return path

# ============================================================
# 🎥 TỐI ƯU 2: GIẢM TẢI COMPOSITING
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Tiền xử lý các file tĩnh
        char_path = create_static_overlay_image(custom_image_path)
        
        # 1. Background Layer (Đã tiền xử lý contrast/color)
        bg_path = get_path('assets', 'images', 'default_background.png')
        processed_bg = process_static_image(bg_path, OUTPUT_WIDTH, OUTPUT_HEIGHT, is_bg=True)
        bg_temp_path = get_path('assets', 'temp', 'processed_bg.png')
        processed_bg.save(bg_temp_path)
        bg_clip = ImageClip(bg_temp_path).set_duration(duration)

        # 2. Character Layer
        char_clip = ImageClip(char_path).set_duration(duration)

        # 3. Video Overlay (TỐI ƯU: Tắt audio, resize sẵn)
        video_overlay = None
        base_video_path = get_path('assets', 'video', 'long_background.mp4')
        if os.path.exists(base_video_path):
            # Load video với thông số tối ưu: resize ngay khi load
            v_clip = VideoFileClip(base_video_path, audio=False, target_resolution=(OUTPUT_HEIGHT, OUTPUT_WIDTH))
            if v_clip.duration < duration:
                v_clip = v_clip.fx(vfx.loop, duration=duration)
            video_overlay = v_clip.subclip(0, duration).set_opacity(0.35).fx(vfx.colorx, factor=1.1)

        # 4. Glow & Text
        glow_layer = make_glow_layer(duration)
        
        layers = [bg_clip, char_clip]
        if video_overlay: layers.append(video_overlay)
        layers.append(glow_layer)

        if title_text:
            title = TextClip(title_text.upper(), fontsize=55, font='DejaVu-Sans-Bold', color='#FFD700',
                             stroke_color='black', stroke_width=3, method='caption', align='West', size=(800, None)
                             ).set_position((50, 50)).set_duration(duration)
            layers.append(title)

        # 5. RENDER (THAY ĐỔI FPS XUỐNG 12-15)
        # Video dạng kể chuyện tĩnh này không cần 20fps. 15fps sẽ giảm 25% thời gian render.
        final_video = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        out_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        logger.info(f"🚀 Render Start: {episode_id}")
        
        final_video.write_videofile(
            out_path, 
            fps=15,             # GIẢM FPS xuống 15 để nhanh hơn
            codec="libx264", 
            preset="ultrafast", # Preset nhanh nhất
            threads=4,          # Tận dụng đa nhân
            ffmpeg_params=["-crf", "26"], # CRF 26 nhanh hơn và nhẹ hơn 24
            logger='bar'
        )
        
        # Cleanup
        final_video.close()
        audio.close()
        return out_path

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
        return False
