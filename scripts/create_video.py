# scripts/create_video.py (ĐÃ SỬA: Cải thiện sóng âm - Spectrum Analyzer Style)
import os
import logging
import moviepy.editor as mp
import math
import random # Cần để tạo độ ngẫu nhiên cho nhịp điệu

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30) 

# --- HÀM TẢI ẢNH AN TOÀN (GIỮ NGUYÊN) ---
def load_asset_image(file_name, width=None, height=None, duration=None, position=('center', 'center')):
    paths_to_check = [
        os.path.join('assets', 'images', file_name), 
        os.path.join('assets', 'image', file_name)
    ]
    image_path = None
    for path in paths_to_check:
        if os.path.exists(path):
            image_path = path
            break
            
    if not image_path:
        logging.warning(f"Không tìm thấy file ảnh: {file_name} trong cả assets/images và assets/image. Trả về None.")
        return None

    try:
        clip = mp.ImageClip(image_path).set_duration(duration)
        if width and height:
            clip = clip.resize(newsize=(width, height))
        elif width:
            clip = clip.resize(width=width)
        elif height:
            clip = clip.resize(height=height)
        return clip.set_pos(position)
    except Exception as e:
        logging.error(f"Lỗi khi tải hoặc resize ảnh {image_path}: {e}")
        return None
# --- KẾT THÚC HÀM TẢI ẢNH AN TOÀN ---

# --- HÀM TẠO VISUALIZER ĐA THANH MỚI (Cải tiến) ---
def create_multi_bar_visualizer(duration, container_width, container_max_height, base_color):
    NUM_BARS = 60 # Tăng số lượng thanh để trông dày đặc hơn
    BAR_WIDTH = 3
    BAR_SPACING = 3
    
    # Random seeds cho mỗi thanh để tạo sự ngẫu nhiên trong chuyển động
    random.seed(42) # Để đảm bảo kết quả nhất quán giữa các lần chạy
    bar_configs = []
    for _ in range(NUM_BARS):
        bar_configs.append({
            'pulse_speed_mult': random.uniform(0.8, 1.2), # Tốc độ nhấp nháy khác nhau
            'phase_offset': random.uniform(0, 2 * math.pi), # Pha ngẫu nhiên
            'min_height_ratio': random.uniform(0.1, 0.3) # Tỷ lệ chiều cao tối thiểu
        })
    
    bar_clips = []
    
    # Tính toán vị trí X để căn giữa
    total_bar_width = NUM_BARS * (BAR_WIDTH + BAR_SPACING) - BAR_SPACING
    start_x = (container_width - total_bar_width) / 2 

    for i in range(NUM_BARS):
        config = bar_configs[i]
        
        # 1. Clip cơ sở (sử dụng chiều cao tối thiểu 1px)
        base_bar = mp.ColorClip((BAR_WIDTH, 1), color=base_color).set_duration(duration)

        # 2. Hàm tính toán Chiều cao và Độ trong suốt theo thời gian (t)
        def get_bar_properties(t, index=i, conf=config):
            # Biến đổi giá trị sin từ [-1, 1] về [0, 1]
            oscillation = 0.5 * (1 + math.sin(t * 8 * conf['pulse_speed_mult'] + conf['phase_offset']))
            
            # Chiều cao: từ min_height_ratio đến full height
            current_height = max(1, int(container_max_height * (conf['min_height_ratio'] + (1 - conf['min_height_ratio']) * oscillation)))
            
            # Độ trong suốt: Tăng khi thanh nhảy cao, giảm khi thấp
            # Giúp tạo hiệu ứng "glow" hoặc "mờ" khi thanh thấp
            opacity = 0.5 + 0.5 * oscillation # Từ 0.5 đến 1.0
            
            return current_height, opacity
        
        # 3. Áp dụng Resize (Chiều cao) và Độ trong suốt
        animated_bar = base_bar.fx(mp.vfx.resize, height=lambda t: get_bar_properties(t, i, config)[0])
        animated_bar = animated_bar.fx(mp.vfx.set_opacity, lambda t: get_bar_properties(t, i, config)[1])
        
        # 4. Hàm tính toán Vị trí Y (để neo thanh vào đáy container)
        x_pos = start_x + i * (BAR_WIDTH + BAR_SPACING)
        
        def get_bar_pos(t, index=i, conf=config):
            current_height, _ = get_bar_properties(t, index, conf)
            y_pos = container_max_height - current_height # Neo vào đáy
            return (x_pos, y_pos)

        bar_clips.append(animated_bar.set_pos(get_bar_pos))

    # 5. Ghép các thanh lại thành Composite Clip
    return mp.CompositeVideoClip(bar_clips, size=(container_width, container_max_height)).set_duration(duration)
# --- KẾT THÚC HÀM TẠO VISUALIZER ĐA THANH ---


def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        logging.warning("BỎ QUA HOÀN TOÀN TẠO PHỤ ĐỀ (SubtitleClip) cho video 16:9 để hoàn thành pipeline.")
        
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        subtitle_clip_to_use = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)

        # Tải nền
        background_clip = load_asset_image('default_background.png', width=VIDEO_WIDTH, height=VIDEO_HEIGHT, duration=duration)
        if not background_clip:
            background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
            
        # Tải micro
        microphone_clip = load_asset_image('microphone.png', width=int(VIDEO_WIDTH * 0.2), duration=duration, position=("center", VIDEO_HEIGHT // 2 + 50))
        
        # XỬ LÝ NỀN MICROPHONE (Bỏ comment nếu ảnh gốc có nền đen và bạn muốn xóa)
        # if microphone_clip:
        #     microphone_clip = microphone_clip.fx(mp.vfx.mask_color, color=[0, 0, 0], s=50) 
        
        # --- SÓNG ÂM MỚI ---
        WAVE_COLOR = (240, 240, 240) # Màu trắng ngà cho sóng âm
        WAVE_WIDTH = int(VIDEO_WIDTH * 0.7)
        WAVE_MAX_HEIGHT = int(VIDEO_HEIGHT * 0.1) 

        waveform_clip = create_multi_bar_visualizer(
            duration,
            WAVE_WIDTH,
            WAVE_MAX_HEIGHT,
            WAVE_COLOR
        )
        waveform_clip = waveform_clip.set_pos(("center", VIDEO_HEIGHT // 2 - 50))
        
        # Ghép các thành phần
        elements = [background_clip, waveform_clip, subtitle_clip_to_use]
        if microphone_clip:
            elements.insert(1, microphone_clip)

        final_clip = mp.CompositeVideoClip(elements, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # Xuất Video (giữ nguyên)
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
