# scripts/create_video.py (ĐÃ SỬA LỖI IMPORT - CHỈ DÙNG NUMPY CHO SÓNG ÂM)
import os
import logging
import numpy as np
# Đã xóa import matplotlib để tránh lỗi ImportError
from moviepy.editor import *
# Đã xóa import MPLFigure vì không dùng đến
from moviepy.video.tools.subtitles import SubtitlesClip, file_to_subtitles

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

# Đường dẫn TĨNH đến file ảnh
ASSET_DIR = 'assets/images'
BACKGROUND_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'background.jpg'), os.path.join(ASSET_DIR, 'background.png')]
MICRO_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'microphone.png'), os.path.join(ASSET_DIR, 'microphone.jpg')]

def create_simple_visualizer(audio_clip, duration, width=800, height=200):
    """
    Tạo hiệu ứng sóng âm đơn giản bằng Numpy (Nhanh, Nhẹ, Không cần Matplotlib).
    Tạo ra một thanh ngang co giãn theo âm lượng.
    """
    def make_frame(t):
        # Lấy âm lượng tại thời điểm t
        t_end = min(t + 0.05, duration) # Đảm bảo không vượt quá duration
        chunk = audio_clip.subclip(t, t_end).to_soundarray(fps=22050)
        
        if len(chunk) == 0: 
            volume = 0
        else:
            # Tính RMS (Root Mean Square)
            volume = np.sqrt(np.mean(chunk**2)) * 10 
        
        # Giới hạn volume
        volume = min(volume, 1.0)
        
        # Tạo một thanh trắng có chiều dài thay đổi
        w = int(width * volume)
        if w <= 0: w = 1
        
        # Tạo mảng ảnh (H, W, 3) - nền trong suốt (hoặc đen nếu MoviePy không hỗ trợ Alpha tốt ở đây)
        # Ở đây ta tạo nền đen hoàn toàn (0,0,0) sau đó dùng ColorClip đè lên hoặc set_opacity
        img = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Vẽ thanh chữ nhật màu Cyan (Xanh lơ) ở giữa
        center_x = width // 2
        half_w = w // 2
        
        # Đảm bảo index không vượt quá giới hạn
        x1 = max(0, center_x - half_w)
        x2 = min(width, center_x + half_w)
        
        # Tô màu [0, 255, 255] (Cyan)
        img[:, x1:x2, :] = [0, 255, 255] 
        
        return img

    # Tạo VideoClip từ hàm make_frame
    return VideoClip(make_frame, duration=duration)

def file_to_subtitles_safe(filename):
    """
    Hàm đọc file phụ đề thực tế.
    """
    if not os.path.exists(filename):
        logging.warning(f"Không tìm thấy file phụ đề: {filename}")
        return []
    
    try:
        return file_to_subtitles(filename)
    except Exception as e:
        logging.error(f"Lỗi đọc phụ đề: {e}")
        return []

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        logging.info("Đang xử lý Audio...")
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # --- 1. XỬ LÝ PHỤ ĐỀ ---
        generator = lambda txt: TextClip(txt, fontsize=55, color='white', font='Arial-Bold',
                                         stroke_color='black', stroke_width=2, method='caption', 
                                         size=(VIDEO_WIDTH*0.8, None), align='center')
        
        subtitles_data = file_to_subtitles_safe(subtitle_path)
        
        if not subtitles_data:
             logging.info("Không có phụ đề. Tạo layer rỗng.")
             subtitle_clip_to_use = ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0,0,0), duration=duration).set_opacity(0)
        else:
             logging.info("Đang tạo SubtitlesClip...")
             subtitle_clip = SubtitlesClip(subtitles_data, generator)
             # Căn chỉnh vị trí phụ đề
             subtitle_clip_to_use = subtitle_clip.set_pos(('center', 0.85), relative=True).set_duration(duration)

        # --- 2. XỬ LÝ NỀN ---
        background_path = next((p for p in BACKGROUND_IMAGE_PATHS if os.path.exists(p)), None)
        if background_path:
             logging.info(f"Sử dụng ảnh nền từ: {background_path}")
             background_clip = ImageClip(background_path, duration=duration).resize(newsize=(VIDEO_WIDTH, VIDEO_HEIGHT))
        else:
             logging.warning("Không tìm thấy ảnh nền. Sử dụng nền đen.")
             background_clip = ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)

        # --- 3. XỬ LÝ MICRO ---
        micro_path = next((p for p in MICRO_IMAGE_PATHS if os.path.exists(p)), None)
        if micro_path:
             micro_clip = ImageClip(micro_path, duration=duration).set_pos(('center', 0.4), relative=True).resize(height=VIDEO_HEIGHT * 0.25)
        else:
             micro_clip = TextClip("Micro", fontsize=40, color='red').set_duration(duration)

        # --- 4. XỬ LÝ SÓNG ÂM (VISUALIZER - Dùng Numpy) ---
        logging.info("Đang tạo hiệu ứng sóng âm (Visualizer)...")
        # Tạo visualizer với chiều rộng 1000px, cao 50px
        visualizer_clip = create_simple_visualizer(audio_clip, duration, width=1000, height=50)
        # Đặt vị trí dưới Micro
        visualizer_clip = visualizer_clip.set_pos(('center', 0.65), relative=True).set_opacity(0.8)
        
        # --- 5. GHÉP ---
        logging.info("Đang ghép các layer...")
        final_clip = CompositeVideoClip([
            background_clip, 
            micro_clip, 
            visualizer_clip, # Layer sóng âm mới
            subtitle_clip_to_use
        ], size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # Xuất Video
        output_dir = os.path.join('outputs', 'video')
        os.makedirs(output_dir, exist_ok=True)
        video_filename = f"{episode_id}_full_podcast_169.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu render Video 16:9...")
        # Preset ultrafast để tiết kiệm thời gian
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, preset='ultrafast', logger='bar'
        )
        
        logging.info(f"Video hoàn tất: {video_path}")
        return video_path
        
    except Exception as e:
        logging.error(f"Lỗi khi tạo video 16:9: {e}", exc_info=True)
        return None
