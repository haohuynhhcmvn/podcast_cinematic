# === scripts/create_video.py ===
import logging
import os
import numpy as np
import math
from pydub import AudioSegment
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

# --- [FIX QUAN TRỌNG] VÁ LỖI PILLOW 10+ CHO MOVIEPY ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ------------------------------------------------------

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, VideoClip, TextClip, concatenate_videoclips,
    vfx
)
from utils import get_path

logger = logging.getLogger(__name__)

# --- ĐỘ PHÂN GIẢI CHUNG (720P) ---
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
# -----------------------------------

# ============================================================
# 🎨 HÀM XỬ LÝ LỚP PHỦ TĨNH (NHÂN VẬT & VIGNETTE)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Tối ưu: Nhân vật nhỏ (60% chiều cao), CĂN GIỮA (Center), SÁT ĐÁY.
    Vignette: Gradient từ dưới lên (Bottom-up) để làm nền cho nhân vật.
    """
    logger.info("   (LOG-BG): Bắt đầu xử lý lớp phủ tĩnh (Center Character)...")
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    # 1. XỬ LÝ NHÂN VẬT (Thu nhỏ 60% & Căn giữa)
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
            
            # --- [CẤU HÌNH] THU NHỎ SIZE ---
            scale_factor = 0.6
            char_h = int(height * scale_factor)
            
            # Tính chiều rộng giữ nguyên tỉ lệ
            char_w = int(char_img.width * (char_h / char_img.height))
            char_img = char_img.resize((char_w, char_h), PIL.Image.LANCZOS)
            
            # --- [CẤU HÌNH] MASK ---
            # Vì ở giữa nên không cần fade một bên, mà giữ nguyên hình dáng
            # hoặc làm mềm cực nhẹ xung quanh (nếu cần). Ở đây giữ nguyên cho sắc nét.
            mask = Image.new("L", (char_w, char_h), 255)
            
            # --- [CẤU HÌNH] VỊ TRÍ DÁN (CENTER - BOTTOM) ---
            paste_x = (width - char_w) // 2  # Căn giữa theo chiều ngang
            paste_y = height - char_h        # Sát đáy theo chiều dọc
            
            final_overlay.paste(char_img, (paste_x, paste_y), mask=mask)
            logger.info(f"   (LOG-BG): ✅ Nhân vật Center ({int(scale_factor*100)}% height).")
        except Exception as e:
            logger.error(f"   (LOG-BG): ❌ Lỗi xử lý ảnh nhân vật: {e}")

    # 2. TẠO VIGNETTE (BÓNG ĐEN TỪ DƯỚI LÊN)
    # Tạo gradient đen ở dưới chân để nhân vật không bị lơ lửng, 
    # nhưng phía trên thì trong suốt để thấy video nền.
    
    vignette_layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw_grad = ImageDraw.Draw(vignette_layer)
    
    # Gradient chiếm 40% chiều cao từ dưới lên
    grad_height = int(height * 0.4)
    start_y = height - grad_height
    
    for y in range(grad_height): 
        # Càng xuống dưới càng đen (max alpha 180)
        alpha = int(180 * (y / grad_height)) 
        # Vẽ từng dòng ngang từ trái qua phải
        draw_grad.line([(0, start_y + y), (width, start_y + y)], fill=(0, 0, 0, alpha))
        
    final_overlay = Image.alpha_composite(final_overlay, vignette_layer)
    
    overlay_path = get_path('assets', 'temp', "char_vignette_overlay.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    
    # [QUAN TRỌNG] Lưu PNG
    final_overlay.save(overlay_path, format="PNG") 
    
    return overlay_path


# ============================================================
# 🎥 HÀM TẠO NỀN VIDEO LAI (HYBRID VIDEO BACKGROUND)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Tạo nền phức hợp: Video động (Sáng) + Ảnh tĩnh (Mờ) + Nhân vật (Giữa).
    """
    logger.info("   (LOG-BG): Bắt đầu tạo Hybrid Video Background...")
    try:
        layers_to_composite = []
        base_clip = None

        # --- LỚP 1: VIDEO ĐỘNG (ĐÁY) ---
        try:
            temp_clip = VideoFileClip(video_path)
            
            if temp_clip.duration < duration:
                num_loops = math.ceil(duration / temp_clip.duration)
                looped_clips = [temp_clip] * num_loops
                final_clip = concatenate_videoclips(looped_clips, method="compose")
            else:
                final_clip = temp_clip
                
            base_clip = final_clip.subclip(0, duration)
            base_clip = base_clip.resize(height=height) 
            base_clip = base_clip.crop(x_center=base_clip.w/2, y_center=base_clip.h/2, width=width, height=height)
            
            # [CẤU HÌNH] Video nền sáng 90%
            base_clip = base_clip.fx(vfx.colorx, factor=0.9)
            
            layers_to_composite.append(base_clip)
            logger.info("   (LOG-BG): ✅ Video Nền Động (Sáng 90%).")
            
        except Exception as video_e:
            logger.error(f"   (LOG-BG): ❌ Lỗi Video Nền: {video_e}. Fallback ảnh tĩnh.")
            base_clip = None 

        # --- LỚP 2: HÌNH NỀN TĨNH (GIỮA) ---
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            img_clip = img_clip.resize(height=height)
            img_clip = img_clip.crop(x_center=img_clip.w/2, y_center=img_clip.h/2, width=width, height=height)
            
            if base_clip is not None:
                # [CẤU HÌNH] Opacity 25%
                static_bg_clip = img_clip.set_opacity(0.25) 
            else:
                static_bg_clip = img_clip.set_opacity(1.0) 
            
            layers_to_composite.append(static_bg_clip) 
            logger.info("   (LOG-BG): ✅ Ảnh Nền Tĩnh (Opacity 25%).")

        # --- LỚP 3: LỚP PHỦ NHÂN VẬT (TRÊN CÙNG) ---
        if os.path.exists(char_overlay_path):
            overlay_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers_to_composite.append(overlay_clip)
            logger.info("   (LOG-BG): ✅ Lớp Phủ Nhân vật (Center) đã thêm.")
        
        if not layers_to_composite:
            return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)
            
        final_bg_clip = CompositeVideoClip(layers_to_composite, size=(width, height))
        return final_bg_clip.set_duration(duration)
        
    except Exception as e:
        logger.error(f"❌ LỖI BACKGROUND: {e}", exc_info=True)
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)


