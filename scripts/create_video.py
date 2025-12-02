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
# 🌟 HIỆU ỨNG WAVEFORM DẠNG VÒNG TRÒN LAN RỘNG (RIPPLE)
# ============================================================
def make_circular_waveform(audio_path, duration, width=1920, height=1080):
    """
    Tạo hiệu ứng sóng âm dạng vòng tròn lan ra từ tâm video.
    Các vòng tròn lan theo thời gian và fade-out theo âm lượng thực tế.
    """
    fps = 30                      # số frame/giây
    pulse_interval = 0.35         # mỗi 0.35 giây tạo 1 vòng tròn
    max_radius = min(width, height) // 2
    speed = 420                   # tốc độ lan vòng tròn (pixel/giây)

    # ---------------------------------------------------------
    # 🟣 Tải audio & chuyển về mảng numpy
    # ---------------------------------------------------------
    audio = AudioSegment.from_file(audio_path)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    # Nếu audio stereo → chuyển về mono
    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    # Chuẩn hóa biên độ 0–1
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples /= max_val

    sample_rate = audio.frame_rate

    # Hàm lấy biên độ tại thời điểm t (theo giây)
    def get_amp(t):
        idx = int(t * sample_rate)
        if idx < 0 or idx >= len(samples):
            return 0
        return abs(samples[idx])

    cx, cy = width // 2, height // 2   # tâm video

    # ---------------------------------------------------------
    # 🟣 Hàm tạo frame cho hiệu ứng
    # ---------------------------------------------------------
    def make_frame(t):
        # Frame RGBA (nền trong suốt)
        frame = np.zeros((height, width, 4), dtype=np.uint8)

        # Số vòng tròn đã sinh ra cho đến thời điểm t
        pulse_count = int(t / pulse_interval)

        for i in range(pulse_count):
            pulse_t = i * pulse_interval
            age = t - pulse_t  # tuổi của vòng tròn

            if age < 0:
                continue

            # bán kính tăng theo thời gian
            r = int(speed * age)
            if r > max_radius:
                continue

            # Alpha giảm dần theo thời gian + theo âm lượng tại thời điểm pulse
            amp = get_amp(pulse_t)
            alpha = int(255 * (1 - age / (max_radius / speed)) * amp)
            alpha = max(0, min(255, alpha))

            if alpha <= 2:
                continue

            # Tạo mặt nạ vòng tròn
            thickness = 4
            yy, xx = np.ogrid[:height, :width]
            dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
            mask = np.logical_and(dist >= r - thickness, dist <= r + thickness)

            # Vẽ vòng tròn → màu trắng, alpha theo âm lượng
            frame[mask] = [255, 255, 255, alpha]

        return frame

    return VideoClip(make_frame, duration=duration).set_fps(fps)


# ============================================================
# 🌟 Light Glow – hiệu ứng sáng nhẹ trung tâm
# ============================================================
def make_glow_layer(duration, width=1920, height=1080):
    y = np.linspace(0, height - 1, height)
    x = np.linspace(0, width - 1, width)
    xx, yy = np.meshgrid(x, y)

    cx, cy = width // 2, int(height * 0.45)
    radius = int(min(width, height) * 0.45)

    dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
    intensity = np.clip(255 - (dist / radius) * 255, 0, 255)

    glow = np.zeros((height, width, 3), dtype=np.uint8)
    glow[:, :, :] = (intensity * 0.25).astype(np.uint8).reshape(height, width, 1)

    return ImageClip(glow).set_duration(duration).set_opacity(0.18)


# ============================================================
# 🎬 HÀM TẠO VIDEO CHÍNH (KHÔNG BAO GIỜ KÉO DÀI VIDEO)
# ============================================================
def create_video(audio_path, episode_id):
    try:
        # -----------------------------------------------------
        # 🔥 Video phải có thời lượng = thời lượng audio
        # -----------------------------------------------------
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"🎧 Audio duration = {duration:.2f}s (video sẽ bằng đúng thời gian này)")

        # -----------------------------------------------------
        # ⭐ Load background
        # -----------------------------------------------------
        bg_video_path = get_path('assets', 'video', 'pppodcast_loop_bg_long.mp4')
        bg_image_path = get_path('assets', 'images', 'default_background.png')

        if os.path.exists(bg_video_path):
            clip = (
                VideoFileClip(bg_video_path)
                .set_audio(None)
                .resize((1920, 1080))
                .loop(duration=duration)
            )
        elif os.path.exists(bg_image_path):
            clip = ImageClip(bg_image_path).set_duration(duration).resize((1920, 1080))
        else:
            clip = ColorClip(size=(1920, 1080), color=(0,0,0), duration=duration)

        # -----------------------------------------------------
        # ⭐ Hiệu ứng Glow
        # -----------------------------------------------------
        glow = make_glow_layer(duration)

        # -----------------------------------------------------
        # ⭐ Circular Ripple Waveform – hiệu ứng vòng tròn
        # -----------------------------------------------------
        waveform = make_circular_waveform(audio_path, duration)
        waveform = waveform.set_position("center")

        # -----------------------------------------------------
        # ⭐ Optional microphone icon
        # -----------------------------------------------------
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
        # ⭐ Ghép các layer vào nhau
        # -----------------------------------------------------
        layers = [clip, glow, waveform]
        if mic:
            layers.append(mic)

        final = CompositeVideoClip(layers).set_audio(audio)

        # -----------------------------------------------------
        # ⭐ Xuất video
        # -----------------------------------------------------
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")

        final.write_videofile(
            output,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="superfast",
            threads=4,
            logger=None,
        )

        logger.info(f"✅ DONE: {output}")
        return output

    except Exception as e:
        logger.error(f"❌ VIDEO ERROR: {e}", exc_info=True)
        return None
