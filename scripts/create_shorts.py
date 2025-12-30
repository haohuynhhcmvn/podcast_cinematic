# === scripts/create_shorts.py ===
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
# ------------------------------------------------------

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
# 🎨 HÀM XỬ LÝ BACKGROUND HYBRID (9:16) - NHÂN VẬT Ở GIỮA
# (GIỮ NGUYÊN CODE CŨ CỦA BẠN VÌ NÓ ĐẸP)
# =========================================================
def process_hybrid_shorts_bg(char_path, base_bg_path, output_path):
    """
    Ghép ảnh: Nền phong cảnh dọc + Nhân vật DALL-E (Ở GIỮA).
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
        
        # Làm tối nền mạnh hơn để nhân vật nổi bật (40% độ sáng)
        enhancer = ImageEnhance.Brightness(base_img)
        base_img = enhancer.enhance(0.4) 

        # 2. XỬ LÝ NHÂN VẬT (Đặt ở Giữa)
        if char_path and os.path.exists(char_path):
            char_img = Image.open(char_path).convert("RGBA")
            
            # Resize nhân vật: Chiều rộng bằng 90% chiều rộng Shorts (để có lề)
            target_char_w = int(width * 0.9)
            char_w = target_char_w
            char_h = int(char_img.height * (char_w / char_img.width))
            char_img = char_img.resize((char_w, char_h), Image.LANCZOS)
            
            # Tạo Mask mờ 2 đầu (Trên và Dưới) để hòa vào nền
            mask = Image.new("L", (char_w, char_h), 255) # Mặc định là hiện rõ (255)
            draw = ImageDraw.Draw(mask)
            fade_height = int(char_h * 0.2) # Vùng mờ là 20% chiều cao ở mỗi đầu

            for y in range(char_h):
                # Mờ phần trên
                if y < fade_height:
                    alpha = int(255 * (y / fade_height))
                    draw.line([(0, y), (char_w, y)], fill=alpha)
                # Mờ phần dưới
                elif y > char_h - fade_height:
                    alpha = int(255 * ((char_h - y) / fade_height))
                    draw.line([(0, y), (char_w, y)], fill=alpha)
            
            # Tính vị trí dán vào GIỮA khung hình
            paste_x = (width - char_w) // 2
            paste_y = (height - char_h) // 2
            
            # Dán nhân vật vào
            base_img.paste(char_img, (paste_x, paste_y), mask=mask)

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
# 🛠️ HÀM TẠO PHỤ ĐỀ (SUBTITLES)
# =========================================================
def generate_subtitle_clips(text_content, total_duration, fontsize=85):
    if not text_content: return []
    # Xử lý text từ string trực tiếp thay vì đọc file
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
        try:
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
        except Exception: pass

    return subtitle_clips

# =========================================================
# 🎬 HÀM CHÍNH (CREATE SHORTS) - LOGIC MỚI
# =========================================================
def create_shorts(audio_path, text_script, episode_id, character_name, hook_title, custom_image_path=None): 
    # [THAY ĐỔI]: Tham số thứ 2 là text_script (string) thay vì script_path (file) để khớp Glue Pipeline
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
        
        # [THAY ĐỔI]: Tự động lấy ảnh DALL-E làm Base BG nếu không có BG riêng
        # Điều này đảm bảo code cũ chạy được mà không cần tìm file base_bg_path thủ công
        base_bg_path = get_path('assets', 'images', f"{episode_id.split('_')[0]}_bg.png")
        if not os.path.exists(base_bg_path) and custom_image_path:
            base_bg_path = custom_image_path

        # Tạo nền Hybrid dùng hàm cũ của bạn
        if custom_image_path:
            final_bg = process_hybrid_shorts_bg(custom_image_path, base_bg_path, hybrid_bg_path)
            if final_bg:
                clip = ImageClip(final_bg).set_duration(duration)

        # Fallback
        if clip is None:
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
        if text_script:
            # [THAY ĐỔI]: Truyền text trực tiếp vào hàm
            subs = generate_subtitle_clips(text_script, duration)
            if subs: elements.extend(subs)

        # 6. Render
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        logger.info("🚀 Rendering Shorts (Old Style)...")
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        return out_path

    except Exception as e:
        logger.error(f"❌ Shorts Error: {e}", exc_info=True)
        return None
