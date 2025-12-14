# === scripts/create_video.py ===

# 1. KHAI BÁO THƯ VIỆN
import logging
import os
import numpy as np
import math
from pydub import AudioSegment
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageChops

# --- [FIX QUAN TRỌNG] VÁ LỖI PILLOW PHIÊN BẢN MỚI ---
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

# --- CẤU HÌNH ĐỘ PHÂN GIẢI ---
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
# ------------------------------


# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT (BLEND MODE: DOUBLE EXPOSURE)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Tạo ảnh nhân vật Full Size, giảm Opacity mạnh (khoảng 70%) để hòa trộn (Mix) vào nền.
    """
    logger.info("   (LOG-BG): Bắt đầu xử lý ảnh nhân vật (Double Exposure Mix)...")
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            # Load ảnh
            char_img = Image.open(char_path).convert("RGBA")
            
            # --- Resize (Full Height) ---
            new_char_h = height 
            new_char_w = int(char_img.width * (new_char_h / char_img.height))
            char_img = char_img.resize((new_char_w, new_char_h), PIL.Image.LANCZOS)
            
            # --- [BƯỚC QUAN TRỌNG] TẠO MASK HÒA TRỘN ---
            
            # 1. Lấy hình dáng gốc (Alpha channel)
            original_alpha = char_img.getchannel("A")
            
            # 2. Co vùng hiển thị vào trong (tăng từ 20px -> 25px)
            shrink_radius = 25
            eroded_mask = original_alpha.filter(ImageFilter.MinFilter(shrink_radius))
            
            # 3. Làm mềm biên cực mạnh (tăng từ 30px -> 35px)
            blur_radius = 35
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(blur_radius))
            
            # 4. [KEY FIX] GIẢM ĐỘ ĐẬM TOÀN THÂN (GLOBAL OPACITY)
            # Giảm từ 230 xuống 190 (tương đương 75% độ đậm) để nền TĨNH có thể xuyên qua rõ rệt.
            blend_opacity = 190 
            opacity_layer = Image.new("L", soft_edge_mask.size, blend_opacity)
            
            # Kết hợp Soft Edge + Global Opacity
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            # --- Vị trí: Giữa & Sát đáy ---
            paste_x = (width - new_char_w) // 2 
            paste_y = height - new_char_h       
            
            # Dán nhân vật với mask đã mix
            final_overlay.paste(char_img, (paste_x, paste_y), mask=final_mask)
            logger.info(f"   (LOG-BG): ✅ Nhân vật đã Blend: Alpha={blend_opacity}, SoftBlur={blur_radius}.")
            
        except Exception as e:
            logger.error(f"   (LOG-BG): ❌ Lỗi xử lý nhân vật: {e}")

    # Lưu PNG
    overlay_path = get_path('assets', 'temp', "char_blend_mix.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    
    return overlay_path


# ============================================================
# 🎥 HÀM 2: TẠO NỀN "DREAMY CINEMATIC" (VIDEO OVERLAY)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Cấu trúc Layer: Ảnh tĩnh (Rõ) -> Nhân vật (Blend) -> Video Overlay (Mờ).
    """
    logger.info("   (LOG-BG): Bắt đầu phối cảnh (Cinematic Layering)...")
    try:
        layers_to_composite = []

        # --- LAYER 1: ẢNH NỀN TĨNH (ĐÁY) ---
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            img_clip = img_clip.resize(height=height)
            img_clip = img_clip.crop(x_center=img_clip.w/2, y_center=img_clip.h/2, width=width, height=height)
            img_clip = img_clip.set_opacity(1.0) # Rõ 100%
            layers_to_composite.append(img_clip)
            logger.info("   (LOG-BG): ✅ [Lớp 1] Ảnh nền tĩnh (Gốc).")

        # --- LAYER 2: NHÂN VẬT (GIỮA - ĐÃ BLEND) ---
        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers_to_composite.append(char_clip)
            logger.info("   (LOG-BG): ✅ [Lớp 2] Nhân vật (Đã Blend).")

        # --- LAYER 3: VIDEO CHUYỂN ĐỘNG (TRÊN CÙNG) ---
        try:
            temp_clip = VideoFileClip(video_path)
            
            if temp_clip.duration < duration:
                num_loops = math.ceil(duration / temp_clip.duration)
                looped_clips = [temp_clip] * num_loops
                final_video = concatenate_videoclips(looped_clips, method="compose")
            else:
                final_video = temp_clip
            
            video_layer = final_video.subclip(0, duration)
            video_layer = video_layer.resize(height=height) 
            video_layer = video_layer.crop(x_center=video_layer.w/2, y_center=video_layer.h/2, width=width, height=height)
            
            # Opacity 35% + Tăng sáng 1.1 (Hiệu ứng sương/bụi bay bắt mắt)
            video_layer = video_layer.set_opacity(0.35).fx(vfx.colorx, factor=1.1)

            layers_to_composite.append(video_layer)
            logger.info("   (LOG-BG): ✅ [Lớp 3] Video Overlay (Mờ ảo).")
            
        except Exception as e:
            logger.error(f"   (LOG-BG): ❌ Lỗi video overlay: {e}")

        if not layers_to_composite:
            return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)
            
        final_bg_clip = CompositeVideoClip(layers_to_composite, size=(width, height))
        return final_bg_clip.set_duration(duration)
        
    except Exception as e:
        logger.error(f"❌ Lỗi tổng hợp nền: {e}", exc_info=True)
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)


