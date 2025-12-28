# scripts/create_shorts.py
import logging
import os
import math 
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import PIL.Image

# --- [FIX QUAN TRỌNG] VÁ LỖI PILLOW/MOVIEPY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling') and hasattr(PIL.Image.Resampling, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    elif hasattr(PIL.Image, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip, 
    TextClip, CompositeVideoClip, CompositeAudioClip, concatenate_audioclips
)
from utils import get_path

logger = logging.getLogger(__name__)

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
SHORTS_SIZE = (SHORTS_WIDTH, SHORTS_HEIGHT)
MAX_DURATION = 60 

# =========================================================
# 🎨 HÀM XỬ LÝ BACKGROUND HYBRID (9:16)
# =========================================================
def process_hybrid_shorts_bg(char_path, base_bg_path, output_path):
    try:
        width, height = SHORTS_SIZE
        if base_bg_path and os.path.exists(base_bg_path):
            base_img = Image.open(base_bg_path).convert("RGBA")
        else:
            base_img = Image.new("RGBA", SHORTS_SIZE, (20,20,20,255))
            
        # Aspect Fill Resize
        ratio = width / height
        img_ratio = base_img.width / base_img.height
        if img_ratio > ratio:
            new_h = height
            new_w = int(new_h * img_ratio)
        else:
            new_w = width
            new_h = int(new_w / img_ratio)
            
        base_img = base_img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - width) // 2
        base_img = base_img.crop((left, 0, left + width, height))
        base_img = ImageEnhance.Brightness(base_img).enhance(0.4) 

        # Xử lý nhân vật (Center)
        if char_path and os.path.exists(char_path):
            char_img = Image.open(char_path).convert("RGBA")
            target_char_w = int(width * 0.9)
            char_w = target_char_w
            char_h = int(char_img.height * (char_w / char_img.width))
            char_img = char_img.resize((char_w, char_h), Image.LANCZOS)
            
            mask = Image.new("L", (char_w, char_h), 255)
            draw = ImageDraw.Draw(mask)
            fade_h = int(char_h * 0.2)
            for y in range(char_h):
                if y < fade_h: draw.line([(0, y), (char_w, y)], fill=int(255 * (y / fade_h)))
                elif y > char_h - fade_h: draw.line([(0, y), (char_w, y)], fill=int(255 * ((char_h - y) / fade_h)))
            
            base_img.paste(char_img, ((width - char_w) // 2, (height - char_h) // 2), mask=mask)

        # Vignette cho Text
        overlay = Image.new('RGBA', SHORTS_SIZE, (0,0,0,0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(height):
            if y < height * 0.2: draw_ov.line([(0,y), (width,y)], fill=(0,0,0,int(180 * (1 - y/(height*0.2)))))
            elif y > height * 0.7: draw_ov.line([(0,y), (width,y)], fill=(0,0,0,int(180 * ((y - height*0.7)/(height*0.3)))))
        
        final = Image.alpha_composite(base_img, overlay).convert("RGB")
        final.save(output_path, quality=90)
        return output_path
    except Exception as e:
        logger.error(f"❌ Shorts BG Error: {e}")
        return None

# =========================================================
# 🛠️ HÀM TẠO PHỤ ĐỀ (SUBTITLES)
# =========================================================
def generate_subtitle_clips(text_content, total_duration):
    if not text_content: return []
    words = text_content.replace('\n', ' ').split()
    chunk_size = 4
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    
    time_per_chunk = total_duration / len(chunks)
    clips = []
    for i, chunk in enumerate(chunks):
        try:
            txt = TextClip(chunk.upper(), fontsize=85, font='DejaVu-Sans-Bold', color='#FFD700',
                           stroke_color='black', stroke_width=6, size=(950, None), method='caption').set_start(i * time_per_chunk).set_duration(time_per_chunk).set_position(('center', 1400))
            clips.append(txt)
        except: pass
    return clips

# =========================================================
# 🎬 HÀM CHÍNH: CREATE SHORTS (TƯƠNG THÍCH VỚI MULTI-SHORTS)
# =========================================================
def create_shorts(episode_id, custom_image_path, script_path, audio_path, hook_title=None, base_bg_path=None): 
    """
    Sắp xếp lại tham số để khớp với glue_pipeline: (id, img, script, audio, title)
    """
    try:
        logger.info(f"🎞️ Đang render Shorts cho ID: {episode_id}")
        
        # 1. Audio
        voice = AudioFileClip(audio_path).volumex(1.5)
        duration = min(voice.duration, MAX_DURATION)
        voice = voice.subclip(0, duration)
        
        bg_m = get_path('assets', 'background_music', 'loop_1.mp3')
        if os.path.exists(bg_m):
            music = AudioFileClip(bg_m).volumex(0.1)
            music = concatenate_audioclips([music] * math.ceil(duration/music.duration)).subclip(0, duration)
            final_audio = CompositeAudioClip([music, voice])
        else:
            final_audio = voice

        # 2. Background
        hybrid_path = get_path('assets', 'temp', f"{episode_id}_hybrid.jpg")
        bg_file = process_hybrid_shorts_bg(custom_image_path, base_bg_path, hybrid_path)
        bg_clip = ImageClip(bg_file).set_duration(duration) if bg_file else ColorClip(SHORTS_SIZE, color=(20,20,20)).set_duration(duration)

        elements = [bg_clip]

        # 3. Hook Title
        if hook_title:
            try:
                h_clip = TextClip(hook_title.upper(), fontsize=90, color='white', font='DejaVu-Sans-Bold',
                                  method='caption', size=(1000, None), stroke_color='black', stroke_width=8).set_pos(('center', 200)).set_duration(duration)
                elements.append(h_clip)
            except: pass

        # 4. Subtitles
        if os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                subs = generate_subtitle_clips(f.read(), duration)
                elements.extend(subs)

        # 5. Render
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        final_video = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        final_video.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        
        # Đóng các clip để giải phóng RAM
        final_video.close()
        voice.close()
        return out_path

    except Exception as e:
        logger.error(f"❌ Shorts Error {episode_id}: {e}")
        return None
