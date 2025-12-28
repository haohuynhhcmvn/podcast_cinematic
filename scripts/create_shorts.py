# scripts/create_shorts.py
import logging
import os
import math 
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import PIL.Image

# --- [FIX QUAN TRỌNG] VÁ LỖI PILLOW/MOVIEPY ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', getattr(PIL.Image, 'Resampling', None))
# ---------------------------------------------

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip, 
    TextClip, CompositeVideoClip, CompositeAudioClip, 
    concatenate_audioclips, vfx  # <--- ĐÃ THÊM vfx VÀO ĐÂY ĐỂ FIX LỖI
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
            
        # Aspect Fill
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

        # Nhân vật ở giữa
        if char_path and os.path.exists(char_path):
            char_img = Image.open(char_path).convert("RGBA")
            target_char_w = int(width * 0.9)
            char_h = int(char_img.height * (target_char_w / char_img.width))
            char_img = char_img.resize((target_char_w, char_h), Image.LANCZOS)
            
            # Mask mờ biên
            mask = Image.new("L", (target_char_w, char_h), 255)
            draw = ImageDraw.Draw(mask)
            fade = int(char_h * 0.2)
            for y in range(char_h):
                if y < fade: draw.line([(0, y), (target_char_w, y)], fill=int(255 * (y / fade)))
                elif y > char_h - fade: draw.line([(0, y), (target_char_w, y)], fill=int(255 * ((char_h - y) / fade)))
            
            base_img.paste(char_img, ((width - target_char_w) // 2, (height - char_h) // 2), mask=mask)

        # Vignette cho Text
        overlay = Image.new('RGBA', SHORTS_SIZE, (0,0,0,0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(height):
            if y < height * 0.2: 
                draw_ov.line([(0,y), (width,y)], fill=(0,0,0,int(180 * (1 - y/(height*0.2)))))
            elif y > height * 0.7: 
                draw_ov.line([(0,y), (width,y)], fill=(0,0,0,int(180 * ((y - height*0.7)/(height*0.3)))))
        
        final = Image.alpha_composite(base_img, overlay).convert("RGB")
        final.save(output_path, quality=85)
        return output_path
    except Exception as e:
        logger.error(f"❌ Shorts BG Error: {e}")
        return None

# =========================================================
# 🛠️ HÀM TẠO PHỤ ĐỀ (SUBTITLES)
# =========================================================
def generate_subtitle_clips(text_content, total_duration, fontsize=85):
    if not text_content: return []
    words = text_content.replace('\n', ' ').split()
    if not words: return []

    chunk_size = 4
    chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    time_per_chunk = total_duration / len(chunks)
    subtitle_clips = []
    
    for i, chunk in enumerate(chunks):
        try:
            txt_clip = TextClip(
                chunk.upper(), fontsize=fontsize, font='DejaVu-Sans-Bold',
                color='#FFD700', stroke_color='black', stroke_width=4,
                size=(950, None), method='caption', align='center'
            ).set_position(('center', 1400)).set_start(i * time_per_chunk).set_duration(time_per_chunk)
            subtitle_clips.append(txt_clip)
        except: continue
    return subtitle_clips

# =========================================================
# 🎬 HÀM CHÍNH (CREATE SHORTS)
# =========================================================
def create_shorts(audio_path, hook_title, episode_id, character_name, script_path, custom_image_path=None, base_bg_path=None): 
    try:
        if not os.path.exists(audio_path): return None
        voice = AudioFileClip(audio_path).volumex(1.5) 
        duration = min(voice.duration, MAX_DURATION) 
        voice = voice.subclip(0, duration) 
        
        # Audio Mix với hiệu ứng Loop Music
        bg_music_path = get_path('assets', 'background_music', 'loop_1.mp3')
        if os.path.exists(bg_music_path):
            bg_music = AudioFileClip(bg_music_path).volumex(0.1) 
            # Sử dụng vfx.loop (Đã fix lỗi import)
            bg_music_looped = bg_music.fx(vfx.loop, duration=duration)
            final_audio = CompositeAudioClip([bg_music_looped, voice])
        else:
            final_audio = voice

        # Background xử lý
        hybrid_bg_path = get_path('assets', 'temp', f"{episode_id}_shorts_hybrid.jpg")
        final_bg = process_hybrid_shorts_bg(custom_image_path, base_bg_path, hybrid_bg_path)
        
        bg_to_use = final_bg if final_bg else base_bg_path
        if bg_to_use and os.path.exists(bg_to_use):
            clip = ImageClip(bg_to_use).set_duration(duration)
        else:
            clip = ColorClip(SHORTS_SIZE, color=(20,20,20), duration=duration)

        if clip.size != SHORTS_SIZE: 
            clip = clip.resize(height=SHORTS_HEIGHT).crop(x_center=clip.w/2, width=SHORTS_WIDTH)

        elements = [clip]

        # Hook Title
        if hook_title:
            try:
                hook = TextClip(
                    hook_title.upper(), fontsize=90, color='white', font='DejaVu-Sans-Bold', 
                    method='caption', size=(1000, None), stroke_color='black', stroke_width=6, align='center'
                ).set_pos(('center', 200)).set_duration(duration)
                elements.append(hook)
            except: pass

        # Subtitles
        if script_path:
            with open(script_path, "r", encoding="utf-8") as f:
                subs = generate_subtitle_clips(f.read(), duration)
                elements.extend(subs)

        # Render Final
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        
        logger.info(f"🚀 Rendering Shorts (FPS=12, CRF=32)...")
        final.write_videofile(
            out_path, 
            fps=12, 
            codec='libx264', 
            audio_codec='aac', 
            preset='ultrafast', 
            threads=4, 
            ffmpeg_params=["-crf", "32"],
            logger=None
        )
        
        # Cleanup giải phóng RAM
        final.close()
        voice.close()
        if os.path.exists(bg_music_path): bg_music.close()
        
        return out_path
    except Exception as e:
        logger.error(f"❌ Shorts Error: {e}")
        return None
