# scripts/create_video.py
# PHIÊN BẢN PRODUCTION – CÓ SUBTITLES CHO VIDEO DÀI
# - Bỏ waveform (giảm CPU/RAM)
# - Cache static background
# - Thêm Subtitles Word-by-Word ở dưới đáy

import logging
import os
import hashlib

from PIL import Image, ImageFilter
import PIL.Image

# ===== FIX PILLOW / MOVIEPY =====
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    else:
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# =================================

from moviepy.editor import (
    AudioFileClip, ImageClip, CompositeVideoClip, TextClip
)

from utils import get_path

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720

# ============================================================
# 🧠 B2. CACHE STATIC BACKGROUND IMAGE
# ============================================================
def get_cached_background_image(bg_image_path, width, height):
    """
    Cache background image sau resize để tái sử dụng.
    """
    cache_dir = get_path("assets", "temp", "bg_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    # Tạo key hash dựa trên đường dẫn ảnh
    key_hash = hashlib.md5(bg_image_path.encode('utf-8')).hexdigest()
    cached_path = os.path.join(cache_dir, f"{key_hash}_{width}x{height}.png")

    if os.path.exists(cached_path):
        return cached_path

    # Nếu chưa có cache, tạo mới (Cinematic Blur)
    try:
        img = Image.open(bg_image_path).convert("RGBA")
        
        # 1. Tạo nền mờ (Background Blur)
        bg_blur = img.resize((width, height))
        bg_blur = bg_blur.filter(ImageFilter.GaussianBlur(radius=15))
        
        # 2. Tạo ảnh chính (Main Image) giữ tỉ lệ
        img_ratio = img.width / img.height
        target_ratio = width / height
        
        if img_ratio > target_ratio:
            new_w = width
            new_h = int(width / img_ratio)
        else:
            new_h = height
            new_w = int(height * img_ratio)
            
        if hasattr(PIL.Image, 'ANTIALIAS'):
            img_main = img.resize((new_w, new_h), PIL.Image.ANTIALIAS)
        else:
            img_main = img.resize((new_w, new_h))
        
        # 3. Ghép
        final_img = Image.new("RGBA", (width, height), (0,0,0,255))
        final_img.paste(bg_blur, (0,0))
        
        # Căn giữa
        pos_x = (width - new_w) // 2
        pos_y = (height - new_h) // 2
        final_img.paste(img_main, (pos_x, pos_y), img_main)

        # Lưu cache
        final_img.save(cached_path)
        return cached_path
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý ảnh nền: {e}")
        return bg_image_path # Fallback

# ============================================================
# 📝 [NEW] TẠO SUBTITLE CHO VIDEO DÀI (BOTTOM CENTER)
# ============================================================
def generate_long_subs(text, total_duration):
    """
    Tạo phụ đề chạy từng từ (Word-by-Word) ở dưới đáy màn hình.
    """
    if not text: return []
    
    # Tìm font
    font_path = get_path('assets', 'fonts', 'Impact.ttf')
    if not os.path.exists(font_path): 
        font_path = 'Arial-Bold' # Fallback
        
    words = text.split()
    if not words: return []

    total_chars = sum(len(w) for w in words)
    if total_chars == 0: return []
    
    clips = []
    current_start = 0.0
    
    # Cấu hình Style cho Long Video (Nhỏ hơn Shorts một chút)
    FONT_SIZE = 60          
    TEXT_COLOR = "#FFD700"   # Vàng
    STROKE_COLOR = "black"   
    STROKE_WIDTH = 3         
    
    for word in words:
        # Tính thời gian hiển thị (Weighted Duration)
        weight = len(word) + 1 
        word_duration = (weight / (total_chars + len(words))) * total_duration
        
        try:
            txt_clip = (TextClip(
                            word.upper(), 
                            font=font_path, 
                            fontsize=FONT_SIZE, 
                            color=TEXT_COLOR, 
                            stroke_color=STROKE_COLOR, 
                            stroke_width=STROKE_WIDTH,
                            method='label' 
                        )
                        # Vị trí: Giữa ngang, cách đáy 120px
                        .set_position(('center', OUTPUT_HEIGHT - 120)) 
                        .set_start(current_start)
                        .set_duration(word_duration))
            
            clips.append(txt_clip)
        except Exception: 
            pass
            
        current_start += word_duration

    return clips

# ============================================================
# 🎬 MAIN CREATE VIDEO
# ============================================================
def create_video(episode_id, audio_path, image_path, title_text, script_path=None):
    if not audio_path or not os.path.exists(audio_path):
        return None

    try:
        # 1. Audio
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # 2. Background Image (Cached)
        final_bg_path = get_cached_background_image(image_path, OUTPUT_WIDTH, OUTPUT_HEIGHT)
        background = ImageClip(final_bg_path).set_duration(duration)

        layers = [background]

        # 3. Tiêu đề (Title) - Xuất hiện 5s đầu
        if title_text:
            try:
                font_path = get_path('assets', 'fonts', 'Impact.ttf')
                if not os.path.exists(font_path): font_path = 'Arial-Bold'
                
                title_layer = (TextClip(
                    title_text.upper(),
                    fontsize=70, color='white', font=font_path,
                    stroke_color='black', stroke_width=4,
                    method='label'
                ).set_position(('center', 50)).set_duration(5).crossfadeout(1))
                
                layers.append(title_layer)
            except Exception: pass

        # 4. Logo (Góc phải trên)
        logo_path = get_path("assets", "images", "channel_logo.png")
        if os.path.exists(logo_path):
            logo_layer = (ImageClip(logo_path)
                          .resize(height=80)
                          .set_position(("right", "top"))
                          .margin(right=20, top=20, opacity=0)
                          .set_duration(duration))
            layers.append(logo_layer)

        # 5. [NEW] PHỤ ĐỀ (SUBTITLES)
        if script_path and os.path.exists(script_path):
            logger.info("📝 Đang tạo phụ đề cho Long Video...")
            with open(script_path, "r", encoding="utf-8") as f:
                full_text = f.read()
            
            subs = generate_long_subs(full_text, duration)
            if subs:
                layers.extend(subs)

        # Render
        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)

        out_path = get_path("outputs", "video", f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        logger.info("🚀 Rendering Long Video...")
        
        # Preset ultrafast để render nhanh trên GitHub Actions
        final.write_videofile(
            out_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=2,
            logger=None
        )

        # Cleanup
        final.close()
        audio.close()
        for l in layers: 
            try: l.close() 
            except: pass

        logger.info("✅ Video Long form xong!")
        return out_path

    except Exception as e:
        logger.error(f"❌ Lỗi create_video: {e}", exc_info=True)
        return None
