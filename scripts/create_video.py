# === scripts/create_video.py ===
import logging
import os
import numpy as np
import math
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
            # Shrink & Blur bằng Pillow (Rất nhanh)
            eroded_mask = original_alpha.filter(ImageFilter.MinFilter(25))
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(45))
            
            blend_opacity = 190 
            opacity_layer = Image.new("L", soft_edge_mask.size, blend_opacity)
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            # Đặt nhân vật lệch phải (Rule of Thirds) thay vì chính giữa để cinematic hơn
            paste_x = width - new_char_w 
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
# ✨ HÀM 2: LỚP GLOW (ĐÃ FIX LỖI DEFINED)
# ============================================================
def make_glow_layer(duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    # Tạo hiệu ứng Vignette tối góc thay vì Glow tâm để giảm tải CPU
    # MoviePy ColorClip đơn giản hơn nhiều so với vẽ mảng Numpy
    return ColorClip(size=(width, height), color=(0,0,0)).set_duration(duration).set_opacity(0.3)

# ============================================================
# 🎥 HÀM 3: TẠO NỀN "CINEMATIC" (TỐI ƯU RENDER)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    try:
        layers_to_composite = []
        # 1. Ảnh nền tĩnh (Smart contrast)
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            img_clip = img_clip.resize(height=height).crop(x_center=img_clip.w/2, width=width)
            img_clip = img_clip.fx(vfx.colorx, factor=0.85).fx(vfx.lum_contrast, contrast=0.2)
            layers_to_composite.append(img_clip)

        # 2. Nhân vật đã Blend
        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers_to_composite.append(char_clip)

        # 3. Video Overlay (Mây bay/Khói bụi - SILENT)
        try:
            # TỐI ƯU: Resize ngay khi load và tắt audio
            temp_clip = VideoFileClip(video_path, audio=False, target_resolution=(height, width))
            if temp_clip.duration < duration:
                num_loops = math.ceil(duration / temp_clip.duration)
                temp_clip = temp_clip.fx(vfx.loop, duration=duration)
            
            video_layer = temp_clip.subclip(0, duration).set_opacity(0.35).fx(vfx.colorx, factor=1.1)
            layers_to_composite.append(video_layer)
        except: pass

        return CompositeVideoClip(layers_to_composite, size=(width, height)).set_duration(duration)
    except Exception as e:
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)

# ============================================================
# 🎬 HÀM CHÍNH: TẠO VIDEO (MAIN PIPELINE)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        char_overlay_path = create_static_overlay_image(custom_image_path)
        
        # Tự động chọn nền theo Episode ID
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)
        glow_layer = make_glow_layer(duration)

        title_layer = None
        if title_text:
            try:
                title_layer = TextClip(
                    title_text.upper(), fontsize=55, font='DejaVu-Sans-Bold', color='#FFD700', 
                    stroke_color='black', stroke_width=3, method='caption', align='West', size=(850, None)       
                ).set_position((80, 'center')).set_duration(duration)
            except: pass

        final_layers = [background_clip, glow_layer]
        if title_layer: final_layers.append(title_layer)
        
        final_video = CompositeVideoClip(final_layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # TỐI ƯU RENDER: FPS 15 (Giảm 25% khối lượng tính toán), CRF 26 (Tăng tốc độ nén)
        final_video.write_videofile(
            output_path, fps=15, codec="libx264", audio_codec="aac", 
            preset="ultrafast", threads=4, ffmpeg_params=["-crf", "26"], logger=None 
        )
        
        final_video.close()
        audio.close()
        return output_path

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
        return False
