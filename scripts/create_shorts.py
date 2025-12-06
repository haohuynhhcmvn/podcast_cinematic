# scripts/create_shorts.py

import logging
import os
import math 
from PIL import Image, ImageEnhance, ImageFilter
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip, 
    TextClip, CompositeVideoClip, CompositeAudioClip, concatenate_audioclips
)
from utils import get_path

logger = logging.getLogger(__name__)

# Cấu hình Shorts chuẩn HD
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SHORTS_SIZE = (SHORTS_WIDTH, SHORTS_HEIGHT)
MAX_DURATION = 60 

# =========================================================
# 🌑 HÀM XỬ LÝ NỀN SHORTS (TỐI HƠN & MỜ HƠN)
# =========================================================
def process_shorts_background(input_path, output_path, width=SHORTS_WIDTH, height=SHORTS_HEIGHT):
    """
    Tạo nền dọc: Blur mạnh và làm tối ĐẬM để chữ nổi bật.
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGB")
            
            # 1. Resize Aspect Fill
            target_ratio = width / height
            img_ratio = img.width / img.height
            
            if img_ratio > target_ratio:
                new_height = height
                new_width = int(new_height * img_ratio)
            else:
                new_width = width
                new_height = int(new_width / img_ratio)
                
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Center Crop
            left = (new_width - width) // 2
            top = (new_height - height) // 2
            img_cropped = img_resized.crop((left, top, left + width, top + height))
            
            # 2. Xử lý hiệu ứng
            # Blur rất mạnh để tạo chiều sâu (Depth)
            img_blurred = img_cropped.filter(ImageFilter.GaussianBlur(radius=50)) 
            
            # Làm tối đi 60% (Chỉ giữ lại 40% độ sáng) -> Chữ sẽ cực nổi
            enhancer = ImageEnhance.Brightness(img_blurred)
            final_img = enhancer.enhance(0.4) 
            
            final_img.save(output_path, quality=90)
            return output_path
            
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý nền Shorts: {e}")
        return None

# =========================================================
# 🛠️ HÀM TẠO PHỤ ĐỀ (DỜI XUỐNG DƯỚI & STYLE MỚI)
# =========================================================
def generate_subtitle_clips(text_content, total_duration, fontsize=85):
    if not text_content: return []
    
    # Tách từ và gom nhóm (3-4 từ/câu)
    words = text_content.replace('\n', ' ').split()
    if not words: return []

    chunk_size = 4
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk_text = " ".join(words[i:i + chunk_size])
        chunks.append(chunk_text)

    num_chunks = len(chunks)
    time_per_chunk = total_duration / num_chunks
    subtitle_clips = []
    
    for i, chunk in enumerate(chunks):
        start_time = i * time_per_chunk
        
        # STYLE CHUẨN VIRAL:
        # - Font: DejaVu-Sans-Bold (Có sẵn)
        # - Màu: Vàng Gold (#FFD700)
        # - Viền: Đen dày (stroke_width=6)
        # - Vị trí: Dưới thấp (Y=1300) thay vì giữa màn hình
        
        txt_clip = TextClip(
            chunk.upper(),
            fontsize=fontsize,
            font='DejaVu-Sans-Bold',
            color='#FFD700',      # Vàng Gold
            stroke_color='black',
            stroke_width=6,       # Viền dày hơn
            size=(950, None),     # Rộng gần full màn hình
            method='caption',
            align='center'
        )
        
        # VỊ TRÍ QUAN TRỌNG: ('center', 1300)
        # Đặt chữ ở khoảng 70% chiều cao màn hình (tránh nút like/comment bên phải)
        txt_clip = txt_clip.set_position(('center', 1300)).set_start(start_time).set_duration(time_per_chunk)
        subtitle_clips.append(txt_clip)

    return subtitle_clips


# =========================================================
# 🎬 HÀM CHÍNH: TẠO SHORTS
# =========================================================
def create_shorts(audio_path, hook_title, episode_id, character_name, script_path, custom_image_path=None): 
    try:
        # 1. Load Voice & Cut
        if not os.path.exists(audio_path): return None
        voice = AudioFileClip(audio_path).volumex(1.5) 
        duration = min(voice.duration, MAX_DURATION) 
        voice = voice.subclip(0, duration) 
        logger.info(f"⏳ Shorts Duration: {duration:.2f}s")

        # 2. Nhạc Nền
        bg_music_path = get_path('assets', 'background_music', 'loop_1.mp3')
        if os.path.exists(bg_music_path):
            bg_music = AudioFileClip(bg_music_path).volumex(0.1) 
            num_loops = math.ceil(duration / bg_music.duration)
            bg_clips = [bg_music] * num_loops
            bg_music_looped = concatenate_audioclips(bg_clips).subclip(0, duration)
            final_audio = CompositeAudioClip([bg_music_looped, voice])
        else:
            final_audio = voice

        # 3. Video/Ảnh Nền
        clip = None
        
        # [ƯU TIÊN]: Nền từ ảnh nhân vật (đã làm tối)
        if custom_image_path and os.path.exists(custom_image_path):
            processed_shorts_bg = get_path('assets', 'temp', f"{episode_id}_shorts_bg.jpg")
            os.makedirs(os.path.dirname(processed_shorts_bg), exist_ok=True)
            
            final_bg_path = process_shorts_background(custom_image_path, processed_shorts_bg)
            if final_bg_path:
                clip = ImageClip(final_bg_path).set_duration(duration)

        # Fallback
        if clip is None:
            bg_static_clean = get_path('assets', 'images', 'bg_short_epic.png')
            if os.path.exists(bg_static_clean):
                 clip = ImageClip(bg_static_clean).set_duration(duration).resize(SHORTS_SIZE)
            else:
                clip = ColorClip(SHORTS_SIZE, color=(20,20,20), duration=duration)

        elements = [clip]

        # 4. HOOK TITLE (TIÊU ĐỀ TRÊN CÙNG)
        if hook_title:
            try:
                # Chữ Trắng, Viền Đen, Size cực to
                hook_clip = TextClip(
                    hook_title.upper(), 
                    fontsize=90, 
                    color='white', 
                    font='DejaVu-Sans-Bold', 
                    method='caption', 
                    size=(1000, None), 
                    stroke_color='black', 
                    stroke_width=8, 
                    align='center'
                )
                # Đặt vị trí cao (Y=200) để tách biệt với phụ đề
                hook_clip = hook_clip.set_pos(('center', 200)).set_duration(duration)
                elements.append(hook_clip)
            except Exception as e:
                logger.warning(f"⚠️ Lỗi Hook Title: {e}")

        # 5. PHỤ ĐỀ (SUBTITLES)
        if script_path and os.path.exists(script_path):
            try:
                with open(script_path, "r", encoding="utf-8") as f: full_script = f.read()
                subs = generate_subtitle_clips(full_script, duration)
                if subs: elements.extend(subs)
            except Exception: pass
            
        # [NEW] 6. THÊM ẢNH NHÂN VẬT GỐC (NHỎ) Ở GIỮA?
        # Tùy chọn: Nếu muốn chèn ảnh nhân vật không bị mờ ở giữa, cần xử lý tách nền phức tạp.
        # Ở đây ta giữ nguyên nền mờ để tập trung vào chữ.

        # 7. Render
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        logger.info("🚀 Đang render Shorts...")
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        return out_path

    except Exception as e:
        logger.error(f"❌ Lỗi Shorts: {e}", exc_info=True)
        return None
