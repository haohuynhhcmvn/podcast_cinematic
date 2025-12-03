# ===scripts/create_video.py===
import logging
import os
import numpy as np
from pydub import AudioSegment
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, VideoClip
)
from utils import get_path

logger = logging.getLogger(__name__)

# ============================================================
# 🌟 CIRCULAR WAVEFORM – TỐI ƯU HÓA (LOW RES CALCULATION)
# ============================================================
def make_circular_waveform(audio_path, duration, width=1920, height=1080):
    # ⚡ [CHIẾN THUẬT TĂNG TỐC]: Tính toán ở độ phân giải thấp (360p)
    # Thay vì tính 2 triệu điểm ảnh, chỉ tính 230k điểm ảnh (Nhanh gấp 9 lần)
    calc_w, calc_h = 640, 360 
    
    # FPS render cho sóng (không cần 60fps cho sóng trừu tượng)
    fps = 20 

    # 1. Xử lý Audio
    audio = AudioSegment.from_file(audio_path)
    # Lấy mẫu với tốc độ thấp hơn để khớp fps video (Tối ưu mảng numpy)
    chunk_size = int(audio.frame_rate / fps)
    
    # Convert to mono & normalize
    raw_samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    if audio.channels == 2:
        raw_samples = raw_samples.reshape((-1, 2)).mean(axis=1)
    
    # Downsample audio data để khớp với số frame video (tránh lấy idx phức tạp)
    # Lấy giá trị tuyệt đối trung bình cho mỗi chunk (Envelope)
    num_frames = int(duration * fps) + 1
    envelope = []
    
    # Loop nhanh để tạo envelope (nhẹ hơn tính trực tiếp trong frame maker)
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
        envelope = envelope / max_val # Normalize 0-1

    # Cấu hình sóng (Giảm số lượng để render nhanh)
    waves = 15 # Giảm từ 35 -> 15 (Vẫn đẹp nhưng nhẹ CPU)
    center = (calc_w // 2, calc_h // 2)
    
    # Pre-calculate khoảng cách (Distance Matrix) MỘT LẦN DUY NHẤT
    # Thay vì tính trong từng frame
    yy, xx = np.ogrid[:calc_h, :calc_w]
    dist_sq = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
    dist_matrix = np.sqrt(dist_sq)

    # 2. Hàm tạo Mask (Chạy trên độ phân giải thấp)
    def make_mask_frame(t):
        frame_idx = int(t * fps)
        frame_idx = min(frame_idx, len(envelope) - 1)
        amp = envelope[frame_idx]

        # Mask nền đen
        mask_frame = np.zeros((calc_h, calc_w), dtype=np.float32)

        # Bán kính cơ sở (nhỏ hơn vì đang ở res thấp)
        base_radius = 25 + amp * 20 

        for i in range(waves):
            # Tính toán vector hóa (Vectorized operation)
            radius = base_radius + i * 6
            opacity = max(0.0, 1.0 - i * 0.06)

            if opacity <= 0: continue

            # Vẽ vòng tròn (Ring thickness ~ 1.5px ở res thấp)
            # Dùng logic mờ (Gaussian fake) bằng cách check khoảng cách
            ring_mask = (dist_matrix >= radius - 1.5) & (dist_matrix <= radius + 1.5)
            
            mask_frame[ring_mask] = opacity

        return mask_frame

    # 3. Tạo Mask Clip ở độ phân giải thấp
    mask_clip_low_res = VideoClip(make_mask_frame, duration=duration, ismask=True).set_fps(fps)

    # 4. Phóng to (Resize) lên 1080p
    # MoviePy dùng FFmpeg để resize, nhanh hơn Python tính toán từng pixel
    mask_clip_high_res = mask_clip_low_res.resize((width, height))

    # 5. Tạo Color Clip
    color_clip = ColorClip(size=(width, height), color=(235, 235, 235), duration=duration)
    
    final_waveform = color_clip.set_mask(mask_clip_high_res)

    return final_waveform


# ============================================================
# 🌟 Light Glow – Tối ưu hóa (Dùng ảnh tĩnh thay vì tính toán)
# ============================================================
def make_glow_layer(duration, width=1920, height=1080):
    # Thay vì tính toán np.sqrt cho 2 triệu pixel, ta dùng Radial Gradient giả lập
    # Hoặc tính ở res thấp rồi resize như trên.
    # Ở đây làm cách nhanh: Tính 1 frame duy nhất rồi lặp lại.
    
    cx, cy = width // 2, int(height * 0.45)
    
    # Tính trên res thấp 1 lần duy nhất
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

    # Resize lên 1080p -> set duration -> set opacity
    return ImageClip(glow_low).resize((width, height)).set_duration(duration).set_opacity(0.18)


# ============================================================
# 🎬 HÀM TẠO VIDEO CHÍNH
# ============================================================
def create_video(audio_path, episode_id):
    try:
        # -----------------------------------------------------
        # 🔥 Setup Duration
        # -----------------------------------------------------
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"🎧 Audio duration = {duration:.2f}s")

        # -----------------------------------------------------
        # ⭐ Load background (Ưu tiên ảnh tĩnh cho nhanh)
        # -----------------------------------------------------
        bg_video_path = get_path('assets', 'video', 'pppodcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')

        # Nếu là Shorts (<65s), ưu tiên dùng Ảnh tĩnh để render siêu tốc
        is_short = duration < 65
        
        if is_short and os.path.exists(bg_image_path):
             clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
        elif os.path.exists(bg_video_path):
            clip = (
                VideoFileClip(bg_video_path)
                .set_audio(None)
                .resize((1920, 1080))
                .loop(duration=duration)
            )
        elif os.path.exists(bg_image_path):
            clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
        else:
            clip = ColorClip(size=(1920, 1080), color=(10,10,10), duration=duration)

        # -----------------------------------------------------
        # ⭐ Layers
        # -----------------------------------------------------
        # Glow (Đã tối ưu)
        glow = make_glow_layer(duration)

        # Waveform (Đã tối ưu hóa thuật toán)
        waveform = make_circular_waveform(audio_path, duration)
        waveform = waveform.set_position("center")

        # Microphone
        mic_path = get_path('assets', 'images', 'microphone.png')
        mic = None
        if os.path.exists(mic_path):
            mic = (
                ImageClip(mic_path)
                .set_duration(duration)
                .resize(height=260)
                .set_pos(("center", "bottom"))
            )

        # -----------------------------------------------------
        # ⭐ Ghép layers
        # -----------------------------------------------------
        layers = [clip, glow, waveform]
        if mic:
            layers.append(mic)

        final = CompositeVideoClip(layers, size=(1920, 1080)).set_audio(audio)

        # -----------------------------------------------------
        # ⭐ Xuất video (CẤU HÌNH SUPERFAST)
        # -----------------------------------------------------
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output), exist_ok=True)

        logger.info("🚀 Starting fast render...")
        final.write_videofile(
            output,
            fps=24,                  # 24fps là đủ cho content kể chuyện
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",      # QUAN TRỌNG: Tăng tốc render gấp 5 lần
            threads=4,               # Tận dụng tối đa 2 core của Github runner
            ffmpeg_params=["-crf", "28"], # Giảm chất lượng nén một chút để nhanh hơn (số càng to càng nhanh/nhẹ)
            logger=None 
        )

        logger.info(f"✅ DONE: {output}")
        return output

    except Exception as e:
        logger.error(f"❌ VIDEO ERROR: {e}", exc_info=True)
        return None
