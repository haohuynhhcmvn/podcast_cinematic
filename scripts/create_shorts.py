import logging
import os
import math 
from moviepy.editor import AudioFileClip, VideoFileClip, ImageClip, ColorClip, TextClip, CompositeVideoClip, CompositeAudioClip, concatenate_audioclips 
from utils import get_path

logger = logging.getLogger(__name__)

# Cấu hình Shorts
SHORTS_SIZE = (1080, 1920)
MAX_DURATION = 60 

def create_shorts(audio_path, title_text, episode_id):
    try:
        # 1. Load Voice (TTS)
        # Tăng âm lượng giọng đọc lên 1.3 lần
        voice = AudioFileClip(audio_path).volumex(1.3) 
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

        # 4. Thêm Text Tiêu Đề ĐỘNG (Vị trí 1/3 dưới)
        if title_text:
            try:
                # Logic ngắt dòng
                display_text = title_text
                if len(display_text) > 20 and "\n" not in display_text:
                    mid = len(display_text) // 2
                    split_idx = display_text.find(' ', mid - 5, mid + 5)
                    if split_idx == -1: split_idx = mid
                    display_text = display_text[:split_idx] + "\n" + display_text[split_idx+1:]

                txt = TextClip(
                    display_text, 
                    fontsize=70, 
                    color='yellow', 
                    # --- FIX FONT TIẾNG VIỆT ---
                    font='DejaVu-Sans-Bold', # Thay thế Arial-Bold bằng font chuẩn Unicode trên Linux
                    method='caption', 
                    size=(950, None), 
                    stroke_color='black', 
                    stroke_width=3, 
                    align='center'
                )
                
                txt = txt.set_pos(('center', 1280)).set_duration(duration)
                elements.append(txt)
            except Exception as e:
                logger.warning(f"⚠️ Bỏ qua Text do lỗi ImageMagick hoặc Font: {e}")

        # 5. Render
        final = CompositeVideoClip(elements, size=SHORTS_SIZE).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger=None)
        logger.info(f"✅ Shorts hoàn tất: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"❌ Lỗi Shorts: {e}")
        return None