# ============================================================
# 🌟 CIRCULAR WAVEFORM (OPTIMIZED)
# ============================================================
def make_circular_waveform(audio_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """ Tạo sóng âm thanh (Low-Res Calculation). """
    calc_w, calc_h = 400, 400 
    fps = 20 
    
    logger.info("   (LOG-WF): Bắt đầu tạo Waveform (Optimized)...")
    try:
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
            base_radius = 20 + amp * 50 
            
            for i in range(waves):
                radius = base_radius + i * 10 
                opacity = max(0.0, 1.0 - i * 0.08)
                if opacity <= 0: continue
                ring_mask = (dist_matrix >= radius - 0.8) & (dist_matrix <= radius + 0.8)
                mask_frame[ring_mask] = opacity
            return mask_frame

        mask_clip_low_res = VideoClip(make_mask_frame, duration=duration, ismask=True).set_fps(fps)
        mask_clip_high_res = mask_clip_low_res.resize((width, height))
        color_clip = ColorClip(size=(width, height), color=(255, 215, 0), duration=duration) 
        
        return color_clip.set_mask(mask_clip_high_res)
    
    except Exception as e:
        logger.error(f"❌ Lỗi Waveform: {e}")
        return ColorClip(size=(width, height), color=(0, 0, 0), duration=duration)


def make_glow_layer(duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """ Tạo lớp phát sáng mờ. """
    low_w, low_h = 320, 180
    y = np.linspace(0, low_h - 1, low_h)
    x = np.linspace(0, low_w - 1, low_w)
    xx, yy = np.meshgrid(x, y)
    lcx, lcy = low_w // 2, int(low_h * 0.45) 
    radius = int(min(low_w, low_h) * 0.45)
    dist = np.sqrt((xx - lcx)**2 + (yy - lcy)**2)
    intensity = np.clip(255 - (dist / radius) * 255, 0, 255)
    
    glow_low = np.zeros((low_h, low_w, 3), dtype=np.uint8)
    glow_low[:, :, 0] = (intensity * 0.7).astype(np.uint8) 
    glow_low[:, :, 1] = (intensity * 0.5).astype(np.uint8)
    glow_low[:, :, 2] = 0                               
    
    return ImageClip(glow_low).resize((width, height)).set_duration(duration).set_opacity(0.3)

# ============================================================
# 🎬 HÀM CHÍNH (CREATE VIDEO)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        # 1. Setup Audio
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"   (LOG): Đang xử lý Audio. Duration = {duration:.2f}s") 

        # 2. Tạo Lớp Phủ Tĩnh (Nhân vật + Vignette)
        char_overlay_path = create_static_overlay_image(custom_image_path)
        
        # 3. XÁC ĐỊNH CÁC NGUỒN NỀN
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        static_bg_path = get_path('assets', 'images', 'default_background.png')
        
        # --- LOGIC HYBRID VIDEO BACKGROUND ---
        clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)
        clip = clip.set_duration(duration)

        # 4. Waveform & Glow
        glow = make_glow_layer(duration)
        waveform = make_circular_waveform(audio_path, duration)
        
        # [CẤU HÌNH] Waveform: Đẩy lên cao (Top) để không che mặt nhân vật ở giữa
        # Cách lề trên 50px
        waveform = waveform.set_position(("center", 50))

        # 5. Title Text
        title_layer = None
        if title_text:
            try:
                # Đổi text sang góc trái trên (Top-Left) vì ở giữa đã có waveform
                title_layer = TextClip(
                    title_text.upper(),
                    fontsize=55, font='DejaVu-Sans-Bold', color='#FFD700', stroke_color='black', stroke_width=3,
                    method='caption', align='West', size=(800, None)       
                ).set_position((50, 50)).set_duration(duration)
            except Exception as e:
                logger.warning(f"⚠️ Title Error: {e}")

        # 6. Channel Logo
        logo_path = get_path('assets', 'images', 'channel_logo.png')
        logo_layer = None
        if os.path.exists(logo_path):
            logo_layer = ImageClip(logo_path).set_duration(duration).resize(height=100).set_position(("right", "top")).margin(right=20, top=20, opacity=0)

        # 7. Composite Final
        layers = [clip, glow, waveform]
        if title_layer: layers.append(title_layer)
        if logo_layer: layers.append(logo_layer)
        
        logger.info("   (LOG): Đang Composite tất cả các lớp...")

        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        # 8. Render Optimized
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        logger.info("🚀 PHASE RENDER: Bắt đầu Render Long Video (Optimized)...")
        
        final.write_videofile(
            output, fps=20, codec="libx264", audio_codec="aac", preset="ultrafast", threads=2, ffmpeg_params=["-crf", "28"], logger='bar' 
        )
        logger.info(f"✅ RENDER SUCCESS: {output}")
        return output

    except Exception as e:
        logger.error(f"❌ Lỗi FATAL CREATE VIDEO: {e}", exc_info=True)
        return False
