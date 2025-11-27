# scripts/create_shorts.py (ĐÃ TÍCH HỢP SÓNG ÂM ĐỘNG & PHỤ ĐỀ)
import os
import logging
import numpy as np
from moviepy.editor import *
from moviepy.video.tools.subtitles import SubtitlesClip, file_to_subtitles 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) 

# Đường dẫn TĨNH đến file ảnh
ASSET_DIR = 'assets/images'
BACKGROUND_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'background.jpg'), os.path.join(ASSET_DIR, 'background.png')]
MICRO_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'microphone.png'), os.path.join(ASSET_DIR, 'microphone.jpg')]

# --- HÀM TẠO SÓNG ÂM (TÁI SỬ DỤNG LOGIC TỪ CREATE_VIDEO) ---
def create_simple_visualizer(audio_clip, duration, width=800, height=40):
    """
    Tạo hiệu ứng sóng âm đơn giản bằng Numpy (Nhanh, Nhẹ).
    Sóng âm sẽ là một thanh ngang co giãn theo âm lượng.
    """
    def make_frame(t):
        t_end = min(t + 0.05, duration) 
        try:
            chunk = audio_clip.subclip(t, t_end).to_soundarray(fps=22050)
            if len(chunk) == 0: 
                volume = 0
            else:
                volume = np.sqrt(np.mean(chunk**2)) * 15 # Khuếch đại
        except:
            volume = 0
        
        volume = min(volume, 1.0)
        current_width = int(width * volume)
        if current_width <= 0: current_width = 1
        
        img = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Vẽ thanh chữ nhật màu Cyan [0, 255, 255] ở giữa
        center_x = width // 2
        half_w = current_width // 2
        
        x1 = max(0, center_x - half_w)
        x2 = min(width, center_x + half_w)
        
        img[:, x1:x2, :] = [0, 255, 255] # Màu Cyan
        
        return img

    return VideoClip(make_frame, duration=duration)

# --- HÀM ĐỌC SUBTITLE (TÁI SỬ DỤNG LOGIC TỪ CREATE_VIDEO) ---
def file_to_subtitles_safe(filename):
    if not os.path.exists(filename):
        logging.warning(f"Không tìm thấy file phụ đề: {filename}")
        return []
    try:
        # Kích hoạt lại hàm đọc phụ đề của MoviePy
        return file_to_subtitles(filename)
    except Exception as e:
        logging.error(f"Lỗi đọc phụ đề: {e}")
        return []

def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # --- 1. XỬ LÝ PHỤ ĐỀ (SUBTITLES) ---
        generator = lambda txt: TextClip(txt, fontsize=70, color='white', font='Arial-Bold',
                                         stroke_color='black', stroke_width=3, method='caption', 
                                         size=(SHORTS_WIDTH*0.9, None), align='center')
        
        subtitles_data = file_to_subtitles_safe(subtitle_path)
        
        if not subtitles_data:
             logging.warning("Không có phụ đề. Shorts sẽ không có phụ đề.")
             subtitle_clip_to_use = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=(0,0,0), duration=duration).set_opacity(0)
        else:
             logging.info("Đang tạo SubtitlesClip cho Shorts...")
             subtitle_clip = SubtitlesClip(subtitles_data, generator)
             # Đặt phụ đề ở vị trí 75% chiều cao
             subtitle_clip_to_use = subtitle_clip.set_pos(('center', 0.75), relative=True).set_duration(duration)

        # --- 2. XỬ LÝ NỀN ---
        background_path = next((p for p in BACKGROUND_IMAGE_PATHS if os.path.exists(p)), None)
        if background_path:
             background_clip = ImageClip(background_path, duration=duration).resize(newsize=(SHORTS_WIDTH, SHORTS_HEIGHT))
        else:
             background_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # --- 3. TIÊU ĐỀ/CHỦ ĐỀ ---
        title_text = TextClip(f"PODCAST: {episode_id}", fontsize=80, color='yellow', font='Arial-Bold', 
                              size=(SHORTS_WIDTH * 0.9, None), bg_color='black')
        title_text = title_text.set_duration(duration).set_pos(('center', 0.05), relative=True)

        # --- 4. XỬ LÝ MICRO ---
        micro_path = next((p for p in MICRO_IMAGE_PATHS if os.path.exists(p)), None)
        if micro_path:
             micro_clip = ImageClip(micro_path, duration=duration).set_pos(('center', 0.4), relative=True).resize(height=SHORTS_HEIGHT * 0.20)
        else:
             micro_clip = TextClip("Micro Placeholder", fontsize=40, color='red').set_duration(duration)

        # --- 5. XỬ LÝ SÓNG ÂM (VISUALIZER) ---
        logging.info("Đang tạo hiệu ứng sóng âm (Visualizer) cho Shorts...")
        visualizer_clip = create_simple_visualizer(audio_clip, duration, width=800, height=40)
        visualizer_clip = visualizer_clip.set_pos(('center', 0.65), relative=True).set_opacity(0.8)
        
        # --- 6. GHÉP ---
        final_clip = CompositeVideoClip([
            background_clip, 
            title_text, 
            micro_clip, 
            visualizer_clip,
            subtitle_clip_to_use
        ], size=(SHORTS_WIDTH, SHORTS_HEIGHT)).set_audio(audio_clip)

        # Xuất Video
        output_dir = os.path.join('outputs', 'shorts')
        os.makedirs(output_dir, exist_ok=True)
        video_filename = f"{episode_id}_shorts_916.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu render Video Shorts 9:16...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, preset='ultrafast', threads=4, logger='bar'
        )
        
        logging.info(f"Video Shorts 9:16 đã tạo thành công và lưu tại: {video_path}")
        return video_path

    except Exception as e:
        logging.error(f"Lỗi khi tạo video Shorts 9:16: {e}", exc_info=True)
        return None
