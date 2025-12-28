"""
create_video_v2.py
==================

MỤC TIÊU:
- Render video documentary tự động với cảm xúc thị giác cao
- Giữ ổn định tuyệt đối trên GitHub Actions
- Không rewrite pipeline, chỉ nâng cấp chất lượng hình ảnh

MÔI TRƯỜNG:
- Python 3.11+
- moviepy==1.0.3
"""

# =========================
# 1. IMPORT & FIX TƯƠNG THÍCH
# =========================

import os
import random
import numpy as np

# Monkey patch bắt buộc cho Pillow + MoviePy trên Python 3.11+
# Nếu thiếu dòng này, resize sẽ crash ngầm
from PIL import Image
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    ColorClip,
    concatenate_videoclips
)
from moviepy.video.fx import all as vfx


# =========================
# 2. CẤU HÌNH CHUNG
# =========================

# Các giá trị này cố tình nhỏ để:
# - không gây mệt mắt
# - không làm ffmpeg quá tải
BEAT_MIN_SEC = 4.0
BEAT_MAX_SEC = 6.0

ZOOM_INTENSITY = 0.035       # zoom tối đa ~3.5%
PAN_INTENSITY = 0.02         # pan rất nhẹ
CHAR_DRIFT_PX = 1            # nhân vật chỉ trôi rất nhẹ

WAVEFORM_FPS = 10            # thấp để tiết kiệm CPU
OUTPUT_FPS = 20              # đủ mượt cho documentary


# =========================
# 3. VISUAL BEAT ENGINE
# =========================

def generate_visual_beats(duration: float):
    """
    Chia timeline video thành các 'beat' cảm xúc.
    Mỗi beat sẽ có 1 kiểu chuyển động nhẹ khác nhau.

    WHY:
    - Não người rất ghét hình đứng yên quá lâu
    - 4–6s là ngưỡng an toàn cho video dài
    """
    beats = []
    t = 0.0

    motions = (
        ["zoom_in"] * 6 +
        ["zoom_out"] * 3 +
        ["pan_left"] * 2 +
        ["pan_right"] * 2 +
        ["static"] * 1
    )

    while t < duration:
        length = random.uniform(BEAT_MIN_SEC, BEAT_MAX_SEC)
        beats.append({
            "start": t,
            "end": min(t + length, duration),
            "motion": random.choice(motions)
        })
        t += length

    return beats


# =========================
# 4. FAKE CAMERA MOTION
# =========================

def apply_camera_motion(clip, motion: str):
    """
    Áp chuyển động camera GIẢ cho clip.

    RẤT QUAN TRỌNG:
    - Không được zoom/pan mạnh
    - Mục tiêu là 'thở', không phải 'nhảy'
    """

    def frame_transform(get_frame, t):
        frame = get_frame(t)
        h, w = frame.shape[:2]

        # Mặc định không thay đổi
        scale = 1.0
        dx, dy = 0, 0

        if motion == "zoom_in":
            scale = 1.0 + ZOOM_INTENSITY * t
        elif motion == "zoom_out":
            scale = 1.0 - ZOOM_INTENSITY * t
        elif motion == "pan_left":
            dx = int(-PAN_INTENSITY * w * t)
        elif motion == "pan_right":
            dx = int(PAN_INTENSITY * w * t)

        # Resize nếu có zoom
        if scale != 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            frame = np.array(
                Image.fromarray(frame).resize(
                    (new_w, new_h),
                    Image.ANTIALIAS
                )
            )

            # Crop về kích thước cũ
            x = (new_w - w) // 2
            y = (new_h - h) // 2
            frame = frame[y:y+h, x:x+w]

        # Pan nhẹ bằng crop offset
        if dx != 0 or dy != 0:
            frame = np.roll(frame, dx, axis=1)

        return frame.astype("uint8")

    return clip.fl(frame_transform, apply_to=["mask"])


# =========================
# 5. GHÉP BEAT VÀO BACKGROUND
# =========================

