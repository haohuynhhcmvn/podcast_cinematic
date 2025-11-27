# scripts/create_shorts.py (ĐÃ SỬA: Cải thiện sóng âm - Spectrum Analyzer Style)
import os
import logging
from moviepy.editor import *
import math 
import random # Cần để tạo độ ngẫu nhiên cho nhịp điệu

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
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
        clip = ImageClip(image_path).set_duration(duration)
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

# --- HÀM TẠO VISUALIZER ĐA THANH MỚI (Cải tiến - Giống create_video.py) ---
def create_multi_bar_visualizer(duration, container_width, container_max_height, base_color):
    NUM_BARS = 60 
    BAR_WIDTH = 3
    BAR_SPACING = 3
    
    random.seed(42) 
    bar_configs = []
    for _ in range(NUM_BARS):
        bar_configs.append({
            'pulse_speed_mult': random.uniform(0.8, 1.2), 
            'phase_offset': random.uniform(0, 2 * math.pi), 
            'min_height_ratio': random.uniform(0.1, 0.3) 
        })
    
    bar_clips = []
    
    total_bar_width = NUM_BARS * (BAR_WIDTH + BAR_SPACING) - BAR_SPACING
    start_x = (container_width - total_bar_width) / 2 

    for i in range(NUM_BARS):
        config = bar_configs[i]
        
        base_bar = ColorClip((BAR_WIDTH, 1), color=base_color).set_duration(duration)

        def get_bar_properties(t, index=i, conf=config):
            oscillation = 0.5 * (1 + math.sin(t * 8 * conf['pulse_speed_mult'] + conf['phase_offset']))
            current_height = max(1, int(container_max_height * (conf['min_height_ratio'] + (1 - conf['min_height_ratio']) * oscillation)))
            opacity = 0.5 + 0.5 * oscillation 
            return current_height, opacity
        
        animated_bar = base_bar.fx(vfx.resize, height=lambda t: get_bar_properties(t, i, config)[0])
        animated_bar = animated_bar.fx(vfx.set_opacity, lambda t: get_bar_properties(t, i, config)[1])
        
        x_pos = start_x + i * (BAR_WIDTH + BAR_SPACING)
        
        def get_bar_pos(t, index=i, conf=config):
            current_height, _ = get_bar_properties(t, index, conf)
            y_pos = container_max_height - current_height
            return (x_pos, y_pos)

        bar_clips.append(animated_bar.set_pos(get_bar_pos))

    return CompositeVideoClip(bar_clips, size=(container_width, container_max_height)).set_duration(duration)
# --- KẾT THÚC HÀM TẠO VISUALIZER ĐA THANH ---


def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        MAX_SHORTS_DURATION = 60 
        if duration > MAX_SHORTS_DURATION:
            audio_clip = audio_clip.subclip(0, MAX_SHORTS_DURATION)
            duration = MAX_SHORTS_DURATION
        
        logging.warning("BỎ QUA PHỤ ĐỀ cho video Shorts để hoàn thành pipeline.")
        subtitle_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)

        # Tải nền
        background_clip = load_asset_image('default_background_shorts.png', width=SHORTS_WIDTH, height=SHORTS_HEIGHT, duration=duration)
        if not background_clip:
            background_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
            
        # Tải micro
        microphone_clip = load_asset_image('microphone.png', width=int(SHORTS_WIDTH * 0.3), duration=duration, position=("center", SHORTS_HEIGHT // 2 + 150))
        
        # XỬ LÝ NỀN MICROPHONE (Bỏ comment nếu ảnh gốc có nền đen và bạn muốn xóa)
        # if microphone_clip:
        #     microphone_clip = microphone_clip.fx(vfx.mask_color, color=[0, 0, 0], s=50) 
        
        # Tiêu đề
        title_text = TextClip(f"PODCAST: {episode_id}", fontsize=80, color='yellow', font='sans-bold', size=(SHORTS_WIDTH * 0.9, None), bg_color='black')
        title_text = title_text.set_duration(duration).set_pos(('center', SHORTS_HEIGHT * 0.1))

        # --- SÓNG ÂM MỚI ---
        WAVE_COLOR = (240, 240, 240) # Màu trắng ngà cho sóng âm
        WAVE_WIDTH = int(SHORTS_WIDTH * 0.7)
        WAVE_MAX_HEIGHT = int(SHORTS_HEIGHT * 0.08) 

        waveform_clip = create_multi_bar_visualizer(
            duration,
            WAVE_WIDTH,
            WAVE_MAX_HEIGHT,
            WAVE_COLOR
        )
        waveform_clip = waveform_clip.set_pos(("center", SHORTS_HEIGHT * 0.45))
        
        # Ghép các thành phần
        elements = [background_clip, title_text, waveform_clip, subtitle_clip.set_duration(duration).set_pos(('center', 'bottom')).margin(bottom=50)]
        if microphone_clip:
            elements.insert(1, microphone_clip)

        final_clip = CompositeVideoClip(elements, size=(SHORTS_WIDTH, SHORTS_HEIGHT)).set_audio(audio_clip)

        # Xuất Video (giữ nguyên)
        output_dir = os.path.join('outputs', 'shorts')
        video_filename = f"{episode_id}_shorts_916.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu xuất Video Shorts 9:16...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, logger='bar'
        )
        
        logging.info(f"Video Shorts 9:16 đã tạo thành công và lưu tại: {video_path}")
        return video_path 

    except Exception as e:
        logging.error(f"Lỗi khi tạo video Shorts: {e}", exc_info=True)
        return None
