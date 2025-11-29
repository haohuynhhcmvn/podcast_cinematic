# scripts/create_shorts.py
import logging
import os
# Import các hàm cần thiết cho video và audio
from moviepy.editor import AudioFileClip, VideoFileClip, ImageClip, ColorClip, TextClip, CompositeVideoClip, CompositeAudioClip, concatenate_audioclips
import math # Cần math.ceil để tính số lần lặp
from utils import get_path

logger = logging.getLogger(__name__)

# Cấu hình Shorts
SHORTS_SIZE = (1080, 1920)
MAX_DURATION = 60 # YouTube Shorts tối đa 60s

def create_shorts(audio_path, title_text, episode_id):
    try:
        # 1. Load Voice (TTS)
        voice = AudioFileClip(audio_path)
        duration = min(voice.duration, MAX_DURATION) # Giới hạn 60s
        voice = voice.subclip(0, duration) 
        
        # 2. Xử lý Nhạc Nền (SỬA LỖI LOOP TẠI ĐÂY)
        bg_music_path = get_path('assets', 'background_music', 'loop_1.mp3')
        if os.path.exists(bg_music_path):
            # Load nhạc nền và giảm âm lượng
            bg_music = AudioFileClip(bg_music_path).volumex(0.1) 
            
            # --- FIX CHO LỖI 'loop' ATTRIBUTE ---
            
            # Tính số lần lặp cần thiết (làm tròn lên)
            num_loops = math.ceil(duration / bg_music.duration)
            
            # Tạo danh sách các clip nhạc nền và NỐI lại
            bg_clips = [bg_music] * num_loops
            bg_music_looped = concatenate_audioclips(bg_clips).subclip(0, duration)
            
            # Trộn Voice + Nhạc
            final_audio = CompositeAudioClip([bg_music_looped, voice])
            
            logger.info(f"🎵 Đã mix nhạc nền (lặp {num_loops} lần) vào Shorts.")
        else:
            final_audio = voice # Không có nhạc thì dùng voice trần
            logger.warning("⚠️ Không tìm thấy file nhạc nền loop_1.mp3.")


        # 3. Load Video Nền
        bg_video = get_path('assets', 'video', 'podcast_loop_bg_short.mp4')
        if os.path.exists(bg_video):
            clip = VideoFileClip(bg_video).resize(SHORTS_SIZE).loop(duration=duration)
        else:
            clip = ColorClip(SHORTS_SIZE, color=(30,30,30), duration=duration)

        elements = [clip]

        # 4. Thêm Text Tiêu Đề ĐỘNG (Vị trí 1/3 dưới)
        if title_text:
            try:
                # Logic ngắt dòng thông minh hơn
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
                    font='Arial-Bold', 
                    method='caption', 
                    size=(950, None), 
                    stroke_color='black', 
                    stroke_width=3, 
                    align='center'
                )
                
                # Vị trí Y=1280 là 1/3 từ dưới lên
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
        # Trả về None khi xảy ra lỗi để pipeline có thể tiếp tục
        return None
