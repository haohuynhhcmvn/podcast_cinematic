# ===scripts/create_video.py===
import logging
import os
import numpy as np
from pydub import AudioSegment
from PIL import Image, ImageEnhance, ImageFilter # <--- Thêm thư viện xử lý ảnh
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, VideoClip
)
from utils import get_path

logger = logging.getLogger(__name__)

# ============================================================
# 🌑 HÀM XỬ LÝ BACKGROUND (CHIẾN LƯỢC 1 MŨI TÊN 2 ĐÍCH)
# ============================================================
def process_background_image(input_path, output_path, width=1920, height=1080):
    """
    Xử lý ảnh AI để làm nền video:
    1. Center Crop (Fill màn hình).
    2. Darken (Làm tối).
    3. Blur (Làm mờ).
    Dùng PIL xử lý 1 lần -> Render nhanh gấp 10 lần so với MoviePy.
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGB")
            
            # --- 1. RESIZE & CENTER CROP (ASPECT FILL) ---
            target_ratio = width / height
            img_ratio = img.width / img.height
            
            if img_ratio > target_ratio:
                # Ảnh rộng hơn -> Resize theo chiều cao
                new_height = height
                new_width = int(new_height * img_ratio)
            else:
                # Ảnh cao hơn -> Resize theo chiều rộng
                new_width = width
                new_height = int(new_width / img_ratio)
                
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Crop lấy phần giữa
            left = (new_width - width) // 2
            top = (new_height - height) // 2
            img = img.crop((left, top, left + width, top + height))
            
            # --- 2. LÀM TỐI (DARKEN) ---
            # Giảm độ sáng còn 40% để Sóng nhạc & Chữ nổi bật
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.4) 
            
            # --- 3. LÀM MỜ (BLUR) ---
            # Tạo cảm giác Cinematic và đỡ rối mắt
            img = img.filter(ImageFilter.GaussianBlur(radius=5))
            
            # Lưu file
            img.save(output_path, quality=95)
            return output_path
            
    except Exception as e:
        logger.error(f"❌ Error processing background image: {e}")
        return None


# ============================================================
# 🌟 CIRCULAR WAVEFORM – TỐI ƯU HÓA (GIỮ NGUYÊN HIỆU NĂNG CAO)
# ============================================================
def make_circular_waveform(audio_path, duration, width=1920, height=1080):
    # Tính toán ở độ phân giải thấp (Nhanh gấp 9 lần)
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
    color_clip = ColorClip(size=(width, height), color=(235, 235, 235), duration=duration)
    return color_clip.set_mask(mask_clip_high_res)


# ============================================================
# 🌟 Light Glow – Tối ưu hóa
# ============================================================
def make_glow_layer(duration, width=1920, height=1080):
    low_w, low_h = 320, 180
    y = np.linspace(0, low_h - 1, low_h)
    x = np.linspace(0, low_w - 1, low_w)
    xx, yy = np.meshgrid(x, y)
    lcx, lcy = low_w // 2, int(low_h * 0.45)
    radius = int(min(low_w, low_h) * 0.45)
    dist = np.sqrt((xx - lcx)**2 + (yy - lcy)**2)
    intensity = np.clip(255 - (dist / radius) * 255, 0, 255)
    glow_low = np.zeros((low_h, low_w, 3), dtype=np.uint8)
    glow_low[:, :, :] = (intensity * 0.25).astype(np.uint8).reshape(low_h, low_w, 1)
    return ImageClip(glow_low).resize((width, height)).set_duration(duration).set_opacity(0.18)


# ============================================================
# 🎬 HÀM TẠO VIDEO CHÍNH (LOGIC MỚI)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None):
    try:
        # -----------------------------------------------------
        # 🔥 Setup Duration
        # -----------------------------------------------------
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"🎧 Audio duration = {duration:.2f}s")

        # -----------------------------------------------------
        # ⭐ Load background (LOGIC THÔNG MINH)
        # -----------------------------------------------------
        bg_video_path = get_path('assets', 'video', 'pppodcast_loop_bg_long.mp4')
        bg_default_img = get_path('assets', 'images', 'default_background.png')
        
        clip = None

        # [ƯU TIÊN 1]: ẢNH NHÂN VẬT (CHIẾN LƯỢC 1 MŨI TÊN 2 ĐÍCH)
        if custom_image_path and os.path.exists(custom_image_path):
            logger.info(f"🖼️ Found custom image: {custom_image_path}")
            # Tạo đường dẫn file tạm cho ảnh đã xử lý
            processed_bg_path = get_path('assets', 'temp', f"{episode_id}_processed_bg.jpg")
            os.makedirs(os.path.dirname(processed_bg_path), exist_ok=True)
            
            # Xử lý ảnh (Darken + Blur + Resize)
            final_bg_path = process_background_image(custom_image_path, processed_bg_path)
            
            if final_bg_path:
                logger.info(f"🎨 Using Processed Background: {final_bg_path}")
                clip = ImageClip(final_bg_path).set_duration(duration)

        # [ƯU TIÊN 2]: VIDEO LOOP MẶC ĐỊNH
        if clip is None and os.path.exists(bg_video_path):
             clip = (
                VideoFileClip(bg_video_path)
                .set_audio(None)
                .resize((1920, 1080))
                .loop(duration=duration)
            )

        # [FALLBACK]: ẢNH MẶC ĐỊNH HOẶC MÀU ĐEN
        if clip is None:
            if os.path.exists(bg_default_img):
                clip = ImageClip(bg_default_img).set_duration(duration).resize((1920, 1080))
            else:
                clip = ColorClip(size=(1920, 1080), color=(10,10,10), duration=duration)

        # -----------------------------------------------------
        # ⭐ Layers
        # -----------------------------------------------------
        glow = make_glow_layer(duration)
        waveform = make_circular_waveform(audio_path, duration)
        waveform = waveform.set_position("center")

        mic_path = get_path('assets', 'images', 'microphone.png')
        mic = None
        if os.path.exists(mic_path):
            mic = (
                ImageClip(mic_path)
                .set_duration(duration)
                .resize(height=260)
                .set_pos(("center", "bottom"))
            )

        layers = [clip, glow, waveform]
        if mic:
            layers.append(mic)

        final = CompositeVideoClip(layers, size=(1920, 1080)).set_audio(audio)

        # -----------------------------------------------------
        # ⭐ Xuất video (ULTRAFAST)
        # -----------------------------------------------------
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output), exist_ok=True)

        logger.info("🚀 Starting fast render...")
        final.write_videofile(
            output,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",      # Render nhanh nhất
            threads=4,
            ffmpeg_params=["-crf", "28"], 
            size=(1280, 720),
            logger=None 
        )

        logger.info(f"✅ DONE: {output}")
        
        # Dọn dẹp ảnh tạm nếu cần
        if custom_image_path and os.path.exists(get_path('assets', 'temp', f"{episode_id}_processed_bg.jpg")):
             try:
                 os.remove(get_path('assets', 'temp', f"{episode_id}_processed_bg.jpg"))
             except:
                 pass

        return output

    except Exception as e:
        logger.error(f"❌ VIDEO ERROR: {e}", exc_info=True)
        return None
