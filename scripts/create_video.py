# === scripts/create_video.py (FIXED ARGUMENT NAME) ===
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
    CompositeVideoClip, TextClip, concatenate_videoclips,
    vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT (PHỦ KÍN 16:9 & SIÊU MỜ VIỀN)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info("   (LOG-BG): Xử lý nhân vật AI (Phủ kín 16:9 & Ultra Soft Blend)...")
    
    # Khởi tạo canvas trong suốt chuẩn kích thước video
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
            
            # --- BƯỚC 1: RESIZE & CROP ĐỂ PHỦ KÍN 16:9 (XÓA VIỀN ĐEN) ---
            img_ratio = char_img.width / char_img.height
            target_ratio = width / height

            if img_ratio > target_ratio:
                # Ảnh gốc rộng hơn 16:9 -> Resize theo chiều cao
                new_h = height
                new_w = int(new_h * img_ratio)
                char_img = char_img.resize((new_w, new_h), Image.LANCZOS)
                # Cắt lấy phần giữa để đúng chiều rộng 1280
                left = (new_w - width) // 2
                char_img = char_img.crop((left, 0, left + width, height))
            else:
                # Ảnh gốc dọc/vuông hơn 16:9 -> Resize theo chiều rộng
                new_w = width
                new_h = int(new_w / img_ratio)
                char_img = char_img.resize((new_w, new_h), Image.LANCZOS)
                # Cắt lấy phần giữa để đúng chiều cao 720
                top = (new_h - height) // 2
                char_img = char_img.crop((0, top, width, top + height))

            # --- BƯỚC 2: LÀM MỜ VIỀN TỐI ĐA (ULTRA SOFT MASK) ---
            alpha = char_img.getchannel("A")
            # Thu nhỏ vùng Alpha để vết mờ ăn sâu vào trong (Erode)
            eroded_mask = alpha.filter(ImageFilter.MinFilter(35)) 
            # Làm nhòe cực mạnh để tan biến vào nền tĩnh (GaussianBlur 80-100)
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(90))
            
            # Giảm độ đậm nhẹ để nền tĩnh xuyên thấu (Opacity ~70%)
            opacity_layer = Image.new("L", soft_edge_mask.size, 180)
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            # Dán trực tiếp vào canvas (Lúc này char_img đã bằng đúng width/height video)
            final_overlay.paste(char_img, (0, 0), mask=final_mask)
            
        except Exception as e:
            logger.error(f"❌ Lỗi Pillow xử lý phủ nền: {e}")

    overlay_path = get_path('assets', 'temp', "char_blend_full.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

# ============================================================
# 🎥 HÀM 2: TẠO NỀN HYBRID (PHỐI CẢNH 3 LỚP)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    try:
        layers = []
        # Lớp 1: Ảnh nền tĩnh (Sắc nét, tương phản cao để làm nổi bật chiều sâu)
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            img_clip = img_clip.resize(height=height).crop(x_center=img_clip.w/2, width=width)
            img_clip = img_clip.fx(vfx.colorx, factor=0.85).fx(vfx.lum_contrast, contrast=0.35)
            layers.append(img_clip)

        # Lớp 2: Nhân vật (Đã phủ kín 16:9 và mờ biên cực mạnh)
        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers.append(char_clip)

        # Lớp 3: Video Overlay (Mây/Khói bay mờ - Chế độ Không âm thanh)
        try:
            temp_clip = VideoFileClip(video_path, audio=False, target_resolution=(height, width))
            if temp_clip.duration < duration:
                temp_clip = temp_clip.fx(vfx.loop, duration=duration)
            
            video_layer = temp_clip.subclip(0, duration).set_opacity(0.35).fx(vfx.colorx, factor=1.1)
            layers.append(video_layer)
        except: pass

        return CompositeVideoClip(layers, size=(width, height)).set_duration(duration)
    except Exception as e:
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)

# ============================================================
# 🎬 HÀM CHÍNH: CREATE VIDEO
# ============================================================
# [FIXED] Đổi 'custom_image_path' thành 'image_path' để khớp với glue_pipeline
def create_video(audio_path, episode_id, image_path=None, title_text=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Smart Picker: Chọn nền tĩnh theo ID hoặc mặc định
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        
        # Sử dụng đúng tên biến image_path
        char_overlay_path = create_static_overlay_image(image_path)
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)

        # 🖋️ LỚP TIÊU ĐỀ (GÓC TRÁI TRÊN)
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
        
        # RENDER TỐI ƯU: 15 FPS / CRF 26
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
