# ===scripts/create_video.py===
import logging
import os
import numpy as np
from pydub import AudioSegment
from PIL import Image, ImageDraw

# --- [FIX QUAN TRỌNG] VÁ LỖI PILLOW 10+ CHO MOVIEPY ---
import PIL.Image
# Đảm bảo dùng LANCZOS nếu ANTIALIAS không tồn tại (Pillow 10+)
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ------------------------------------------------------

from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, VideoClip, TextClip,
    vfx # Cần thiết cho các hiệu ứng video như colorx
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
    Tạo một lớp phủ (overlay image) chứa nhân vật (fade-in) và vignette đen.
    Lớp này được dùng chung cho cả nền tĩnh và nền động.
    """
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    # 1. XỬ LÝ NHÂN VẬT (Lớp trên, Fade-in từ phải)
    if char_path and os.path.exists(char_path):
        try:
            char_img = Image.open(char_path).convert("RGBA")
            
            char_h = height
            char_w = int(char_img.width * (char_h / char_img.height))
            char_img = char_img.resize((char_w, char_h), Image.LANCZOS)
            
            # Tạo Mask Gradient
            mask = Image.new("L", (char_w, char_h), 0)
            draw_mask = ImageDraw.Draw(mask)
            
            for x in range(char_w):
                pct = x / char_w
                # Fade-in từ 20% đến 60% chiều rộng ảnh
                if pct < 0.2:
                    alpha = 0
                elif pct > 0.6:
                    alpha = 255
                else:
                    alpha = int(255 * ((pct - 0.2) / 0.4))
                
                draw_mask.line([(x, 0), (x, char_h)], fill=alpha)
            
            # Tính vị trí paste (căn về bên phải, dịch vào 50px)
            paste_x = width - char_w + 50 
            if paste_x < 0: paste_x = 0
            
            final_overlay.paste(char_img, (paste_x, 0), mask=mask)
            logger.info("✅ Đã xử lý lớp nhân vật Overlay.")
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý ảnh nhân vật: {e}")

    # 2. TẠO VIGNETTE ĐEN BÊN TRÁI
    gradient = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw_grad = ImageDraw.Draw(gradient)
    
    # Kéo dài Vignette 60% màn hình
    for x in range(int(width * 0.6)): 
        alpha = int(200 * (1 - (x / (width * 0.6))))
        draw_grad.line([(x, 0), (x, height)], fill=(0, 0, 0, alpha))
        
    final_overlay = Image.alpha_composite(final_overlay, gradient)
    
    overlay_path = get_path('assets', 'temp', "char_vignette_overlay.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.convert("RGB").save(overlay_path, quality=95)
    
    return overlay_path


# ============================================================
# 🎥 HÀM TẠO NỀN VIDEO LAI (HYBRID VIDEO BACKGROUND)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Tạo nền phức hợp: Video động (đáy) + Ảnh tĩnh (giữa, bán trong suốt) + Lớp phủ nhân vật (trên).
    """
    try:
        layers_to_composite = []

        # --- LỚP 1: VIDEO ĐỘNG (ĐÁY) ---
        base_clip = VideoFileClip(video_path)

        if base_clip.duration < duration:
            base_clip = base_clip.loop(duration=duration)
        elif base_clip.duration > duration:
            base_clip = base_clip.subclip(0, duration)
        
        # Căn chỉnh kích thước (Aspect Fill & Center Crop)
        base_clip = base_clip.resize(height=height) 
        base_clip = base_clip.crop(x_center=base_clip.w/2, y_center=base_clip.h/2, width=width, height=height)
        
        # FIX LỖI ATTRIBUTE ERROR: Dùng vfx.colorx để làm tối (factor=0.7)
        base_clip = base_clip.fx(vfx.colorx, factor=0.7)
        
        layers_to_composite.append(base_clip)


        # --- LỚP 2: HÌNH NỀN TĨNH (GIỮA, Dùng default_background.png) ---
        if static_bg_path and os.path.exists(static_bg_path):
            logger.info(f"🖼️ Đang thêm lớp nền tĩnh: {static_bg_path}")
            img_clip = ImageClip(static_bg_path)
            
            # Resize & Crop fill màn hình
            img_clip = img_clip.resize(height=height)
            img_clip = img_clip.crop(x_center=img_clip.w/2, y_center=img_clip.h/2, width=width, height=height)
            
            # Set thời lượng và ĐỘ TRONG SUỐT (Opacity 30%)
            static_bg_clip = img_clip.set_duration(duration).set_opacity(0.3)
            
            layers_to_composite.append(static_bg_clip)


        # --- LỚP 3: LỚP PHỦ NHÂN VẬT & VIGNETTE (TRÊN) ---
        if os.path.exists(char_overlay_path):
            overlay_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers_to_composite.append(overlay_clip)

        
        # Composite tất cả các lớp nền lại (Đây là clip nền hoàn chỉnh)
        final_bg_clip = CompositeVideoClip(layers_to_composite, size=(width, height))
        return final_bg_clip.set_duration(duration)
        
    except Exception as e:
        logger.error(f"❌ Lỗi tạo Hybrid Video Background: {e}", exc_info=True)
        # Fallback nền đen
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)

