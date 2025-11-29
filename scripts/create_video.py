# scripts/create_video.py
import os
import logging
import moviepy.editor as mp
import math
import numpy as np 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30) 

# --- HÀM TẢI VIDEO LẶP NỀN ---
def load_looping_background_video(file_name, target_duration, width, height):
    """
    Tải video nền, đảm bảo video lặp lại liên tục cho đến khi đạt được target_duration.
    """
    video_path = os.path.join('assets', 'video', file_name)
    if not os.path.exists(video_path):
        logging.warning(f"Không tìm thấy video nền tại: {video_path}. Sẽ dùng nền màu tĩnh.")
        return mp.ColorClip((width, height), color=COLOR_BACKGROUND, duration=target_duration)

    try:
        # Tải video gốc
        original_clip = mp.VideoFileClip(video_path)
        
        # Nếu video gốc đã dài hơn thời lượng mục tiêu, chỉ cần cắt
        if original_clip.duration >= target_duration:
            clip = original_clip.subclip(0, target_duration)
        else:
            # Tính toán số lần lặp cần thiết
            num_loops = math.ceil(target_duration / original_clip.duration)
            # Tạo danh sách các clip lặp lại và nối lại
            looped_clips = [original_clip] * num_loops
            final_loop = mp.concatenate_videoclips(looped_clips)
            clip = final_loop.subclip(0, target_duration)
        
        # Đảm bảo clip được resize để vừa với khung hình mục tiêu
        clip = clip.resize(newsize=(width, height))

        logging.info(f"Đã tạo video nền lặp thành công. Độ dài: {clip.duration:.2f}s")
        return clip

    except Exception as e:
        logging.error(f"Lỗi khi tải hoặc lặp video nền {video_path}: {e}")
        return mp.ColorClip((width, height), color=COLOR_BACKGROUND, duration=target_duration)

# --- HÀM CREATE_VIDEO CHÍNH ---
def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # --- 1. Tải Nền Dạng Video Lặp (LONG) ---
        background_clip = load_looping_background_video('podcast_loop_bg_long.mp4', duration, VIDEO_WIDTH, VIDEO_HEIGHT)
        
        # --- 2. Tạo Sóng Âm (Waveform Visualization) ---
        # TẠM THỜI TẠO WAVEFORM GIẢ
        wave_visualization_clip = mp.ImageClip(os.path.join('assets', 'images', 'default_waveform_placeholder.png')).set_duration(duration).set_pos(('center', 'center')).resize(width=VIDEO_WIDTH * 0.8)


        # --- 3. Tải Micro/Avatar ---
        microphone_clip = mp.ImageClip(os.path.join('assets', 'images', 'microphone.png')).set_duration(duration).set_pos(("center", VIDEO_HEIGHT * 0.75)).resize(width=VIDEO_WIDTH * 0.15)
        
        # --- 4. Tải Phụ đề (GIỮ CHỖ) ---
        subtitle_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)


        # --- 5. Ghép các thành phần ---
        elements = [
            background_clip, 
            wave_visualization_clip,
            microphone_clip, 
            subtitle_clip
        ]

        final_clip = mp.CompositeVideoClip(elements, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # --- 6. Xuất Video ---
        output_dir = os.path.join('outputs', 'video')
        os.makedirs(output_dir, exist_ok=True)
        video_filename = f"{episode_id}_full_podcast_169.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu xuất Video DÀI 16:9...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, logger='bar'
        )
        
        logging.info(f"Video DÀI 16:9 đã tạo thành công và lưu tại: {video_path}")
        return video_path 

    except Exception as e:
        logging.error(f"Lỗi khi tạo video DÀI: {e}", exc_info=True)
        return None
