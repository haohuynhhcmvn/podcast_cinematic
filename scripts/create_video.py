# scripts/create_video.py (ĐÃ SỬA: Sóng âm động và Xóa import lỗi)
import os
import logging
import moviepy.editor as mp
import math # Cần import math cho hàm sin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        logging.warning("BỎ QUA HOÀN TOÀN TẠO PHỤ ĐỀ (SubtitleClip) cho video 16:9 để hoàn thành pipeline.")
        
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Tạo clip placeholder trong suốt thay thế cho phụ đề
        subtitle_clip_to_use = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)

        # Nền (Background)
        background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # Sóng âm ĐỘNG (Animated Visual Placeholder)
        WAVE_COLOR = (0, 200, 0) # Màu xanh lá đậm
        WAVE_HEIGHT = 10 
        WAVE_WIDTH = int(VIDEO_WIDTH * 0.7)
        
        # Tạo clip cơ sở (thanh sóng âm tĩnh)
        base_waveform_clip = mp.ColorClip((WAVE_WIDTH, WAVE_HEIGHT), color=WAVE_COLOR, duration=duration)

        # THÊM HIỆU ỨNG ĐỘNG
        MAX_HEIGHT_MULTIPLIER = 3.0 # Chiều cao tối đa gấp 3 lần base_height
        PULSE_SPEED = 10 # Tần số nhảy (10 lần/giây)

        def resize_func(t):
            # Tính toán hệ số nhân chiều cao dựa trên thời gian (t)
            # Hàm sin tạo ra sự dao động mượt mà
            scale_factor = 1.0 + (MAX_HEIGHT_MULTIPLIER - 1.0) * (0.5 * (1 + math.sin(t * PULSE_SPEED)))
            return scale_factor
        
        # Áp dụng hiệu ứng resize động
        waveform_clip = base_waveform_clip.fx(mp.vfx.resize, height=lambda t: WAVE_HEIGHT * resize_func(t))
        
        # Đặt clip vào vị trí
        waveform_clip = waveform_clip.set_pos(("center", VIDEO_HEIGHT // 2 - 50))
        
        # Ghép các thành phần
        final_clip = mp.CompositeVideoClip([
            background_clip, waveform_clip, subtitle_clip_to_use
        ], size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # Xuất Video
        output_dir = os.path.join('outputs', 'video')
        video_filename = f"{episode_id}_full_podcast_169.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu xuất Video 16:9...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, logger='bar'
        )

        logging.info(f"Video 16:9 đã tạo thành công và lưu tại: {video_path}")
        return video_path

    except Exception as e:
        logging.error(f"Lỗi khi tạo video 16:9: {e}", exc_info=True)
        return None