# ============================================================
# 🌟 CIRCULAR WAVEFORM
# ============================================================
def make_circular_waveform(audio_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """ Tạo clip sóng âm thanh hình tròn, đồng bộ với audio. """
    calc_w, calc_h = 1000, 1000
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

    waves = 20
    center = (calc_w // 2, calc_h // 2)
    yy, xx = np.ogrid[:calc_h, :calc_w]
    dist_sq = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
    dist_matrix = np.sqrt(dist_sq)

    def make_mask_frame(t):
        frame_idx = int(t * fps)
        frame_idx = min(frame_idx, len(envelope) - 1)
        amp = envelope[frame_idx]
        mask_frame = np.zeros((calc_h, calc_w), dtype=np.float32)
        
        base_radius = 60 + amp * 100 
        
        for i in range(waves):
            radius = base_radius + i * 20 
            
            opacity = max(0.0, 1.0 - i * 0.05)
            if opacity <= 0: continue
            
            ring_mask = (dist_matrix >= radius - 0.6) & (dist_matrix <= radius + 0.6)
            
            mask_frame[ring_mask] = opacity
        return mask_frame

    mask_clip_low_res = VideoClip(make_mask_frame, duration=duration, ismask=True).set_fps(fps)
    mask_clip_high_res = mask_clip_low_res.resize((width, height))
    color_clip = ColorClip(size=(width, height), color=(255, 215, 0), duration=duration) 
    return color_clip.set_mask(mask_clip_high_res)


def make_glow_layer(duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """ Tạo lớp phát sáng mờ dưới sóng âm. """
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
    """
    Hàm chính tạo video từ audio, ảnh nhân vật và video nền động.
    """
    try:
        # 1. Setup Audio
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"🎧 Audio duration = {duration:.2f}s") 

        # 2. Tạo Lớp Phủ Tĩnh (Nhân vật + Vignette)
        char_overlay_path = create_static_overlay_image(custom_image_path)
        
        # 3. XÁC ĐỊNH CÁC NGUỒN NỀN
        base_video_path = get_path('assets', 'video', 'long_background.mp4')
        # Đường dẫn HÌNH NỀN TĨNH của bạn
        static_bg_path = get_path('assets', 'images', 'default_background.png')
        
        clip = None
        
        if os.path.exists(base_video_path):
            # SỬ DỤNG NỀN PHỨC HỢP (Video động + Ảnh tĩnh + Nhân vật)
            clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)
        else:
            # FALLBACK (Nếu không có video động)
            logger.warning(f"⚠️ Không tìm thấy Video nền động. Sử dụng nền tĩnh/đen.")
            
            # Nếu có ảnh tĩnh thì dùng ảnh tĩnh, không thì dùng màu đen
            if os.path.exists(static_bg_path):
                 # Resize và Crop ảnh tĩnh làm nền chính
                 clip = ImageClip(static_bg_path).resize(height=OUTPUT_HEIGHT).crop(x_center=OUTPUT_WIDTH/2, y_center=OUTPUT_HEIGHT/2, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT).set_duration(duration)
            else:
                 clip = ColorClip(size=(OUTPUT_WIDTH, OUTPUT_HEIGHT), color=(15, 15, 15), duration=duration)

            # Dán lớp nhân vật lên trên nền tĩnh/đen
            if os.path.exists(char_overlay_path):
                overlay_clip = ImageClip(char_overlay_path).set_duration(duration)
                clip = CompositeVideoClip([clip, overlay_clip])
        
        clip = clip.set_duration(duration)


        # 4. Waveform & Glow (Các lớp trên cùng)
        glow = make_glow_layer(duration)
        waveform = make_circular_waveform(audio_path, duration)
        waveform = waveform.set_position("center")


        # 5. Title Text
        title_layer = None
        if title_text:
            try:
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

        # 7. Composite Final (Xếp chồng các lớp chính)
        layers = [clip, glow, waveform] # Nền -> Glow -> Sóng
        if title_layer: layers.append(title_layer)
        if logo_layer: layers.append(logo_layer)

        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        # 8. Render
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
