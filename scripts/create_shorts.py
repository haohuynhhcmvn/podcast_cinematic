# scripts/create_shorts.py
import logging
import os
import math 
from moviepy.editor import AudioFileClip, VideoFileClip, ImageClip, ColorClip, TextClip, CompositeVideoClip, CompositeAudioClip, concatenate_audioclips 
from utils import get_path

logger = logging.getLogger(__name__)

# Cấu hình Shorts
SHORTS_SIZE = (1080, 1920)
MAX_DURATION = 60 

def create_shorts(audio_path, title_text, episode_id): # Giữ title_text (hook_title) nhưng sẽ ít dùng hơn
    try:
        # 1. Load Voice (TTS)
        voice = AudioFileClip(audio_path).volumex(1.5) 
        duration = min(voice.duration, MAX_DURATION) 
        voice = voice.subclip(0, duration) 
        
        # 2. Xử lý Nhạc Nền (Loop và Mix)
        bg_music_path = get_path('assets', 'background_music', 'loop_1.mp3')
        if os.path.exists(bg_music_path):
            bg_music = AudioFileClip(bg_music_path).volumex(0.1) 
            num_loops = math.ceil(duration / bg_music.duration)
            bg_clips = [bg_music] * num_loops
            bg_music_looped = concatenate_audioclips(bg_clips).subclip(0, duration)
            final_audio = CompositeAudioClip([bg_music_looped, voice])
        else:
            final_audio = voice
            logger.warning("⚠️ Không tìm thấy file nhạc nền loop_1.mp3.")


        # 3. Load Video Nền (TẮT AUDIO NGUỒN)
        bg_video = get_path('assets', 'video', 'podcast_loop_bg_short.mp4')
        if os.path.exists(bg_video):
            clip = VideoFileClip(bg_video).set_audio(None).resize(SHORTS_SIZE).loop(duration=duration)
        else:
            clip = ColorClip(SHORTS_SIZE, color=(30,30,30), duration=duration)

        elements = [clip]

        # 4. Thêm Text Tiêu Đề Cố Định (Tên nhân vật - Trắng Neon)
        # Lấy tên nhân vật từ data.get('Name')
        # SỬ DỤNG TÊN NHÂN VẬT THAY VÌ HOOK_TITLE
        main_title_content = episode_id.split('_')[0] # Lấy phần trước dấu gạch dưới từ episode_id (ví dụ: "Abraham Lincoln" từ "Abraham Lincoln_short")
        if main_title_content:
            try:
                # Định dạng chữ trắng neon
                main_title_clip = TextClip(main_title_content.upper(), 
                                           fontsize=85, 
                                           color='white', # Màu chữ trắng
                                           font='DejaVu-Sans-Bold', # Font mạnh mẽ
                                           method='caption', 
                                           size=(1000, None), # Chiều rộng tối đa 1000px
                                           stroke_color='cyan', # Viền màu xanh cyan để tạo hiệu ứng neon
                                           stroke_width=5, 
                                           align='center')
                
                # Đặt vị trí ở khoảng 1/4 trên màn hình
                main_title_clip = main_title_clip.set_pos(('center', 150)).set_duration(duration)
                elements.append(main_title_clip)
            except Exception as e:
                logger.warning(f"⚠️ Bỏ qua Text Title chính do lỗi ImageMagick hoặc Font: {e}")

        # 5. Render
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        logger.info(f"✅ Shorts hoàn tất: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"❌ Lỗi Shorts: {e}")
        return None
