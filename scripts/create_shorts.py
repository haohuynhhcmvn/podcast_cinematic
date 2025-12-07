# scripts/create_shorts.py

import logging
import os
import math 
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
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
# 🎨 HÀM XỬ LÝ BACKGROUND HYBRID (9:16) - CẬP NHẬT
# =========================================================
def process_hybrid_shorts_bg(char_path, base_bg_path, output_path):
    """
    Ghép ảnh: Nền phong cảnh dọc (dưới) + Nhân vật DALL-E (đáy).
    """
    try:
        width, height = SHORTS_SIZE
        
        # 1. LOAD & RESIZE BASE BG (Ảnh nền dọc)
        if base_bg_path and os.path.exists(base_bg_path):
            base_img = Image.open(base_bg_path).convert("RGBA")
        else:
            base_img = Image.new("RGBA", SHORTS_SIZE, (20,20,20,255))
            
        # Resize Aspect Fill
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
        
        # Làm tối nền để nổi chữ vàng (50%)
        enhancer = ImageEnhance.Brightness(base_img)
        base_img = enhancer.enhance(0.5) 

        # 2. XỬ LÝ NHÂN VẬT (Nằm dưới cùng) - CẬP NHẬT LOGIC
        if char_path and os.path.exists(char_path):
            char_img = Image.open(char_path).convert("RGBA")
            
            # Resize nhân vật sao cho chiều rộng bằng chiều rộng Shorts
            # Điều này giúp nhân vật chiếm trọn phần dưới, rõ ràng hơn
            char_w = width
            char_h = int(char_img.height * (char_w / char_img.width))
            char_img = char_img.resize((char_w, char_h), Image.LANCZOS)
            
            # Mask mờ dần từ trên xuống (Để cạnh trên của nhân vật hòa vào nền)
            mask = Image.new("L", (char_w, char_h), 0)
            draw = ImageDraw.Draw(mask)
            for y in range(char_h):
                pct = y / char_h
                # 20% trên cùng trong suốt hoàn toàn để hòa trộn tốt hơn
                if pct < 0.2: alpha = 0
                # Sau đó hiện dần lên
                else: alpha = int(255 * ((pct - 0.2) / 0.3)) # Gradient nhanh hơn một chút
                if alpha > 255: alpha = 255
                draw.line([(0, y), (char_w, y)], fill=alpha)
            
            # Dán vào đáy ảnh. 
            # Paste Y: Đặt nhân vật sát đáy hoặc hơi thấp xuống một chút nếu ảnh quá cao
            # Logic: Nếu ảnh nhân vật cao hơn 1/2 chiều cao Shorts, cho nó lún xuống một chút
            if char_h > height * 0.6:
                 paste_y = height - char_h + int(char_h * 0.1) # Lún xuống 10% chiều cao nhân vật
            else:
                 paste_y = height - char_h

            # Đảm bảo không bị khoảng trống ở đáy
            if paste_y < 0: paste_y = height - char_h # Fallback nếu tính toán sai
            
            base_img.paste(char_img, (0, paste_y), mask=mask)

        # 3. TẠO VIGNETTE (Tối Đỉnh và Đáy cho Text)
        overlay = Image.new('RGBA', SHORTS_SIZE, (0,0,0,0))
        draw_ov = ImageDraw.Draw(overlay)
        
        for y in range(height):
            # Tối ở Đỉnh (20% trên cùng) - Cho Hook Title
            if y < height * 0.2: 
                alpha = int(180 * (1 - y/(height*0.2)))
                draw_ov.line([(0,y), (width,y)], fill=(0,0,0,alpha))
            # Tối ở Đáy (30% dưới cùng) - Cho Subtitles
            elif y > height * 0.7: 
                alpha = int(180 * ((y - height*0.7)/(height*0.3)))
                draw_ov.line([(0,y), (width,y)], fill=(0,0,0,alpha))
        
        final = Image.alpha_composite(base_img, overlay)
        final = final.convert("RGB")
        final.save(output_path, quality=90)
        return output_path

    except Exception as e:
        logger.error(f"❌ Shorts BG Error: {e}")
        return None

