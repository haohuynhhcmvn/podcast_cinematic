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

# Cấu hình Shorts
SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SHORTS_SIZE = (SHORTS_WIDTH, SHORTS_HEIGHT)
MAX_DURATION = 60 

# =========================================================
# 🌑 [NEW] HÀM XỬ LÝ NỀN SHORTS TỪ ẢNH NHÂN VẬT
# =========================================================
def process_shorts_background(input_path, output_path, width=SHORTS_WIDTH, height=SHORTS_HEIGHT):
    """
    Chuyển ảnh nhân vật (ngang/vuông) thành nền dọc 9:16 mờ ảo.
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGB")
            
            # 1. Resize Aspect Fill (Lấp đầy khung hình dọc)
            target_ratio = width / height
            img_ratio = img.width / img.height
            
            if img_ratio > target_ratio:
                # Ảnh gốc rộng hơn -> Cắt bớt chiều ngang
                new_height = height
                new_width = int(new_height * img_ratio)
            else:
                # Ảnh gốc cao hơn (hiếm) -> Cắt bớt chiều dọc
                new_width = width
                new_height = int(new_width / img_ratio)
                
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Center Crop
            left = (new_width - width) // 2
            top = (new_height - height) // 2
            img_cropped = img_resized.crop((left, top, left + width, top + height))
            
            # 2. Tạo hiệu ứng Nền Mờ (Blurred & Darkened)
            # Blur mạnh để làm nền
            img_blurred = img_cropped.filter(ImageFilter.GaussianBlur(radius=40)) 
            
            # Làm tối đi 50% để tôn chữ trắng/vàng
            enhancer = ImageEnhance.Brightness(img_blurred)
            final_img = enhancer.enhance(0.5) 
            
            final_img.save(output_path, quality=90)
            return output_path
            
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý nền Shorts: {e}")
        return None

# =========================================================
# 🛠️ HÀM TẠO PHỤ ĐỀ (GIỮ NGUYÊN)
# =========================================================
def generate_subtitle_clips(text_content, total_duration, fontsize=70):
    if not text_content: return []
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
        
        txt_clip = TextClip(
            chunk.upper(),
            fontsize=fontsize,
            font='DejaVu-Sans-Bold',
            color='yellow',
            stroke_color='black',
            stroke_width=4,
            size=(900, None),
            method='caption',
            align='center'
        )
        txt_clip = txt_clip.set_position(('center', 'center')).set_start(start_time).set_duration(time_per_chunk)
        subtitle_clips.append(txt_clip)

    return subtitle_clips


# =========================================================
# 🎬 HÀM CHÍNH: TẠO SHORTS (ĐÃ CẬP NHẬT LOGIC NỀN)
# =========================================================
# 👇 THÊM THAM SỐ custom_image_path VÀO ĐÂY
def create_shorts(audio_path, hook_title, episode_id, character_name, script_path, custom_image_path=None): 
    try:
        # 1. Load Voice & Cut 60s
        if not os.path.exists(audio_path):
            return None
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

        # --- 3. XỬ LÝ VIDEO NỀN (LOGIC MỚI) ---
        clip = None
        
        # [ƯU TIÊN 1]: Xử lý ảnh nhân vật thành nền mờ dọc
        if custom_image_path and os.path.exists(custom_image_path):
            logger.info(f"🖼️ Đang tạo nền Shorts từ ảnh nhân vật...")
            processed_shorts_bg = get_path('assets', 'temp', f"{episode_id}_shorts_bg.jpg")
            os.makedirs(os.path.dirname(processed_shorts_bg), exist_ok=True)
            
            final_bg_path = process_shorts_background(custom_image_path, processed_shorts_bg)
            
            if final_bg_path:
                clip = ImageClip(final_bg_path).set_duration(duration)

        # [ƯU TIÊN 2]: Ảnh nền đá "sạch" (Fallback)
        bg_static_clean = get_path('assets', 'images', 'bg_short_epic.png')
        if clip is None and os.path.exists(bg_static_clean):
             clip = ImageClip(bg_static_clean).set_duration(duration).resize(SHORTS_SIZE)

        # [FALLBACK CUỐI]: Màu đen
        if clip is None:
            clip = ColorClip(SHORTS_SIZE, color=(20,20,20), duration=duration)

        elements = [clip]

        # 4. Text Hook (Trên cùng)
        if hook_title:
            try:
                hook_clip = TextClip(
                    hook_title, 
                    fontsize=80, color='white', font='DejaVu-Sans-Bold', 
                    method='caption', size=(1000, None), 
                    stroke_color='black', stroke_width=5, align='center'
                ).set_pos(('center', 250)).set_duration(duration)
                elements.append(hook_clip)
            except Exception: pass

        # 5. Phụ đề (Giữa màn hình)
        if script_path and os.path.exists(script_path):
            try:
                with open(script_path, "r", encoding="utf-8") as f: full_script = f.read()
                subs = generate_subtitle_clips(full_script, duration)
                if subs: elements.extend(subs)
            except Exception: pass

        # 6. Render
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        logger.info("🚀 Đang render Shorts...")
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        return out_path

    except Exception as e:
        logger.error(f"❌ Lỗi Shorts: {e}", exc_info=True)
        return None
