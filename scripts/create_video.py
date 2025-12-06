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
# 🌑 HÀM XỬ LÝ BACKGROUND: CINEMATIC GRADIENT (TRÁI -> PHẢI)
# ============================================================
def process_background_image(input_path, output_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Xử lý ảnh AI: Phủ Gradient tối bên trái (cho Title) -> Trong suốt bên phải (cho Nhân vật).
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGBA")
            
            # 1. Resize & Center Crop (Lấp đầy màn hình 16:9)
            target_ratio = width / height
            img_ratio = img.width / img.height
            
            if img_ratio > target_ratio:
                new_height = height
                new_width = int(new_height * img_ratio)
            else:
                new_width = width
                new_height = int(new_width / img_ratio)
                
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Crop chính giữa
            left = (new_width - width) // 2
            top = (new_height - height) // 2
            img_crop = img.crop((left, top, left + width, top + height))
            
            # 2. TẠO LỚP GRADIENT (Masking)
            gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(gradient)
            
            # Vẽ từng đường dọc từ trái sang phải
            for x in range(width):
                # Logic: 35% đầu rất tối (để đọc chữ), sau đó nhạt dần
                pct = x / width 
                
                if pct < 0.35:
                    alpha = 200 # Tối đậm (khoảng 80%)
                elif pct < 0.75:
                    # Fade out từ từ
                    fade_ratio = (pct - 0.35) / (0.40) 
                    alpha = int(200 * (1 - fade_ratio))
                else:
                    alpha = 0 # Trong suốt hoàn toàn
                
                draw.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))

            # 3. Hòa trộn
            final_img = Image.alpha_composite(img_crop, gradient)
            
            # 4. Tăng nhẹ độ bão hòa màu (Saturation) cho đẹp
            final_img = final_img.convert("RGB")
            enhancer = ImageEnhance.Color(final_img)
            final_img = enhancer.enhance(1.1)
            
            final_img.save(output_path, quality=95)
            logger.info(f"🌑 Đã tạo nền Cinematic Gradient: {output_path}")
            return output_path
            
    except Exception as e:
        logger.error(f"❌ Error processing background image: {e}")
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
        if len(chunk) > 0:
            val = np.mean(np.abs(chunk))
            envelope.append(val)
        if len(envelope) >= num_frames:
            break
            
    envelope = np.array(envelope)
    max_val = np.max(envelope) if len(envelope) > 0 else 1
    if max_val > 0:
        envelope = envelope / max_val 

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
            ring_mask = (dist_matrix >= radius - 1.5) & (dist_matrix <= radius + 1.5)
            mask_frame[ring_mask] = opacity
        return mask_frame

    mask_clip_low_res = VideoClip(make_mask_frame, duration=duration, ismask=True).set_fps(fps)
    mask_clip_high_res = mask_clip_low_res.resize((width, height))
    color_clip = ColorClip(size=(width, height), color=(255, 215, 0), duration=duration) 
    return color_clip.set_mask(mask_clip_high_res)


# ============================================================
# 🌟 GLOW LAYER
# ============================================================
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
# 🎬 HÀM TẠO VIDEO CHÍNH (ĐÃ BỔ SUNG title_text)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        # Setup Duration
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"🎧 Audio duration = {duration:.2f}s") 

        # --- 1. LAYER NỀN (BACKGROUND) ---
        bg_video_path = get_path('assets', 'video', 'podcast_loop_bg_long.mp4')
        bg_default_img = get_path('assets', 'images', 'default_background.png')
        clip = None

        if custom_image_path and os.path.exists(custom_image_path):
            logger.info(f"🖼️ Found custom image. Processing layout...")
            processed_bg_path = get_path('assets', 'temp', f"{episode_id}_processed_bg.jpg")
            os.makedirs(os.path.dirname(processed_bg_path), exist_ok=True)
            
            # Gọi hàm xử lý ảnh Cinematic Gradient
            final_bg_path = process_background_image(custom_image_path, processed_bg_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT)
            if final_bg_path:
                clip = ImageClip(final_bg_path).set_duration(duration)

        # Fallback
        if clip is None:
            if os.path.exists(bg_video_path):
                 clip = VideoFileClip(bg_video_path).set_audio(None).resize((OUTPUT_WIDTH, OUTPUT_HEIGHT)).loop(duration=duration)
            elif os.path.exists(bg_default_img):
                clip = ImageClip(bg_default_img).set_duration(duration).resize((OUTPUT_WIDTH, OUTPUT_HEIGHT))
            else:
                clip = ColorClip(size=(OUTPUT_WIDTH, OUTPUT_HEIGHT), color=(15,15,15), duration=duration)

        # --- 2. LAYER WAVEFORM & GLOW ---
        glow = make_glow_layer(duration)
        waveform = make_circular_waveform(audio_path, duration)
        waveform = waveform.set_position("center")

        # --- 3. LAYER TIÊU ĐỀ (TITLE OVERLAY) - GÓC TRÁI TRÊN ---
        title_layer = None
        if title_text:
            try:
                # Dùng font có sẵn trên hệ thống Linux
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
                )
                title_layer = title_layer.set_position((50, 50)).set_duration(duration)
            except Exception as e:
                logger.warning(f"⚠️ Không thể tạo Title Overlay: {e}")

        # --- 4. LAYER LOGO KÊNH ---
        logo_path = get_path('assets', 'images', 'channel_logo.png')
        logo_layer = None
        if os.path.exists(logo_path):
             logo_layer = ImageClip(logo_path).set_duration(duration).resize(height=100).set_position(("right", "top")).margin(right=20, top=20, opacity=0)

        # --- GỘP LAYERS ---
        layers = [clip, glow, waveform]
        if title_layer: layers.append(title_layer)
        if logo_layer: layers.append(logo_layer)

        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        # --- XUẤT FILE ---
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output), exist_ok=True)

        logger.info("🚀 Starting render with Title Overlay...")
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