# ============================================================
# 🌊 HÀM 3: TẠO SÓNG NHẠC (THƯA & SANG TRỌNG)
# ============================================================
def make_circular_waveform(audio_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """ Tạo sóng nhạc thưa, đường nét mảnh để không che hình ảnh. """
    calc_w, calc_h = 500, 500 
    fps = 20 
    
    logger.info("   (LOG-WF): Tạo Waveform (Elegant Mode)...")
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

        # --- CẤU HÌNH WAVEFORM ---
        waves = 8  # Ít vòng (8 vòng)
        center = (calc_w // 2, calc_h // 2)
        yy, xx = np.ogrid[:calc_h, :calc_w]
        dist_sq = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
        dist_matrix = np.sqrt(dist_sq)

        def make_mask_frame(t):
            frame_idx = int(t * fps)
            frame_idx = min(frame_idx, len(envelope) - 1)
            amp = envelope[frame_idx]
            mask_frame = np.zeros((calc_h, calc_w), dtype=np.float32)
            
            # Bán kính lớn hơn
            base_radius = 40 + amp * 60 
            
            for i in range(waves):
                # Khoảng cách rộng (25px)
                radius = base_radius + i * 25 
                
                opacity = max(0.0, 1.0 - i * 0.12)
                if opacity <= 0: continue
                
                # Nét rất mảnh (0.3)
                ring_mask = (dist_matrix >= radius - 0.3) & (dist_matrix <= radius + 0.3)
                mask_frame[ring_mask] = opacity
            return mask_frame

        mask_clip_low_res = VideoClip(make_mask_frame, duration=duration, ismask=True).set_fps(fps)
        mask_clip_high_res = mask_clip_low_res.resize((width, height))
        color_clip = ColorClip(size=(width, height), color=(255, 215, 0), duration=duration) 
        return color_clip.set_mask(mask_clip_high_res)
    
    except Exception as e:
        logger.error(f"❌ Lỗi Waveform: {e}")
        return ColorClip(size=(width, height), color=(0, 0, 0, 0), duration=duration)


# ============================================================
# ✨ HÀM 4: GLOW LAYER
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
    glow_low[:, :, 0] = (intensity * 0.7).astype(np.uint8) 
    glow_low[:, :, 1] = (intensity * 0.5).astype(np.uint8) 
    glow_low[:, :, 2] = 0                                  
    
    return ImageClip(glow_low).resize((width, height)).set_duration(duration).set_opacity(0.3)

# ============================================================
# 🎬 HÀM CHÍNH
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"   (LOG): Audio Duration = {duration:.2f}s") 

        # 1. Ảnh nhân vật
        char_overlay_path = create_static_overlay_image(custom_image_path)
        
        # 2. Tài nguyên nền
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        static_bg_path = get_path('assets', 'images', 'default_background.png')
        
        # 3. Nền Cinematic Mix
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)
        background_clip = background_clip.set_duration(duration)

        # 4. Hiệu ứng
        glow_layer = make_glow_layer(duration)
        waveform_layer = make_circular_waveform(audio_path, duration)
        waveform_layer = waveform_layer.set_position(("center", 50)) 

        # 5. Tiêu đề
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

        # 6. Logo
        logo_path = get_path('assets', 'images', 'channel_logo.png')
        logo_layer = None
        if os.path.exists(logo_path):
            logo_layer = ImageClip(logo_path).set_duration(duration).resize(height=100).set_position(("right", "top")).margin(right=20, top=20, opacity=0)

        # 7. Composite
        final_layers = [background_clip, glow_layer, waveform_layer]
        if title_layer: final_layers.append(title_layer)
        if logo_layer: final_layers.append(logo_layer)
        
        logger.info("   (LOG): Compositing...")
        final_video = CompositeVideoClip(final_layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        # 8. Render
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        logger.info(f"🚀 RENDER START: {output_path}")
        final_video.write_videofile(
            output_path, fps=20, codec="libx264", audio_codec="aac", preset="ultrafast", threads=2, ffmpeg_params=["-crf", "28"], logger='bar' 
        )
        logger.info(f"✅ RENDER SUCCESS!")
        return output_path

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
        return False
