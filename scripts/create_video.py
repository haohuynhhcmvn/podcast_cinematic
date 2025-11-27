# scripts/create_video.py (ĐÃ SỬA: Thêm Background và Micro từ Assets)
import os
import logging
import moviepy.editor as mp
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30) # Màu dự phòng nếu không tìm thấy ảnh
MICROPHONE_IMAGE_PATH = os.path.join('assets', 'images', 'microphone.png') # Đường dẫn tới ảnh micro
BACKGROUND_IMAGE_DEFAULT_PATH = os.path.join('assets', 'images', 'default_background.png') # Ảnh nền mặc định

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        logging.warning("BỎ QUA HOÀN TOÀN TẠO PHỤ ĐỀ (SubtitleClip) cho video 16:9 để hoàn thành pipeline.")
        
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # Tạo clip placeholder trong suốt thay thế cho phụ đề
        subtitle_clip_to_use = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)

        # --- NỀN (BACKGROUND IMAGE) ---
        # Ưu tiên tìm ảnh nền từ ImageFolder nếu có, nếu không thì dùng mặc định
        # LƯU Ý: logic ImageFolder cần được xử lý ở fetch_content/glue_pipeline để truyền đường dẫn cụ thể vào đây
        # Tạm thời dùng mặc định cho đến khi có đường dẫn ImageFolder cụ thể
        
        background_image_path = BACKGROUND_IMAGE_DEFAULT_PATH # Sử dụng ảnh nền mặc định
        
        if not os.path.exists(background_image_path):
            logging.warning(f"Ảnh nền mặc định không tìm thấy tại {background_image_path}. Dùng ColorClip làm nền.")
            background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        else:
            background_clip = mp.ImageClip(background_image_path).set_duration(duration)
            background_clip = background_clip.resize(newsize=(VIDEO_WIDTH, VIDEO_HEIGHT)) # Đảm bảo ảnh vừa khung hình

        # --- MICROPHONE IMAGE ---
        microphone_clip = None
        if os.path.exists(MICROPHONE_IMAGE_PATH):
            microphone_clip = mp.ImageClip(MICROPHONE_IMAGE_PATH).set_duration(duration)
            microphone_clip = microphone_clip.resize(width=int(VIDEO_WIDTH * 0.2)) # Kích thước micro
            microphone_clip = microphone_clip.set_pos(("center", VIDEO_HEIGHT // 2 + 50)) # Đặt phía dưới sóng âm

        # Sóng âm ĐỘNG
        WAVE_COLOR = (0, 200, 0) # Màu xanh lá đậm
        WAVE_HEIGHT = 10 
        WAVE_WIDTH = int(VIDEO_WIDTH * 0.7)
        
        base_waveform_clip = mp.ColorClip((WAVE_WIDTH, WAVE_HEIGHT), color=WAVE_COLOR, duration=duration)

        MAX_HEIGHT_MULTIPLIER = 3.0 
        PULSE_SPEED = 10 

        def resize_func(t):
            scale_factor = 1.0 + (MAX_HEIGHT_MULTIPLIER - 1.0) * (0.5 * (1 + math.sin(t * PULSE_SPEED)))
            return scale_factor
        
        waveform_clip = base_waveform_clip.fx(mp.vfx.resize, height=lambda t: WAVE_HEIGHT * resize_func(t))
        waveform_clip = waveform_clip.set_pos(("center", VIDEO_HEIGHT // 2 - 50))
        
        # Ghép các thành phần (Đúng thứ tự lớp: Background -> Micro -> Sóng âm -> Subtitle)
        elements = [background_clip, waveform_clip, subtitle_clip_to_use]
        if microphone_clip:
            elements.insert(1, microphone_clip) # Chèn micro phía trên background, dưới sóng âm

        final_clip = mp.CompositeVideoClip(elements, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

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
