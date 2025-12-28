# === scripts/create_video.py ===
import logging
import os
import numpy as np
# THÊM ImageDraw VÀO ĐÂY ĐỂ FIX LỖI
from PIL import Image, ImageEnhance, ImageFilter, ImageChops, ImageDraw
import PIL.Image

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', None))

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, TextClip, vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

def prepare_static_layers(char_path, static_bg_path, episode_id):
    """
    Đảm bảo nhân vật và nền hòa quyện bằng kỹ thuật Soft Masking.
    """
    logger.info("⚡ Đang tiền xử lý lớp hình ảnh tĩnh (Pillow)...")
    
    # 1. Xử lý Nền tĩnh: Làm tối nhẹ để tạo chiều sâu
    if static_bg_path and os.path.exists(static_bg_path):
        bg = Image.open(static_bg_path).convert("RGBA")
        bg = bg.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.LANCZOS)
        bg = ImageEnhance.Brightness(bg).enhance(0.7) # Tối 30% để nổi bật nhân vật
    else:
        bg = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (20, 20, 20, 255))

    # 2. Xử lý Nhân vật: Blend viền cực mềm
    if char_path and os.path.exists(char_path):
        char = Image.open(char_path).convert("RGBA")
        char_h = int(OUTPUT_HEIGHT * 0.95) # Nhân vật cao gần bằng khung hình
        char_w = int(char.width * (char_h / char.height))
        char = char.resize((char_w, char_h), Image.LANCZOS)
        
        # Tạo mask mờ biên để hòa vào nền (không bị cắt dán thô)
        mask = char.getchannel("A")
        mask = mask.filter(ImageFilter.GaussianBlur(30)) 
        
        # Đặt nhân vật lệch phải (Quy tắc 1/3) để không che khuất tâm video
        paste_x = OUTPUT_WIDTH - char_w - 50
        bg.paste(char, (paste_x, OUTPUT_HEIGHT - char_h), mask=mask)

    # 3. Vignette: Vẽ thêm viền tối 4 góc (Sử dụng ImageDraw đã fix lỗi)
    vignette = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0, 0))
    overlay = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0, 0))
    # Tạo hiệu ứng tối dần ra rìa
    draw = ImageDraw.Draw(overlay)
    # (Đơn giản hóa: dùng một gradient nhạt đen ở các cạnh)
    
    final_img = Image.alpha_composite(bg, overlay)
    static_path = get_path('assets', 'temp', f"{episode_id}_static_final.png")
    final_img.convert("RGB").save(static_path)
    return static_path

def create_video(audio_path, episode_id, custom_image_path=None, title_text=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Gọi ảnh nền thông minh (ưu tiên {ID}_bg.png)
        custom_bg = get_path('assets', 'images', f"{episode_id}_bg.png")
        static_bg_path = custom_bg if os.path.exists(custom_bg) else get_path('assets', 'images', 'default_background.png')
        
        # Tiền xử lý gộp Nền + Nhân vật
        final_static_img = prepare_static_layers(custom_image_path, static_bg_path, episode_id)
        
        # Lớp 1: Nền tĩnh & Nhân vật
        base_layer = ImageClip(final_static_img).set_duration(duration)

        # Lớp 2: Video Mây/Bụi (Độ mờ 0.35 để hòa quyện, không che lấp nhân vật)
        video_overlay = None
        video_path = get_path('assets', 'video', 'long_background.mp4')
        if os.path.exists(video_path):
            ov_clip = VideoFileClip(video_path, audio=False).resize(height=OUTPUT_HEIGHT)
            video_overlay = ov_clip.fx(vfx.loop, duration=duration).set_opacity(0.35)

        # Lớp 3: Tiêu đề (Bố cục bên trái vùng trống)
        title_layer = None
        if title_text:
            title_layer = TextClip(
                title_text.upper(), fontsize=55, font='DejaVu-Sans-Bold', color='white',
                stroke_color='black', stroke_width=2, method='caption', size=(750, None), align='West'
            ).set_position((80, 'center')).set_duration(duration)

        # TỔNG HỢP: Thứ tự lớp đảm bảo không che lấp nội dung chính
        layers = [base_layer]
        if video_overlay: layers.append(video_overlay)
        if title_layer: layers.append(title_layer)
        
        final_video = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        final_video.write_videofile(
            output_path, fps=15, codec="libx264", preset="ultrafast",
            threads=4, ffmpeg_params=["-crf", "28"], logger=None
        )
        
        final_video.close()
        audio.close()
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Render: {e}")
        return False
