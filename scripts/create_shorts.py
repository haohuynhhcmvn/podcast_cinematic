# scripts/create_shorts.py (ĐÃ SỬA: Nâng cấp sóng âm thành Multi-Bar EQ Visualizer)
import os
import logging
from moviepy.editor import *
import math 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SHORTS_WIDTH = 1080
SHORTS_HEIGHT = 1920
COLOR_BACKGROUND = (30, 30, 30) 

# --- HÀM TẢI ẢNH AN TOÀN (GIỮ NGUYÊN) ---
def load_asset_image(file_name, width=None, height=None, duration=None, position=('center', 'center')):
    """Tải ảnh, resize và đặt vị trí an toàn."""
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

# --- HÀM TẠO VISUALIZER ĐA THANH MỚI (GIỐNG create_video.py) ---
def create_multi_bar_visualizer(duration, container_width, container_max_height, color):
    NUM_BARS = 20
    BAR_WIDTH = 10
    BAR_SPACING = 5
    PULSE_SPEED = 8 
    
    bar_clips = []
    
    total_bar_width = NUM_BARS * (BAR_WIDTH + BAR_SPACING) - BAR_SPACING
    start_x = (container_width - total_bar_width) / 2 

    for i in range(NUM_BARS):
        base_bar = ColorClip((BAR_WIDTH, 5), color=color).set_duration(duration)

        def get_bar_height(t, index=i):
            phase_offset = index * 0.5
            freq_mult = 1 + (index % 5) * 0.1
            
            height_mult = 0.5 + 0.5 * math.sin(t * PULSE_SPEED * freq_mult + phase_offset)
            
            return max(5, int(container_max_height * height_mult))
        
        animated_bar = base_bar.fx(vfx.resize, height=get_bar_height)
        
        x_pos = start_x + i * (BAR_WIDTH + BAR_SPACING)
        
        def get_bar_pos(t, index=i):
            current_height = get_bar_height(t, index)
            y_pos = container_max_height - current_height
            return (x_pos, y_pos)

        bar_clips.append(animated_bar.set_pos(get_bar_pos))

    return CompositeVideoClip(bar_clips, size=(container_width, container_max_height)).set_duration(duration)
# --- KẾT THÚC HÀM TẠO VISUALIZER ĐA THANH ---


def create_shorts(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        audio_clip = AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # ... (Logic giới hạn thời lượng và phụ đề giữ nguyên)
        MAX_SHORTS_DURATION = 60 
        
        if duration > MAX_SHORTS_DURATION:
            audio_clip = audio_clip.subclip(0, MAX_SHORTS_DURATION)
            duration = MAX_SHORTS_DURATION
        
        logging.warning("BỎ QUA PHỤ ĐỀ cho video Shorts để hoàn thành pipeline.")
        subtitle_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)

        # Tải nền và micro
        background_clip = load_asset_image('default_background_shorts.png', width=SHORTS_WIDTH, height=SHORTS_HEIGHT, duration=duration)
        if not background_clip:
            background_clip = ColorClip((SHORTS_WIDTH, SHORTS_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
            
        microphone_clip = load_asset_image('microphone.png', width=int(SHORTS_WIDTH * 0.3), duration=duration, position=("center", SHORTS_HEIGHT // 2 + 150))
        
        # Tiêu đề
        title_text = TextClip(f"PODCAST: {episode_id}", fontsize=80, color='yellow', font='sans-bold', size=(SHORTS_WIDTH * 0.9, None), bg_color='black')
        title_text = title_text.set_duration(duration).set_pos(('center', SHORTS_HEIGHT * 0.1))

        # --- TẠO SÓNG ÂM ĐA THANH MỚI ---
        WAVE_COLOR = (0, 200, 0)
        WAVE_WIDTH = int(SHORTS_WIDTH * 0.7)
        WAVE_MAX_HEIGHT = int(SHORTS_HEIGHT * 0.08) # Chiều cao tối đa container cho Shorts

        waveform_clip = create_multi_bar_visualizer(
            duration,
            WAVE_WIDTH,
            WAVE_MAX_HEIGHT,
            WAVE_COLOR
        )
        # Đặt toàn bộ Visualizer vào vị trí
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
