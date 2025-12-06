# ===scripts/create_video.py===
import logging
import os
import numpy as np
from pydub import AudioSegment
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

# --- [FIX QUAN TRỌNG] VÁ LỖI PILLOW 10+ CHO MOVIEPY ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ------------------------------------------------------

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, VideoClip, TextClip
)
from utils import get_path

logger = logging.getLogger(__name__)

# --- ĐỘ PHÂN GIẢI CHUNG (720P) ---
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
# -----------------------------------

# ============================================================
# 🎨 HÀM XỬ LÝ BACKGROUND HYBRID (16:9)
# ============================================================
def process_hybrid_background(char_path, base_bg_path, output_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Ghép ảnh: Nền phong cảnh cố định (dưới) + Nhân vật DALL-E (trên, lệch phải).
    """
    try:
        # 1. LOAD & RESIZE BASE BACKGROUND (Lớp nền)
        if base_bg_path and os.path.exists(base_bg_path):
            base_img = Image.open(base_bg_path).convert("RGBA")
        else:
            # Fallback nếu thiếu ảnh nền
            base_img = Image.new("RGBA", (width, height), (20, 20, 20, 255))

        # Resize Aspect Fill (Lấp đầy màn hình)
        bg_ratio = base_img.width / base_img.height
        target_ratio = width / height
        
        if bg_ratio > target_ratio:
            new_h = height
            new_w = int(new_h * bg_ratio)
        else:
            new_w = width
            new_h = int(new_w / bg_ratio)
            
        base_img = base_img.resize((new_w, new_h), Image.LANCZOS)
        
        # Center Crop
        left = (new_w - width) // 2
        top = (new_h - height) // 2
        base_img = base_img.crop((left, top, left + width, top + height))
        
        # Làm tối nền gốc một chút (30%) để nhân vật nổi hơn
        enhancer = ImageEnhance.Brightness(base_img)
        base_img = enhancer.enhance(0.7) 

        # 2. XỬ LÝ NHÂN VẬT (Lớp trên)
        if char_path and os.path.exists(char_path):
            char_img = Image.open(char_path).convert("RGBA")
            
            # Tính toán kích thước nhân vật (Cao bằng màn hình)
            char_h = height
            char_w = int(char_img.width * (char_h / char_img.height))
            char_img = char_img.resize((char_w, char_h), Image.LANCZOS)
            
            # Tạo Mask hòa trộn (Gradient từ trong suốt -> hiện rõ)
            # Giúp cạnh trái của nhân vật hòa vào nền
            mask = Image.new("L", (char_w, char_h), 0)
            draw_mask = ImageDraw.Draw(mask)
            
            for x in range(char_w):
                pct = x / char_w
                # 20% đầu trong suốt, sau đó hiện dần
                if pct < 0.2:
                    alpha = 0
                elif pct > 0.6:
                    alpha = 255
                else:
                    alpha = int(255 * ((pct - 0.2) / 0.4))
                
                draw_mask.line([(x, 0), (x, char_h)], fill=alpha)
            
            # Dán nhân vật sang bên phải màn hình
            paste_x = width - char_w + 50 # Đẩy sang phải một chút
            if paste_x < 0: paste_x = 0
            
            base_img.paste(char_img, (paste_x, 0), mask=mask)

        # 3. TẠO VIGNETTE ĐEN BÊN TRÁI (Để viết Title)
        gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw_grad = ImageDraw.Draw(gradient)
        
        # Phủ tối 60% màn hình từ trái sang
        for x in range(int(width * 0.6)): 
            # Giảm dần độ đậm từ 200 về 0
            alpha = int(200 * (1 - (x / (width * 0.6))))
            draw_grad.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))
            
        final_img = Image.alpha_composite(base_img, gradient)
        
        # Lưu ảnh
        final_img = final_img.convert("RGB")
        final_img.save(output_path, quality=95)
        logger.info(f"🎨 Đã tạo Hybrid Background: {output_path}")
        return output_path
            
    except Exception as e:
        logger.error(f"❌ Error Hybrid BG: {e}")
        return None

# ============================================================
# 🌟 CIRCULAR WAVEFORM
# ============================================================
def make_circular_waveform(audio_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    calc_w, calc_h = 640, 360 
    fps = 20 
    audio = AudioSegment.from_file(audio_path)
    raw_samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    if audio.channels == 2:
        raw_samples = raw_samples.reshape((-1, 2)).mean(axis=1)
    
    num_frames = int(duration * fps) + 1
    envelope = []
    step = len(raw_samples) // num_frames
    if step == 0: step = 1
    for i in range(0, len(raw_samples), step):
        chunk = raw_samples[i:i+step]
        if len(chunk) > 0: envelope.append(np.mean(np.abs(chunk)))
        if len(envelope) >= num_frames: break
            
    envelope = np.array(envelope)
    max_val = np.max(envelope) if len(envelope) > 0 else 1
    if max_val > 0: envelope = envelope / max_val 

    waves = 15 
    center = (calc_w // 2, calc_h // 2)
    yy, xx = np.ogrid[:calc_h, :calc_w]
    dist_sq = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
    dist_matrix = np.sqrt(dist_sq)

    def make_mask_frame(t):
        frame_idx = int(t * fps)
        frame_idx = min(frame_idx, len(envelope) - 1)
        amp = envelope[frame_idx]
        mask_frame = np.zeros((calc_h, calc_w), dtype=np.float32)
        base_radius = 25 + amp * 20 
        for i in range(waves):
            radius = base_radius + i * 6
            opacity = max(0.0, 1.0 - i * 0.06)
            if opacity <= 0: continue
            ring_mask = (dist_matrix >= radius - 0.3) & (dist_matrix <= radius + 0.3)
            mask_frame[ring_mask] = opacity
        return mask_frame

    mask_clip_low_res = VideoClip(make_mask_frame, duration=duration, ismask=True).set_fps(fps)
    mask_clip_high_res = mask_clip_low_res.resize((width, height))
    color_clip = ColorClip(size=(width, height), color=(255, 215, 0), duration=duration) 
    return color_clip.set_mask(mask_clip_high_res)

def make_glow_layer(duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    low_w, low_h = 320, 180
    y = np.linspace(0, low_h - 1, low_h)
    x = np.linspace(0, low_w - 1, low_w)
    xx, yy = np.meshgrid(x, y)
    lcx, lcy = low_w // 2, int(low_h * 0.45)
    radius = int(min(low_w, low_h) * 0.45)
    dist = np.sqrt((xx - lcx)**2 + (yy - lcy)**2)
    intensity = np.clip(255 - (dist / radius) * 255, 0, 255)
    glow_low = np.zeros((low_h, low_w, 3), dtype=np.uint8)
    glow_low[:, :, 0] = (intensity * 0.3).astype(np.uint8)
    glow_low[:, :, 1] = (intensity * 0.2).astype(np.uint8)
    glow_low[:, :, 2] = 0                                 
    return ImageClip(glow_low).resize((width, height)).set_duration(duration).set_opacity(0.3)


# ============================================================
# 🎬 HÀM CHÍNH (CREATE VIDEO)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, base_bg_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        # 1. Setup Audio
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"🎧 Audio duration = {duration:.2f}s") 

        # 2. Setup Background (Hybrid)
        clip = None
        # Đường dẫn file ảnh tạm sau khi ghép
        hybrid_bg_path = get_path('assets', 'temp', f"{episode_id}_hybrid_bg.jpg")
        os.makedirs(os.path.dirname(hybrid_bg_path), exist_ok=True)

        if custom_image_path:
            # Gọi hàm ghép ảnh
            final_bg = process_hybrid_background(custom_image_path, base_bg_path, hybrid_bg_path)
            if final_bg:
                clip = ImageClip(final_bg).set_duration(duration)

        # Fallback (Nếu không có ảnh nhân vật thì dùng ảnh nền gốc)
        if clip is None:
             if base_bg_path and os.path.exists(base_bg_path):
                 clip = ImageClip(base_bg_path).set_duration(duration).resize((OUTPUT_WIDTH, OUTPUT_HEIGHT))
             else:
                 clip = ColorClip(size=(OUTPUT_WIDTH, OUTPUT_HEIGHT), color=(15,15,15), duration=duration)

        # 3. Waveform & Glow
        glow = make_glow_layer(duration)
        waveform = make_circular_waveform(audio_path, duration)
        waveform = waveform.set_position("center")

        # 4. Title Text (Góc trái trên)
        title_layer = None
        if title_text:
            try:
                title_layer = TextClip(
                    title_text.upper(),
                    fontsize=55,
                    font='DejaVu-Sans-Bold', 
                    color='#FFD700',      
                    stroke_color='black', 
                    stroke_width=3,
                    method='caption',
                    align='West',         
                    size=(800, None)      
                ).set_position((50, 50)).set_duration(duration)
            except Exception as e:
                logger.warning(f"⚠️ Title Error: {e}")

        # 5. Channel Logo
        logo_path = get_path('assets', 'images', 'channel_logo.png')
        logo_layer = None
        if os.path.exists(logo_path):
             logo_layer = ImageClip(logo_path).set_duration(duration).resize(height=100).set_position(("right", "top")).margin(right=20, top=20, opacity=0)

        # 6. Composite
        layers = [clip, glow, waveform]
        if title_layer: layers.append(title_layer)
        if logo_layer: layers.append(logo_layer)

        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        # 7. Render
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        logger.info("🚀 Starting Render Long Video...")
        
        final.write_videofile(
            output,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",      
            threads=4,
            ffmpeg_params=["-crf", "28"], 
            logger='bar' 
        )
        return output

    except Exception as e:
        logger.error(f"❌ VIDEO ERROR: {e}", exc_info=True)
        return False
