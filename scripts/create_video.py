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
# === scripts/create_video.py ===
# ... (Giữ nguyên các phần import và fix Pillow đầu file) ...
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    logger.info("   (LOG-BG): Xử lý nhân vật AI (Fix viền đen & Blend)...")
    # TỐI ƯU: Tạo canvas hoàn toàn trong suốt với kích thước chính xác của Video
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
            
            # TÍNH TOÁN ĐỂ ẢNH PHỦ KÍN CHIỀU CAO (KHÔNG ĐỂ LẠI VIỀN)
            new_char_h = height 
            aspect_ratio = char_img.width / char_img.height
            new_char_w = int(new_char_h * aspect_ratio)
            
            char_img = char_img.resize((new_char_w, new_char_h), Image.LANCZOS)
            
            # Mask mờ biên mạnh để tan vào nền (Double Exposure)
            original_alpha = char_img.getchannel("A")
            eroded_mask = original_alpha.filter(ImageFilter.MinFilter(20))
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(40))
            
            opacity_layer = Image.new("L", soft_edge_mask.size, 195)
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            # Căn giữa nhân vật để tránh lệch tạo viền đen hai bên
            paste_x = (width - new_char_w) // 2 
            paste_y = 0 # Sát đỉnh để không hở viền trên/dưới
            
            final_overlay.paste(char_img, (paste_x, paste_y), mask=final_mask)
        except Exception as e:
            logger.error(f"❌ Lỗi Pillow: {e}")

    overlay_path = get_path('assets', 'temp', "char_blend_mix.png")
    final_overlay.save(overlay_path, format="PNG") 
    return overlay_path

def create_video(audio_path, episode_id, custom_image_path=None, title_text=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Chọn nền theo ID
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        
        char_overlay_path = create_static_overlay_image(custom_image_path)
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        
        # Tạo nền hòa quyện
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)

        # ------------------------------------------------------------
        # 🖋️ ĐƯA CHỮ LÊN GÓC TRÁI TRÊN
        # ------------------------------------------------------------
        title_layer = None
        if title_text:
            try:
                title_layer = TextClip(
                    title_text.upper(), 
                    fontsize=50, # Chỉnh cỡ chữ vừa phải cho góc trái
                    font='DejaVu-Sans-Bold', 
                    color='#FFD700', # Vàng Gold cinematic
                    stroke_color='black', stroke_width=2,
                    method='caption', 
                    align='West', 
                    size=(OUTPUT_WIDTH * 0.6, None) # Không quá rộng để tránh đè nhân vật
                ).set_position((50, 40)).set_duration(duration) # Cách lề trái 50, lề trên 40
            except: pass

        # ... (Phần Composite và Render giữ nguyên thông số 15 FPS / CRF 26 để nhanh) ...
        final_layers = [background_clip]
        if title_layer: final_layers.append(title_layer)
        
        final_video = CompositeVideoClip(final_layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        out_path = get_path("outputs", "video", f"{episode_id}_video.mp4")
        
        final_video.write_videofile(
            out_path, fps=15, codec="libx264", preset="ultrafast", 
            threads=4, ffmpeg_params=["-crf", "26"], logger='bar' 
        )
        # ... (Cleanup giữ nguyên) ...
        return out_path
    except Exception as e:
        logger.error(f"❌ FATAL ERROR: {e}")
        return False
