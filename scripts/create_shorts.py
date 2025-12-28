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
    TextClip, CompositeVideoClip
)
from utils import get_path

logger = logging.getLogger(__name__)

SHORTS_SIZE = (1080, 1920)

def create_shorts(audio_path, hook_title, episode_id, script_path, short_index=1):
    """
    audio_path: file mp3 của short
    hook_title: Tên nhân vật làm tiêu đề
    episode_id: ID để định danh
    script_path: file txt chứa nội dung để làm sub (QUAN TRỌNG)
    short_index: Số thứ tự 1-5
    """
    try:
        if not os.path.exists(audio_path):
            return None

        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # 1. Tạo nền (Dùng màu tối đơn giản nếu không có ảnh)
        clip = ColorClip(SHORTS_SIZE, color=(20, 20, 20), duration=duration)

        elements = [clip]

        # 2. Hook Title (Trên cùng)
        if hook_title:
            try:
                hook_clip = TextClip(
                    hook_title.upper(), fontsize=70, color='white', font='DejaVu-Sans-Bold',
                    method='caption', size=(900, None), stroke_color='black', stroke_width=4
                ).set_pos(('center', 300)).set_duration(duration)
                elements.append(hook_clip)
            except Exception as e:
                logger.warning(f"Không tạo được Hook Title: {e}")

        # 3. Subtitles (Dưới cùng) - Sử dụng script_path được truyền vào
        if script_path and os.path.exists(script_path):
            try:
                with open(script_path, "r", encoding="utf-8") as f:
                    full_script = f.read()
                # Giả định hàm generate_subtitle_clips đã được định nghĩa trong file của bạn
                from create_shorts import generate_subtitle_clips
                subs = generate_subtitle_clips(full_script, duration)
                if subs: elements.extend(subs)
            except Exception as e:
                logger.warning(f"Không tạo được Subtitles: {e}")

        # 4. Render và Lưu với index riêng biệt
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(audio)
        
        # ĐẶT TÊN FILE THEO INDEX ĐỂ KHÔNG GHI ĐÈ
        out_path = get_path('outputs', 'shorts', f"{episode_id}_short_{short_index}.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        logger.info(f"🚀 Rendering Short Part {short_index}...")
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac')
        
        return out_path
    except Exception as e:
        logger.error(f"❌ Lỗi trong create_shorts: {e}")
        return None
