# scripts/create_shorts.py

import logging
import os
import math 
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip, 
    TextClip, CompositeVideoClip, CompositeAudioClip, concatenate_audioclips
)
from utils import get_path

logger = logging.getLogger(__name__)

SHORTS_SIZE = (1080, 1920)
MAX_DURATION = 60 

# =========================================================
# 🌑 HÀM XỬ LÝ NỀN SHORTS: VERTICAL VIGNETTE
# =========================================================
def process_shorts_background(input_path, output_path, width=1080, height=1920):
    """
    Tạo nền dọc: Blur nhẹ + Gradient tối ở Đỉnh và Đáy (Chữ dễ đọc).
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGBA")
            
            # 1. Resize & Crop 9:16
            target_ratio = width / height
            img_ratio = img.width / img.height
            
            if img_ratio > target_ratio:
                new_height = height
                new_width = int(new_height * img_ratio)
            else:
                new_width = width
                new_height = int(new_width / img_ratio)
                
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            left = (new_width - width) // 2
            top = (new_height - height) // 2
            img_cropped = img.crop((left, top, left + width, top + height))
            
            # 2. Blur (Mức độ vừa phải để còn thấy hình dáng nhân vật)
            img_blurred = img_cropped.filter(ImageFilter.GaussianBlur(radius=30))
            
            # 3. Tạo Gradient Dọc (Tối ở trên cùng và dưới cùng)
            gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(gradient)
            
            for y in range(height):
                # Tỷ lệ vị trí Y (0.0 -> 1.0)
                pct = y / height
                
                # Logic:
                # 0% - 20% (Đỉnh): Tối (cho Hook Title)
                # 20% - 80% (Giữa): Sáng (cho Nhân vật)
                # 80% - 100% (Đáy): Tối (cho Subtitles)
                
                if pct < 0.2: 
                    alpha = int(180 * (1 - (pct / 0.2))) # Giảm dần từ 180 về 0
                elif pct > 0.8:
                    alpha = int(180 * ((pct - 0.8) / 0.2)) # Tăng dần từ 0 lên 180
                else:
                    alpha = 0 # Trong suốt ở giữa
                
                # Vẽ đường ngang
                draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
            
            # 4. Hòa trộn
            final_img = Image.alpha_composite(img_blurred, gradient)
            
            # Làm tối tổng thể một chút (Enhance 0.6)
            final_img = final_img.convert("RGB")
            enhancer = ImageEnhance.Brightness(final_img)
            final_img = enhancer.enhance(0.6) 
            
            final_img.save(output_path, quality=90)
            return output_path
            
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý nền Shorts: {e}")
        return None

# =========================================================
# 🛠️ HÀM TẠO PHỤ ĐỀ (VỊ TRÍ CHUẨN)
# =========================================================
def generate_subtitle_clips(text_content, total_duration, fontsize=85):
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
            color='#FFD700',      # Vàng Gold
            stroke_color='black',
            stroke_width=6,
            size=(950, None),
            method='caption',
            align='center'
        )
        # Đặt ở vùng tối bên dưới (Y=1400)
        txt_clip = txt_clip.set_position(('center', 1400)).set_start(start_time).set_duration(time_per_chunk)
        subtitle_clips.append(txt_clip)

    return subtitle_clips

# =========================================================
# 🎬 HÀM CHÍNH SHORTS
# =========================================================
def create_shorts(audio_path, hook_title, episode_id, character_name, script_path, custom_image_path=None): 
    try:
        if not os.path.exists(audio_path): return None
        voice = AudioFileClip(audio_path).volumex(1.5) 
        duration = min(voice.duration, MAX_DURATION) 
        voice = voice.subclip(0, duration) 
        
        # Nhạc nền
        bg_music_path = get_path('assets', 'background_music', 'loop_1.mp3')
        if os.path.exists(bg_music_path):
            bg_music = AudioFileClip(bg_music_path).volumex(0.1) 
            num_loops = math.ceil(duration / bg_music.duration)
            bg_music_looped = concatenate_audioclips([bg_music]*num_loops).subclip(0, duration)
            final_audio = CompositeAudioClip([bg_music_looped, voice])
        else:
            final_audio = voice

        # Background
        clip = None
        if custom_image_path and os.path.exists(custom_image_path):
            processed_shorts_bg = get_path('assets', 'temp', f"{episode_id}_shorts_bg.jpg")
            os.makedirs(os.path.dirname(processed_shorts_bg), exist_ok=True)
            final_bg_path = process_shorts_background(custom_image_path, processed_shorts_bg)
            if final_bg_path:
                clip = ImageClip(final_bg_path).set_duration(duration)

        if clip is None:
            clip = ColorClip(SHORTS_SIZE, color=(20,20,20), duration=duration)

        elements = [clip]

        # HOOK TITLE (Vùng tối trên cùng - Y=200)
        if hook_title:
            try:
                hook_clip = TextClip(
                    hook_title.upper(), 
                    fontsize=90, color='white', font='DejaVu-Sans-Bold', 
                    method='caption', size=(1000, None), 
                    stroke_color='black', stroke_width=8, align='center'
                ).set_pos(('center', 200)).set_duration(duration)
                elements.append(hook_clip)
            except Exception: pass

        # SUBTITLES
        if script_path and os.path.exists(script_path):
            try:
                with open(script_path, "r", encoding="utf-8") as f: full_script = f.read()
                subs = generate_subtitle_clips(full_script, duration)
                if subs: elements.extend(subs)
            except Exception: pass

        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        logger.info("🚀 Rendering Shorts...")
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        return out_path

    except Exception as e:
        logger.error(f"❌ Shorts Error: {e}", exc_info=True)
        return None
