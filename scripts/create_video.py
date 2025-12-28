# === scripts/create_video.py ===
import logging
import os
from moviepy.editor import *
from PIL import Image, ImageEnhance, ImageFilter
from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
TARGET_FPS = 15  # 15 FPS là "điểm ngọt" cho documentary, nhanh hơn 18-20 FPS rất nhiều

def create_video(audio_path, episode_id, custom_image_path=None, title_text=""):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # --- GIAI ĐOẠN 1: TỐI ƯU HÓA ẢNH TĨNH BẰNG PILLOW (SIÊU NHANH) ---
        # Thay vì dùng MoviePy layers, ta tạo 1 tấm kính duy nhất chứa Nhân vật + Hiệu ứng
        overlay_static_path = get_path("assets", "temp", f"{episode_id}_composite_overlay.png")
        
        # Tạo canvas trong suốt
        composite_img = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0, 0))
        
        if custom_image_path and os.path.exists(custom_image_path):
            char_img = Image.open(custom_image_path).convert("RGBA")
            # Resize nhân vật chuẩn HD
            char_img = char_img.resize((int(char_img.width * (OUTPUT_HEIGHT / char_img.height)), OUTPUT_HEIGHT), Image.LANCZOS)
            
            # Tăng tương phản bằng Pillow (nhanh hơn MoviePy gấp 10 lần)
            enhancer = ImageEnhance.Contrast(char_img)
            char_img = enhancer.enhance(1.15)
            
            # Dán vào bên phải (Rule of Thirds)
            paste_x = OUTPUT_WIDTH - char_img.width
            composite_img.paste(char_img, (paste_x, 0), char_img)

        # Lưu file ảnh đã composite để MoviePy chỉ việc load 1 lần
        composite_img.save(overlay_static_path)
        char_overlay_clip = ImageClip(overlay_static_path).set_duration(duration)

        # --- GIAI ĐOẠN 2: XỬ LÝ VIDEO NỀN ---
        bg_video_path = get_path("assets", "video", "long_background.mp4")
        if os.path.exists(bg_video_path):
            # TỐI ƯU: Bỏ qua audio stream và resize ngay khi load
            bg_clip = VideoFileClip(bg_video_path, audio=False, target_resolution=(OUTPUT_HEIGHT, OUTPUT_WIDTH))
            bg_clip = bg_clip.fx(vfx.loop, duration=duration).set_opacity(0.7)
        else:
            bg_clip = ColorClip(size=(OUTPUT_WIDTH, OUTPUT_HEIGHT), color=(15, 15, 15)).set_duration(duration)

        # Lớp Vignette tĩnh (Load từ file ảnh sẽ nhanh hơn tạo ColorClip)
        # Nếu chưa có file vignette.png, hãy dùng ColorClip cũ nhưng bản chất nó là tĩnh nên ko tốn CPU
        vignette = ColorClip(size=(OUTPUT_WIDTH, OUTPUT_HEIGHT), color=(0,0,0)).set_duration(duration).set_opacity(0.35)

        # --- GIAI ĐOẠN 3: TIÊU ĐỀ ---
        layers = [bg_clip, vignette, char_overlay_clip]
        
        if title_text:
            # Tối ưu: Caption method của MoviePy tốn CPU, nhưng vì nó ngắn nên tạm chấp nhận
            title = TextClip(
                title_text.upper(), fontsize=60, color='white', 
                font='DejaVu-Sans-Bold', method='caption',
                size=(OUTPUT_WIDTH * 0.55, None), align='West',
                stroke_color='black', stroke_width=2
            ).set_position((80, 'center')).set_duration(duration)
            layers.append(title)

        # --- GIAI ĐOẠN 4: RENDER FINAL ---
        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        out_path = get_path("outputs", "video", f"{episode_id}_video.mp4")
        
        logger.info(f"🚀 Render Start: FPS=15, CRF=26 (Cân bằng tốc độ/đẹp)")
        
        final.write_videofile(
            out_path, 
            fps=15, 
            codec="libx264", 
            audio_codec="aac",
            preset="ultrafast", 
            threads=4, 
            ffmpeg_params=["-crf", "26"], # 26 nhanh hơn 23 mà mắt thường khó phân biệt trên phone
            logger='bar'
        )

        # Giải phóng RAM
        final.close()
        audio.close()
        bg_clip.close()
        if os.path.exists(overlay_static_path):
            os.remove(overlay_static_path)
            
        return out_path

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False
