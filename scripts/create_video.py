# === scripts/create_video.py ===
import logging
import os
import numpy as np
import math
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageChops
import PIL.Image
from rembg import remove  # Thư viện xóa nền AI

# --- [FIX QUAN TRỌNG] VÁ LỖI TƯƠNG THÍCH PILLOW/MOVIEPY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling') and hasattr(PIL.Image.Resampling, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    elif hasattr(PIL.Image, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# -----------------------------------------------------------

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, TextClip, concatenate_videoclips, vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

# ============================================================
# 🎨 HÀM 1: TÁCH NỀN AI & XỬ LÝ ẢNH NHÂN VẬT (ULTRA BLEND)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info("🎨 Đang tách nền AI và tạo hiệu ứng hòa quyện nhân vật...")
    # Tạo canvas hoàn toàn trong suốt chuẩn 16:9
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            # Bước 1: Mở ảnh và Xóa nền bằng AI (như Photoshop)
            raw_img = Image.open(char_path).convert("RGBA")
            char_no_bg = remove(raw_img) # Tự động xóa nền chỉ giữ người
            
            # Bước 2: Resize & Crop để phủ kín hoàn toàn khung hình 16:9
            img_w, img_h = char_no_bg.size
            img_ratio = img_w / img_h
            target_ratio = width / height

            if img_ratio > target_ratio:
                # Ảnh rộng hơn 16:9 -> Lấy chiều cao làm chuẩn
                new_h = height
                new_w = int(new_h * img_ratio)
                char_no_bg = char_no_bg.resize((new_w, new_h), Image.LANCZOS)
                left = (new_w - width) // 2
                char_no_bg = char_no_bg.crop((left, 0, left + width, height))
            else:
                # Ảnh dọc hơn 16:9 -> Lấy chiều rộng làm chuẩn
                new_w = width
                new_h = int(new_w / img_ratio)
                char_no_bg = char_no_bg.resize((new_w, new_h), Image.LANCZOS)
                top = (new_h - height) // 2
                char_no_bg = char_no_bg.crop((0, top, width, top + height))

            # Bước 3: Làm mờ viền tối đa (Ultra Soft Edge)
            alpha = char_no_bg.getchannel("A")
            # Cắt bớt viền AI để tránh bị "răng cưa"
            eroded_mask = alpha.filter(ImageFilter.MinFilter(30)) 
            # Làm nhòe cực mạnh (GaussianBlur 90) để tan biến vào bối cảnh
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(90))
            
            # Giảm Opacity xuống ~70% để tạo hiệu ứng Double Exposure (nhìn xuyên thấu nền)
            opacity_layer = Image.new("L", soft_edge_mask.size, 180)
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            # Dán vào canvas (Lúc này ảnh đã bằng khít video 1280x720)
            final_overlay.paste(char_no_bg, (0, 0), mask=final_mask)
            
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý ảnh AI: {e}")

    overlay_path = get_path('assets', 'temp', "char_final_cinematic.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

# ============================================================
# 🎥 HÀM 2: TẠO NỀN HYBRID (PHỐI CẢNH 3 LỚP)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration):
    try:
        layers = []
        # Lớp 1: Ảnh nền tĩnh (Sắc nét, tương phản cao)
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            img_clip = img_clip.resize(height=OUTPUT_HEIGHT).crop(x_center=img_clip.w/2, width=OUTPUT_WIDTH)
            # Tăng Contrast mạnh để làm nổi bật chiều sâu không gian
            img_clip = img_clip.fx(vfx.colorx, factor=0.85).fx(vfx.lum_contrast, contrast=0.35)
            layers.append(img_clip)

        # Lớp 2: Nhân vật (Đã xóa nền AI, phủ kín 16:9, mờ biên cực đại)
        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers.append(char_clip)

        # Lớp 3: Video Overlay (Mây/Khói bay mờ - Không âm thanh)
        try:
            temp_clip = VideoFileClip(video_path, audio=False, target_resolution=(OUTPUT_HEIGHT, OUTPUT_WIDTH))
            if temp_clip.duration < duration:
                temp_clip = temp_clip.fx(vfx.loop, duration=duration)
            
            # Độ mờ 0.35 đảm bảo chuyển động mượt mà không che lấp nhân vật
            video_layer = temp_clip.subclip(0, duration).set_opacity(0.35).fx(vfx.colorx, factor=1.1)
            layers.append(video_layer)
        except: pass

        return CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_duration(duration)
    except Exception as e:
        return ColorClip(size=(OUTPUT_WIDTH, OUTPUT_HEIGHT), color=(15, 15, 15), duration=duration)

# ============================================================
# 🎬 HÀM CHÍNH: CREATE VIDEO (MAIN RENDER)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Chọn nền tĩnh theo ID hoặc mặc định
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        
        char_overlay_path = create_static_overlay_image(custom_image_path)
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
        
        # RENDER: FPS 15 / CRF 26 (Cân bằng Tốc độ & Vẻ đẹp cho GitHub Actions)
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
