# scripts/create_shorts.py
import logging
import os
import math 
from PIL import Image, ImageEnhance, ImageFilter
import PIL.Image

# =======================================================
# 🛠️ [QUAN TRỌNG] VÁ LỖI PILLOW 10 VÀ MOVIEPY
# MoviePy cũ dùng ANTIALIAS, Pillow mới đã bỏ nó.
# =======================================================
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    else:
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# =======================================================

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip, 
    TextClip, CompositeVideoClip
)
from utils import get_path

logger = logging.getLogger(__name__)

# --- CẤU HÌNH SHORTS ---
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SHORTS_SIZE = (SHORTS_WIDTH, SHORTS_HEIGHT)
FPS = 24 

# =========================================================
# 🎨 1. HÀM TẠO SUBTITLE KIỂU HORMOZI (WORD-BY-WORD)
# =========================================================
def generate_subtitle_clips(text, total_duration, font_name="Impact.ttf"):
    """
    Tạo phụ đề từng từ một, xuất hiện chính giữa màn hình.
    Thời gian hiển thị được tính toán dựa trên độ dài từ.
    """
    if not text: return []
    
    # Tìm font
    font_path = get_path('assets', 'fonts', font_name)
    if not os.path.exists(font_path):
        logger.warning(f"⚠️ Không tìm thấy font {font_name}, dùng font mặc định.")
        font_path = 'Arial-Bold' # Fallback
        
    words = text.split()
    if not words: return []

    # Tính toán thời gian (Weighted Duration)
    total_chars = sum(len(w) for w in words)
    if total_chars == 0: return []
    
    clips = []
    current_start = 0.0

    # Style cấu hình
    FONT_SIZE = 110          
    TEXT_COLOR = "#FFD700"   # Vàng Gold
    STROKE_COLOR = "black"   
    STROKE_WIDTH = 6         
    
    for word in words:
        # Công thức: Từ càng dài thì hiện càng lâu
        weight = len(word) + 1 
        word_duration = (weight / (total_chars + len(words))) * total_duration
        
        try:
            # method='label' tốt hơn cho từ đơn (auto-resize)
            txt_clip = (TextClip(
                            word.upper(), 
                            font=font_path, 
                            fontsize=FONT_SIZE, 
                            color=TEXT_COLOR, 
                            stroke_color=STROKE_COLOR, 
                            stroke_width=STROKE_WIDTH,
                            method='label' 
                        )
                        .set_position(('center', 'center')) # Giữa màn hình
                        .set_start(current_start)
                        .set_duration(word_duration))
            
            clips.append(txt_clip)
        except Exception as e:
            logger.error(f"⚠️ Lỗi render sub từ '{word}': {e}")
            pass
            
        current_start += word_duration

    return clips

# =========================================================
# 🖼️ 2. HÀM XỬ LÝ BACKGROUND (AUTO BLUR)
# =========================================================
def create_cinematic_background(image_path, duration):
    """
    Tạo nền 9:16 từ ảnh 16:9:
    - Lớp dưới: Ảnh phóng to + làm mờ (Blur)
    - Lớp trên: Ảnh gốc giữ nguyên tỉ lệ ở giữa
    """
    if not image_path or not os.path.exists(image_path):
        return ColorClip(SHORTS_SIZE, color=(20,20,20), duration=duration)

    try:
        # Lớp nền mờ (Background Blur)
        bg_clip = (ImageClip(image_path)
                   .resize(height=SHORTS_HEIGHT) # Resize cao bằng màn hình -> sẽ bị crop 2 bên
                   .crop(x1=0, y1=0, width=SHORTS_WIDTH, height=SHORTS_HEIGHT, x_center=SHORTS_WIDTH/2, y_center=SHORTS_HEIGHT/2)
                   .fl_image(lambda image: image.filter(ImageFilter.GaussianBlur(radius=20))) # Làm mờ
                   .set_duration(duration))

        # Lớp chính (Main Image) - nằm giữa
        main_clip = (ImageClip(image_path)
                     .resize(width=SHORTS_WIDTH) # Resize rộng bằng màn hình
                     .set_position(('center', 'center'))
                     .set_duration(duration))
        
        return [bg_clip, main_clip]
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý background: {e}")
        return [ColorClip(SHORTS_SIZE, color=(20,20,20), duration=duration)]

# =========================================================
# 🎬 3. HÀM CHÍNH: CREATE SHORTS
# =========================================================
def create_shorts(episode_id, audio_path, script_path=None, image_path=None, hook_title=None):
    """
    Quy trình dựng Shorts:
    Audio -> Background (Blur+Main) -> Subtitle (Hormozi) -> Hook Title -> Render
    """
    if not audio_path or not os.path.exists(audio_path):
        logger.error("❌ Thiếu file Audio input.")
        return None

    try:
        # 1. Load Audio
        final_audio = AudioFileClip(audio_path)
        duration = final_audio.duration
        
        # 2. Tạo Background Layers
        logger.info("🎨 Đang tạo Background...")
        bg_layers = create_cinematic_background(image_path, duration)
        elements = bg_layers # List chứa các clips

        # 3. Tạo Subtitles (Hormozi Style)
        if script_path and os.path.exists(script_path):
            logger.info("📝 Đang tạo Subtitles...")
            with open(script_path, "r", encoding="utf-8") as f:
                full_text = f.read()
            
            subs = generate_subtitle_clips(full_text, duration, font_name="Impact.ttf")
            if subs:
                elements.extend(subs)

        # 4. Tạo Hook Title (Tiêu đề tĩnh ở trên cùng)
        if hook_title:
            try:
                # Tìm font Impact cho Hook luôn cho đồng bộ
                font_path = get_path('assets', 'fonts', 'Impact.ttf')
                if not os.path.exists(font_path): font_path = 'Arial-Bold'

                hook_clip = (TextClip(
                                hook_title.upper(), 
                                fontsize=80, 
                                color='white', 
                                font=font_path,
                                stroke_color='black', 
                                stroke_width=4,
                                method='label'
                            )
                            .set_position(('center', 200)) # Cách mép trên 200px
                            .set_duration(duration))
                elements.append(hook_clip)
            except Exception as e:
                logger.warning(f"⚠️ Không tạo được Hook Title: {e}")

        # 5. Render Video
        # set_audio cho composite clip
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)

        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        logger.info(f"🚀 Rendering Shorts: {out_path} ({duration:.1f}s)")
        
        # Preset ultrafast để tiết kiệm thời gian trên GitHub Actions
        final.write_videofile(
            out_path, 
            fps=FPS, 
            codec='libx264', 
            audio_codec='aac',
            preset='ultrafast', 
            threads=2,
            logger=None # Tắt log ffmpeg dài dòng
        )

        # Cleanup
        final.close()
        final_audio.close()
        for clip in elements:
            try: clip.close() 
            except: pass
            
        logger.info("✅ Shorts render xong!")
        return out_path

    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng khi tạo Shorts: {e}", exc_info=True)
        return None
