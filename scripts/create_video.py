# scripts/create_video.py (ĐÃ SỬA: Nâng cấp sóng âm thành Multi-Bar EQ Visualizer)
import os
import logging
import moviepy.editor as mp
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30) 
MICROPHONE_IMAGE_PATH = os.path.join('assets', 'images', 'microphone.png') 
BACKGROUND_IMAGE_DEFAULT_PATH = os.path.join('assets', 'images', 'default_background.png') 

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

# --- HÀM TẠO VISUALIZER ĐA THANH MỚI ---
def create_multi_bar_visualizer(duration, container_width, container_max_height, color):
    NUM_BARS = 20
    BAR_WIDTH = 10
    BAR_SPACING = 5
    PULSE_SPEED = 8 # Tốc độ cơ sở
    
    bar_clips = []
    
    # Tính toán vị trí X để căn giữa
    total_bar_width = NUM_BARS * (BAR_WIDTH + BAR_SPACING) - BAR_SPACING
    start_x = (container_width - total_bar_width) / 2 

    for i in range(NUM_BARS):
        # 1. Clip cơ sở (sử dụng chiều cao tối thiểu 5px)
        base_bar = mp.ColorClip((BAR_WIDTH, 5), color=color).set_duration(duration)

        # 2. Hàm tính toán Chiều cao theo thời gian (t)
        def get_bar_height(t, index=i):
            # Sử dụng index để tạo pha và tần số khác nhau cho mỗi thanh
            phase_offset = index * 0.5
            freq_mult = 1 + (index % 5) * 0.1
            
            height_mult = 0.5 + 0.5 * math.sin(t * PULSE_SPEED * freq_mult + phase_offset)
            
            # Chiều cao nằm trong khoảng [5, container_max_height]
            return max(5, int(container_max_height * height_mult))
        
        # 3. Áp dụng Resize (Chiều cao)
        animated_bar = base_bar.fx(mp.vfx.resize, height=get_bar_height)
        
        # 4. Hàm tính toán Vị trí Y (để neo thanh vào đáy container)
        x_pos = start_x + i * (BAR_WIDTH + BAR_SPACING)
        
        def get_bar_pos(t, index=i):
            # Vị trí Y top edge = container_max_height - current_height
            current_height = get_bar_height(t, index)
            y_pos = container_max_height - current_height
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

        # Tải nền và micro
        background_clip = load_asset_image('default_background.png', width=VIDEO_WIDTH, height=VIDEO_HEIGHT, duration=duration)
        if not background_clip:
            background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
            
        microphone_clip = load_asset_image('microphone.png', width=int(VIDEO_WIDTH * 0.2), duration=duration, position=("center", VIDEO_HEIGHT // 2 + 50))


        # --- TẠO SÓNG ÂM ĐA THANH MỚI ---
        WAVE_COLOR = (0, 200, 0)
        WAVE_WIDTH = int(VIDEO_WIDTH * 0.7)
        WAVE_MAX_HEIGHT = int(VIDEO_HEIGHT * 0.1) # Chiều cao tối đa của container visualizer

        waveform_clip = create_multi_bar_visualizer(
            duration,
            WAVE_WIDTH,
            WAVE_MAX_HEIGHT,
            WAVE_COLOR
        )
        # Đặt toàn bộ Visualizer vào vị trí
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
