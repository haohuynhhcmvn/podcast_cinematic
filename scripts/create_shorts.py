# === scripts/create_shorts.py ===
import logging
import os
import math 
import random
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageChops
import PIL.Image 

# --- [FIX QUAN TRỌNG] VÁ LỖI PILLOW/MOVIEPY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling') and hasattr(PIL.Image.Resampling, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    elif hasattr(PIL.Image, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ------------------------------------------------------

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip, 
    TextClip, CompositeVideoClip, CompositeAudioClip, concatenate_audioclips, vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SHORTS_SIZE = (SHORTS_WIDTH, SHORTS_HEIGHT)
MAX_DURATION = 60 

# =========================================================
# 🎨 HÀM XỬ LÝ BACKGROUND HYBRID (9:16) - FIX HIỂN THỊ
# =========================================================
def process_hybrid_shorts_bg(char_path, base_bg_path, output_path):
    try:
        width, height = SHORTS_SIZE
        
        # 1. LOAD BASE BG (Ưu tiên ảnh dọc bg_short_epic.png)
        if base_bg_path and os.path.exists(base_bg_path):
            base_img = Image.open(base_bg_path).convert("RGBA")
        else:
            base_img = Image.new("RGBA", SHORTS_SIZE, (15,15,15,255))
            
        # Resize Fit/Fill thông minh cho nền
        img_ratio = base_img.width / base_img.height
        target_ratio = width / height
        
        if img_ratio > target_ratio:
            new_h = height
            new_w = int(new_h * img_ratio)
        else:
            new_w = width
            new_h = int(new_w / img_ratio)
            
        base_img = base_img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        base_img = base_img.crop((left, top, left + width, top + height))
        
        # Làm tối nền để nhân vật và chữ nổi bật
        enhancer = ImageEnhance.Brightness(base_img)
        base_img = enhancer.enhance(0.45) 

        # 2. XỬ LÝ NHÂN VẬT (Đặt giữa, không bị cắt)
        if char_path and os.path.exists(char_path):
            char_img = Image.open(char_path).convert("RGBA")
            # Nhân vật chiếm 85% chiều rộng để tạo khoảng thở (padding)
            char_w = int(width * 0.85)
            char_h = int(char_img.height * (char_w / char_img.width))
            char_img = char_img.resize((char_w, char_h), Image.LANCZOS)
            
            # Mask mờ biên trên dưới để hòa vào nền Epic
            mask = Image.new("L", (char_w, char_h), 255)
            draw = ImageDraw.Draw(mask)
            fade = int(char_h * 0.25)
            for y in range(char_h):
                if y < fade:
                    draw.line([(0, y), (char_w, y)], fill=int(255 * (y / fade)))
                elif y > char_h - fade:
                    draw.line([(0, y), (char_w, y)], fill=int(255 * ((char_h - y) / fade)))
            
            paste_y = (height - char_h) // 2
            base_img.paste(char_img, ((width - char_w) // 2, paste_y), mask=mask)

        # 3. VIGNETTE CHO TEXT CỰC MẠNH
        overlay = Image.new('RGBA', SHORTS_SIZE, (0,0,0,0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(height):
            if y < height * 0.25: # Đỉnh (Hook)
                alpha = int(200 * (1 - y/(height*0.25)))
                draw_ov.line([(0,y), (width,y)], fill=(0,0,0,alpha))
            elif y > height * 0.65: # Đáy (Subs)
                alpha = int(220 * ((y - height*0.65)/(height*0.35)))
                draw_ov.line([(0,y), (width,y)], fill=(0,0,0,alpha))
        
        final = Image.alpha_composite(base_img, overlay).convert("RGB")
        final.save(output_path, quality=95)
        return output_path
    except Exception as e:
        logger.error(f"❌ Shorts BG Error: {e}")
        return None

# =========================================================
# 🛠️ HÀM TẠO PHỤ ĐỀ (SUBTITLES NEON)
# =========================================================
def generate_subtitle_clips(text_content, total_duration):
    if not text_content: return []
    words = text_content.replace('\n', ' ').split()
    chunk_size = 3 # Fast-paced (3 từ/lần)
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

    time_per_chunk = total_duration / len(chunks)
    subtitle_clips = []
    
    for i, chunk in enumerate(chunks):
        try:
            txt_clip = TextClip(
                chunk.upper(), fontsize=105, font='DejaVu-Sans-Bold',
                color='#FFEA00', stroke_color='black', stroke_width=9,
                size=(1000, None), method='caption', align='center'
            ).set_start(i * time_per_chunk).set_duration(time_per_chunk).set_position(('center', 1450))
            
            # Hiệu ứng Pop-in (phóng to nhẹ khi xuất hiện)
            txt_clip = txt_clip.fx(vfx.resize, lambda t: 1 + 0.06 * (t / time_per_chunk))
            subtitle_clips.append(txt_clip)
        except: pass
    return subtitle_clips

# =========================================================
# 🎬 HÀM CHÍNH (CREATE SHORTS)
# =========================================================
def create_shorts(audio_path, text_script, episode_id, character_name, hook_title, custom_image_path=None): 
    try:
        # 1. Audio Processing
        voice = AudioFileClip(audio_path).volumex(1.6)
        duration = min(voice.duration, MAX_DURATION)
        voice = voice.subclip(0, duration)
        
        # Nhạc nền ngẫu nhiên để tránh bị quét Spam
        bg_music_path = get_path('assets', 'background_music', 'loop_1.mp3')
        if os.path.exists(bg_music_path):
            bg_music = AudioFileClip(bg_music_path).volumex(0.12)
            num_loops = math.ceil(duration / bg_music.duration)
            bg_music_looped = concatenate_audioclips([bg_music]*num_loops).subclip(0, duration)
            final_audio = CompositeAudioClip([bg_music_looped, voice])
        else: final_audio = voice

        # 2. Smart Background Selection
        hybrid_bg_path = get_path('assets', 'temp', f"{episode_id}_shorts_hybrid.jpg")
        # Ưu tiên tìm file nền Epic dọc
        base_bg_path = get_path('assets', 'images', 'bg_short_epic.png')
        if not os.path.exists(base_bg_path):
            base_bg_path = get_path('assets', 'images', f"{episode_id.split('_')[0]}_bg.png")
        if not os.path.exists(base_bg_path):
            base_bg_path = custom_image_path

        final_bg = process_hybrid_shorts_bg(custom_image_path, base_bg_path, hybrid_bg_path)
        clip = ImageClip(final_bg).set_duration(duration) if final_bg else ColorClip(SHORTS_SIZE, color=(15,15,15), duration=duration)
        
        # Zoom nhẹ toàn bộ video (Ken Burns cho Shorts)
        clip = clip.resize(lambda t: 1 + 0.05 * (t / duration)).set_position('center')

        elements = [clip]

        # 3. Hook Title (High Visibility)
        if hook_title:
            try:
                hook_clip = TextClip(
                    hook_title.upper(), fontsize=95, color='white', font='DejaVu-Sans-Bold',
                    method='caption', size=(950, None), stroke_color='black', stroke_width=10, align='center'
                ).set_pos(('center', 220)).set_duration(duration)
                elements.append(hook_clip)
            except: pass

        # 4. Subtitles (Neon Pop)
        if text_script:
            subs = generate_subtitle_clips(text_script, duration)
            elements.extend(subs)

        # 5. Render
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        logger.info(f"🚀 Rendering Cinematic Short: {episode_id}")
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        return out_path

    except Exception as e:
        logger.error(f"❌ Shorts Error: {e}", exc_info=True)
        return None
