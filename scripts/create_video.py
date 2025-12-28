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
    CompositeVideoClip, TextClip, concatenate_videoclips,
    vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT (ULTRA SOFT BLEND - XÓA VIỀN)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info("   (LOG-BG): Xử lý nhân vật AI (Ultra Soft Blend & No Black Edges)...")
    # Tạo canvas hoàn toàn trong suốt
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
            
            # Tính toán tỷ lệ để ảnh phủ kín chiều cao video
            new_char_h = height 
            aspect_ratio = char_img.width / char_img.height
            new_char_w = int(new_char_h * aspect_ratio)
            char_img = char_img.resize((new_char_w, new_char_h), Image.LANCZOS)
            
            # --- KỸ THUẬT LÀM MỜ VIỀN TỐI ĐA ---
            alpha = char_img.getchannel("A")
            # Thu nhỏ vùng hiển thị để vết mờ ăn sâu vào trong
            eroded_mask = alpha.filter(ImageFilter.MinFilter(25))
            # Làm nhòe cực mạnh (GaussianBlur 60-80) để tan biến vào nền
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(70))
            
            # Giảm độ đậm toàn thân (Opacity ~75%) để làm nổi bật nền tĩnh xuyên thấu
            opacity_layer = Image.new("L", soft_edge_mask.size, 190)
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            # Canh giữa nhân vật
            paste_x = (width - new_char_w) // 2 
            final_overlay.paste(char_img, (paste_x, 0), mask=final_mask)
            
        except Exception as e:
            logger.error(f"❌ Lỗi Pillow: {e}")

    overlay_path = get_path('assets', 'temp', "char_blend_mix.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

# ============================================================
# 🎥 HÀM 2: TẠO NỀN HYBRID (PHỐI CẢNH ĐA TẦNG)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    try:
        layers = []

        # 1. LỚP ĐÁY: ẢNH NỀN TĨNH (Đã tăng tương phản để làm nổi bật không gian)
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            img_clip = img_clip.resize(height=height).crop(x_center=img_clip.w/2, width=width)
            # Làm tối nền (0.85) và tăng nét (0.3) để tôn lớp nhân vật mờ ảo phía trên
            img_clip = img_clip.fx(vfx.colorx, factor=0.85).fx(vfx.lum_contrast, contrast=0.3)
            layers.append(img_clip)

        # 2. LỚP GIỮA: NHÂN VẬT ĐÃ BLEND VIỀN
        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers.append(char_clip)

        # 3. LỚP PHỦ: VIDEO ĐỘNG (Mây/Khói bay mờ - Chế độ Không âm thanh)
        try:
            # audio=False giúp render nhanh kịch sàn vì bỏ qua xử lý audio stream
            temp_clip = VideoFileClip(video_path, audio=False, target_resolution=(height, width))
            if temp_clip.duration < duration:
                num_loops = math.ceil(duration / temp_clip.duration)
                temp_clip = temp_clip.fx(vfx.loop, duration=duration)
            
            video_layer = temp_clip.subclip(0, duration).set_opacity(0.35).fx(vfx.colorx, factor=1.1)
            layers.append(video_layer)
        except:
            pass

        return CompositeVideoClip(layers, size=(width, height)).set_duration(duration)
    except Exception as e:
        logger.error(f"❌ Lỗi tổng hợp: {e}")
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)

# ============================================================
# 🎬 HÀM CHÍNH: CREATE VIDEO (RENDER PIPELINE)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Smart Picker: Chọn nền tĩnh theo ID (ID_bg.png) hoặc mặc định
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        
        # Tiền xử lý nhân vật (Làm mờ viền tối đa)
        char_overlay_path = create_static_overlay_image(custom_image_path)
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        
        # Tổng hợp nền phối cảnh 3 lớp
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
                ).set_position((50, 40)).set_duration(duration) # Cách trái 50, trên 40
            except Exception as e:
                logger.warning(f"⚠️ Title Error: {e}")

        # Composing Final
        final_layers = [background_clip]
        if title_layer: final_layers.append(title_layer)
        
        final_video = CompositeVideoClip(final_layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # RENDER TỐI ƯU: 15 FPS giúp GitHub Actions chạy nhanh gấp đôi bản 30 FPS
        logger.info(f"🚀 RENDER START (Cinematic Optimized): {output_path}")
        final_video.write_videofile(
            output_path, fps=15, codec="libx264", audio_codec="aac", 
            preset="ultrafast", threads=4, ffmpeg_params=["-crf", "26"], logger='bar' 
        )
        
        # Cleanup giải phóng RAM
        final_video.close()
        audio.close()
        return output_path

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
        return False