def apply_beats_to_background(bg_clip, beats):
    """
    Cắt background theo beat và áp chuyển động tương ứng.

    WHY:
    - Mỗi 4–6s có thay đổi
    - Nhưng không cần đổi scene
    """
    segments = []

    for beat in beats:
        sub = bg_clip.subclip(beat["start"], beat["end"])
        animated = apply_camera_motion(sub, beat["motion"])
        segments.append(animated)

    return concatenate_videoclips(segments, method="compose")


# =========================
# 6. DEPTH LAYER CHO NHÂN VẬT
# =========================

def build_character_layer(char_img_path, duration, video_size):
    """
    Tạo nhân vật có chiều sâu giả (fake depth).

    CÁCH LÀM:
    - Duplicate layer
    - Layer dưới: blur + tối + lệch nhẹ
    - Layer trên: nét
    """

    char = (
        ImageClip(char_img_path)
        .set_duration(duration)
        .resize(height=int(video_size[1] * 0.85))
    )

    # Shadow layer (tạo cảm giác chiều sâu)
    shadow = (
        char
        .fx(vfx.blur, 25)
        .fx(vfx.colorx, 0.7)
        .set_position(lambda t: ("center", video_size[1] - char.h + 6))
    )

    # Nhân vật chính (drift cực nhẹ để tránh đứng chết)
    main = (
        char
        .set_position(lambda t: (
            "center",
            video_size[1] - char.h + int(np.sin(t) * CHAR_DRIFT_PX)
        ))
    )

    return CompositeVideoClip([shadow, main], size=video_size)


# =========================
# 7. AUDIO → EMOTION (NHẸ)
# =========================

def compute_audio_envelope(audio_clip):
    """
    Tính envelope âm thanh đơn giản.

    KHÔNG dùng để 'nhảy theo sóng',
    mà chỉ để hình ảnh 'thở' theo giọng.
    """
    samples = audio_clip.to_soundarray(fps=WAVEFORM_FPS)
    envelope = np.mean(np.abs(samples), axis=1)

    # Normalize an toàn
    envelope = envelope / (np.max(envelope) + 1e-6)
    return envelope


def emotion_opacity(envelope):
    """
    Trả về hàm opacity theo thời gian.
    """
    def opacity_at(t):
        idx = min(int(t * WAVEFORM_FPS), len(envelope) - 1)
        return 0.15 + envelope[idx] * 0.25
    return opacity_at


# =========================
# 8. MAIN PIPELINE
# =========================

def create_video(
    background_video,
    character_image,
    audio_path,
    output_path
):
    """
    Hàm chính – giữ signature đơn giản để
    không phá pipeline cũ.
    """

    # Load audio
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    # Load background
    bg = VideoFileClip(background_video).set_duration(duration)
    video_size = bg.size

    # Visual beats
    beats = generate_visual_beats(duration)
    bg_animated = apply_beats_to_background(bg, beats)

    # Character
    character_layer = build_character_layer(
        character_image,
        duration,
        video_size
    )

    # Audio envelope → ánh sáng cảm xúc
    envelope = compute_audio_envelope(audio)
    vignette = (
        ColorClip(video_size, color=(0, 0, 0))
        .set_duration(duration)
        .set_opacity(emotion_opacity(envelope))
    )

    # Final composite
    final = (
        CompositeVideoClip(
            [
                bg_animated,
                character_layer,
                vignette
            ],
            size=video_size
        )
        .set_audio(audio)
        .set_fps(OUTPUT_FPS)
    )

    # Render
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=2,              # GitHub Actions an toàn
        temp_audiofile="temp.m4a",
        remove_temp=True
    )


# =========================
# 9. ENTRY POINT (CLI)
# =========================

if __name__ == "__main__":
    create_video(
        background_video="background.mp4",
        character_image="character.png",
        audio_path="audio.wav",
        output_path="output.mp4"
    )