# =========================================================
# 🛠️ HÀM TẠO PHỤ ĐỀ (SUBTITLES) - CẦN THIẾT
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
# 🎬 HÀM CHÍNH (CREATE SHORTS)
# =========================================================
def create_shorts(audio_path, hook_title, episode_id, character_name, script_path, custom_image_path=None, base_bg_path=None): 
    try:
        # 1. Load Voice
        if not os.path.exists(audio_path): return None
        voice = AudioFileClip(audio_path).volumex(1.5) 
        duration = min(voice.duration, MAX_DURATION) 
        voice = voice.subclip(0, duration) 
        
        # 2. Audio Mix (Loop Bg Music)
        bg_music_path = get_path('assets', 'background_music', 'loop_1.mp3')
        if os.path.exists(bg_music_path):
            bg_music = AudioFileClip(bg_music_path).volumex(0.1) 
            num_loops = math.ceil(duration / bg_music.duration)
            bg_music_looped = concatenate_audioclips([bg_music]*num_loops).subclip(0, duration)
            final_audio = CompositeAudioClip([bg_music_looped, voice])
        else:
            final_audio = voice

        # 3. Hybrid Background
        clip = None
        hybrid_bg_path = get_path('assets', 'temp', f"{episode_id}_shorts_hybrid.jpg")
        os.makedirs(os.path.dirname(hybrid_bg_path), exist_ok=True)
        
        # Luôn ưu tiên tạo nền Hybrid nếu có ảnh nhân vật
        if custom_image_path:
            # Ghép nền có sẵn + Nhân vật DALL-E
            final_bg = process_hybrid_shorts_bg(custom_image_path, base_bg_path, hybrid_bg_path)
            if final_bg:
                clip = ImageClip(final_bg).set_duration(duration)

        # Fallback - Chỉ dùng khi không tạo được hybrid bg
        if clip is None:
             if base_bg_path and os.path.exists(base_bg_path):
                 # Resize ảnh nền có sẵn cho Shorts
                 clip = ImageClip(base_bg_path).set_duration(duration)
                 # Cần resize về chuẩn 1080x1920 nếu chưa đúng
                 if clip.size != SHORTS_SIZE:
                     # Resize giữ tỷ lệ để phủ kín chiều cao hoặc chiều rộng (Aspect Fill)
                     # Logic resize của MoviePy: resize(height=...) sẽ tự tính width theo tỷ lệ
                     clip = clip.resize(height=SHORTS_HEIGHT)
                     # Nếu width vẫn nhỏ hơn SHORTS_WIDTH thì resize theo width
                     if clip.w < SHORTS_WIDTH:
                         clip = clip.resize(width=SHORTS_WIDTH)
                     
                     # Crop giữa
                     clip = clip.crop(x1=clip.w/2 - SHORTS_WIDTH/2, width=SHORTS_WIDTH, 
                                      y1=clip.h/2 - SHORTS_HEIGHT/2, height=SHORTS_HEIGHT)
             else:
                 clip = ColorClip(SHORTS_SIZE, color=(20,20,20), duration=duration)

        elements = [clip]

        # 4. Hook Title (Trên cùng)
        if hook_title:
            try:
                hook_clip = TextClip(
                    hook_title.upper(), fontsize=90, color='white', font='DejaVu-Sans-Bold', 
                    method='caption', size=(1000, None), stroke_color='black', stroke_width=8, align='center'
                ).set_pos(('center', 200)).set_duration(duration)
                elements.append(hook_clip)
            except Exception: pass

        # 5. Subtitles (Dưới cùng)
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
        
        logger.info("🚀 Rendering Shorts...")
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        return out_path

    except Exception as e:
        logger.error(f"❌ Shorts Error: {e}", exc_info=True)
        return None
