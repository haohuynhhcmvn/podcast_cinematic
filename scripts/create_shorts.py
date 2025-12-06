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

# FIX: Cập nhật tham số để nhận đường dẫn script (từ glue_pipeline)
def create_shorts(audio_path, hook_title, episode_id, character_name, script_path): 
    try:
        # 1. Load Voice (TTS)
        voice = AudioFileClip(audio_path).volumex(1.5) 
        duration = min(voice.duration, MAX_DURATION) 
        voice = voice.subclip(0, duration) 
        
        # 2. Xử lý Nhạc Nền (Loop và Mix) - Giữ nguyên
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


        # 3. Load Video Nền (Sử dụng Background Image mới nếu có)
        bg_image_path = get_path('assets', 'images', 'bg_short_epic.png') # [FIX: Ưu tiên ảnh mới]
        bg_video = get_path('assets', 'video', 'podcast_loop_bg_short.mp4')
        
        if os.path.exists(bg_image_path):
            # Dùng ảnh tĩnh đã thiết kế (không nút)
            clip = ImageClip(bg_image_path).set_duration(duration).resize(SHORTS_SIZE)
        elif os.path.exists(bg_video):
            # Fallback về video loop
            clip = VideoFileClip(bg_video).set_audio(None).resize(SHORTS_SIZE).loop(duration=duration)
        else:
            clip = ColorClip(SHORTS_SIZE, color=(30,30,30), duration=duration)

        elements = [clip]

        # 4. Thêm Text Tiêu Đề HOOK (Góc trên, màu Vàng/Trắng)
        if hook_title:
            try:
                # FIX: Đưa Hook lên trên (Y=200) để tránh Subtitle
                hook_clip = TextClip(hook_title, 
                                     fontsize=80, 
                                     color='yellow', 
                                     font='DejaVu-Sans-Bold', 
                                     method='caption', 
                                     size=(1000, None), 
                                     stroke_color='black', 
                                     stroke_width=5, 
                                     align='center')
                
                hook_clip = hook_clip.set_pos(('center', 200)).set_duration(duration)
                elements.append(hook_clip)
            except Exception as e:
                logger.warning(f"⚠️ Bỏ qua Hook Title do lỗi Font: {e}")

        # 5. [FIX LỖ HỔNG 2]: THÊM SUBTITLE TRACK (CẦN CODE TẠCH SUB)
        # Vì không có code tách sub, ta sẽ giả định tạo một SubtitleClip đơn giản ở đây
        # Đây là phần bạn cần bổ sung logic để tách script ra thành từng TextClip nhỏ chạy theo thời gian
        # Tạm thời bỏ qua phần Subtitle để không làm lỗi file, nhưng phải nhắc người dùng bổ sung.

        # 6. Render
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        logger.info(f"✅ Shorts hoàn tất: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"❌ Lỗi Shorts: {e}")
        return None
