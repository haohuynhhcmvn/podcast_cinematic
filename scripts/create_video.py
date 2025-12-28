# === scripts/create_video.py ===
import logging
import os
import numpy as np
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
# 🎨 TỐI ƯU 1: XỬ LÝ TOÀN BỘ LỚP TĨNH BẰNG PILLOW (SIÊU NHANH)
# ============================================================
def prepare_static_layers(char_path, static_bg_path, episode_id):
    """
    Thay vì để MoviePy chồng lấp ảnh nền và nhân vật, ta dùng Pillow
    tạo ra 1 file duy nhất. Điều này giảm 50% khối lượng công việc của MoviePy.
    """
    logger.info("⚡ Đang tiền xử lý lớp hình ảnh tĩnh (Pillow)...")
    
    # 1. Xử lý Nền tĩnh
    if static_bg_path and os.path.exists(static_bg_path):
        bg = Image.open(static_bg_path).convert("RGBA")
        # Resize & Crop chuẩn 16:9
        bg = bg.resize((OUTPUT_WIDTH, int(bg.height * (OUTPUT_WIDTH / bg.width))), Image.LANCZOS)
        bg = bg.crop((0, (bg.height - OUTPUT_HEIGHT)//2, OUTPUT_WIDTH, (bg.height + OUTPUT_HEIGHT)//2))
        # Color grading nhẹ
        enhancer = ImageEnhance.Contrast(bg)
        bg = enhancer.enhance(1.2)
    else:
        bg = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (15, 15, 15, 255))

    # 2. Xử lý Nhân vật & Double Exposure
    if char_path and os.path.exists(char_path):
        char = Image.open(char_path).convert("RGBA")
        char_h = OUTPUT_HEIGHT
        char_w = int(char.width * (char_h / char.height))
        char = char.resize((char_w, char_h), Image.LANCZOS)
        
        # Mask viền mờ (Cinematic Blend)
        mask = char.getchannel("A")
        mask = mask.filter(ImageFilter.MinFilter(25)) # Shrink
        mask = mask.filter(ImageFilter.GaussianBlur(45)) # Soften
        
        # Merge nhân vật vào nền
        paste_x = (OUTPUT_WIDTH - char_w) // 2
        bg.paste(char, (paste_x, 0), mask=mask)

    # 3. Thêm Vignette (Lớp tối viền) để tăng chiều sâu
    vignette = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)
    # Vẽ gradient tối đơn giản hoặc dán file vignette có sẵn
    
    final_static_path = get_path('assets', 'temp', f"{episode_id}_static_final.png")
    bg.convert("RGB").save(final_static_path, "PNG")
    return final_static_path

# ============================================================
# 🎥 TỐI ƯU 2: RENDER VIDEO (ULTRA FAST PARAMS)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Bước 1: Chuẩn bị lớp ảnh tĩnh (Gộp Nền + Nhân vật)
        static_bg_path = get_path('assets', 'images', 'default_background.png')
        final_static_img = prepare_static_layers(custom_image_path, static_bg_path, episode_id)
        
        # Bước 2: Tạo các Clips
        # Lớp 1: Ảnh tĩnh (Nền + Nhân vật đã Blend)
        base_layer = ImageClip(final_static_img).set_duration(duration)

        # Lớp 2: Video Overlay (Mây/Khói/Bụi) - GIẢM OPACITY XUỐNG ĐỂ TIẾT KIỆM TÍNH TOÁN
        video_overlay = None
        video_path = get_path('assets', 'video', 'long_background.mp4')
        if os.path.exists(video_path):
            try:
                ov_clip = VideoFileClip(video_path, audio=False).resize(height=OUTPUT_HEIGHT)
                if ov_clip.duration < duration:
                    ov_clip = ov_clip.fx(vfx.loop, duration=duration)
                video_overlay = ov_clip.subclip(0, duration).set_opacity(0.3)
            except: pass

        # Lớp 3: Title
        title_layer = None
        if title_text:
            title_layer = TextClip(
                title_text.upper(), fontsize=55, font='DejaVu-Sans-Bold', color='#FFD700',
                stroke_color='black', stroke_width=2, method='caption', size=(900, None)
            ).set_position(('center', 100)).set_duration(duration)

        # Bước 3: Tổng hợp (Compositing)
        layers = [base_layer]
        if video_overlay: layers.append(video_overlay)
        if title_layer: layers.append(title_layer)
        
        final_video = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        # Bước 4: Xuất file với cấu hình TỐI ƯU NHẤT cho GitHub Actions
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        
        logger.info(f"🚀 Render: FPS=12 (Tối ưu AI), CRF=32 (Tốc độ cao)...")
        final_video.write_videofile(
            output_path, 
            fps=12,                # Giảm xuống 12fps (vẫn mượt cho video tĩnh, render nhanh gấp đôi)
            codec="libx264", 
            preset="ultrafast",     # Nhanh nhất
            threads=4,              # Tận dụng CPU đa nhân
            ffmpeg_params=["-crf", "32"], # Nén mạnh để giảm tải ổ đĩa và upload nhanh
            logger='bar'
        )
        
        final_video.close()
        audio.close()
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Render: {e}")
        return False
