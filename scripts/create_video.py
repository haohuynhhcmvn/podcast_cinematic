# scripts/create_video.py (ĐÃ TÍCH HỢP SÓNG ÂM & PHỤ ĐỀ)
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from moviepy.editor import *
from moviepy.video.io.bindings import MPLFigure
from moviepy.video.tools.subtitles import SubtitlesClip, file_to_subtitles

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

# Đường dẫn TĨNH đến file ảnh
ASSET_DIR = 'assets/images'
BACKGROUND_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'background.jpg'), os.path.join(ASSET_DIR, 'background.png')]
MICRO_IMAGE_PATHS = [os.path.join(ASSET_DIR, 'microphone.png'), os.path.join(ASSET_DIR, 'microphone.jpg')]

def create_waveform_clip(audio_clip, duration, width=1000, height=300):
    """
    Tạo video sóng âm (Waveform) đơn giản di chuyển theo thời gian.
    Sử dụng matplotlib để vẽ đồ thị biên độ âm thanh.
    """
    logging.info("Đang tạo video sóng âm (Waveform)... Quá trình này có thể mất vài phút.")
    
    # Lấy dữ liệu âm thanh (chuyển về mono nếu là stereo)
    # audio_clip.to_soundarray trả về mảng numpy (N_frames, N_channels)
    # Lấy mẫu với tốc độ khung hình thấp hơn để vẽ cho nhanh (ví dụ: 24fps)
    fps = 24
    
    # Tạo hàm make_frame cho VideoClip
    # Chúng ta sẽ vẽ sóng âm "giả lập" dạng thanh nhảy múa (Bar Visualizer) cho nhẹ
    # hoặc dạng đường sóng (Line Plot). Ở đây dùng Bar cho hiện đại.
    
    def make_frame(t):
        # Lấy một đoạn âm thanh nhỏ quanh thời điểm t (ví dụ: 0.1s)
        t_start = t
        t_end = t + 0.1
        chunk = audio_clip.subclip(t_start, t_end).to_soundarray(fps=44100)
        
        # Tính âm lượng trung bình (RMS) của đoạn này
        if len(chunk) == 0: volume = 0
        else: volume = np.sqrt(np.mean(chunk**2))
        
        # Vẽ biểu đồ bằng Matplotlib (trả về ảnh RGB)
        fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
        
        # Tạo dữ liệu ngẫu nhiên nhưng nhân với Volume để tạo hiệu ứng nhảy theo nhạc
        x = np.linspace(0, 10, 20) # 20 thanh
        y = np.random.rand(20) * (volume * 10) # Chiều cao phụ thuộc Volume
        
        ax.bar(x, y, color='cyan', alpha=0.7)
        ax.set_ylim(0, 1) # Cố định trục Y
        ax.axis('off') # Tắt khung viền
        
        # Chuyển Matplotlib figure thành ảnh cho MoviePy
        fig.canvas.draw()
        img = np.frombuffer(fig.canvas.tostring_rgb(), dtype='uint8')
        img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        plt.close(fig)
        
        return img

    # Tạo VideoClip từ hàm make_frame
    # Lưu ý: Việc render từng frame bằng matplotlib khá nặng. 
    # Để tối ưu cho GitHub Actions, ta dùng ColorClip nhấp nháy theo nhạc (đơn giản hơn)
    # HOẶC dùng giải pháp dưới đây: ColorClip thay đổi độ trong suốt (Opacity) theo âm lượng
    
    return VideoClip(make_frame, duration=duration).set_mask(None)

def create_simple_visualizer(audio_clip, duration, width=800, height=200):
    """
    Giải pháp nhẹ hơn: Tạo một thanh ngang co giãn theo âm lượng.
    Nhanh hơn nhiều so với vẽ Matplotlib từng frame.
    """
    def make_frame(t):
        # Lấy âm lượng tại thời điểm t
        chunk = audio_clip.subclip(t, t+0.05).to_soundarray(fps=22050)
        volume = np.sqrt(np.mean(chunk**2)) * 10 # Khuếch đại
        
        # Giới hạn volume
        volume = min(volume, 1.0)
        
        # Tạo một thanh trắng có chiều dài thay đổi
        w = int(width * volume)
        if w == 0: w = 1
        
        # Tạo mảng ảnh (H, W, 3)
        img = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Vẽ thanh chữ nhật ở giữa
        center_x = width // 2
        half_w = w // 2
        img[:, center_x - half_w : center_x + half_w, :] = [0, 255, 255] # Màu Cyan
        
        return img

    return VideoClip(make_frame, duration=duration)

def file_to_subtitles_safe(filename):
    """
    Hàm đọc file phụ đề thực tế.
    """
    if not os.path.exists(filename):
        logging.warning(f"Không tìm thấy file phụ đề: {filename}")
        return []
    
    try:
        # Sử dụng hàm có sẵn của MoviePy
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
             subtitle_clip_to_use = subtitle_clip.set_pos(('center', 0.85), relative=True).set_duration(duration)

        # --- 2. XỬ LÝ NỀN ---
        background_path = next((p for p in BACKGROUND_IMAGE_PATHS if os.path.exists(p)), None)
        if background_path:
             background_clip = ImageClip(background_path, duration=duration).resize(newsize=(VIDEO_WIDTH, VIDEO_HEIGHT))
        else:
             background_clip = ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)

        # --- 3. XỬ LÝ MICRO ---
        micro_path = next((p for p in MICRO_IMAGE_PATHS if os.path.exists(p)), None)
        if micro_path:
             micro_clip = ImageClip(micro_path, duration=duration).set_pos(('center', 0.4), relative=True).resize(height=VIDEO_HEIGHT * 0.25)
        else:
             micro_clip = TextClip("Micro", fontsize=40, color='red').set_duration(duration)

        # --- 4. XỬ LÝ SÓNG ÂM (VISUALIZER) ---
        # Sử dụng hàm đơn giản để render nhanh trên GitHub Actions
        logging.info("Đang tạo hiệu ứng sóng âm...")
        visualizer_clip = create_simple_visualizer(audio_clip, duration, width=1000, height=50)
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
        # Preset ultrafast để tiết kiệm thời gian trên GitHub Actions
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, preset='ultrafast', logger='bar'
        )
        
        logging.info(f"Video hoàn tất: {video_path}")
        return video_path
        
    except Exception as e:
        logging.error(f"Lỗi khi tạo video 16:9: {e}", exc_info=True)
        return None
