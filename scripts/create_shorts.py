# scripts/create_shorts.py
import logging
import os
# Import thêm CompositeAudioClip để trộn nhạc
from moviepy.editor import AudioFileClip, VideoFileClip, ImageClip, ColorClip, TextClip, CompositeVideoClip, CompositeAudioClip
from utils import get_path

logger = logging.getLogger(__name__)

def create_shorts(audio_path, title_text, episode_id):
    try:
        # 1. Load Voice (TTS)
        voice = AudioFileClip(audio_path)
        duration = min(voice.duration, 60) # Max 60s
        voice = voice.subclip(0, duration)
        
        # 2. Xử lý Nhạc Nền
        bg_music_path = get_path('assets', 'background_music', 'loop_1.mp3')
        if os.path.exists(bg_music_path):
            # Giảm volume xuống 10% (khá nhỏ để làm nền)
            bg_music = AudioFileClip(bg_music_path).volumex(0.1) 
            bg_music = bg_music.loop(duration=duration)
            # Trộn: Giọng đọc + Nhạc nền
            final_audio = CompositeAudioClip([bg_music, voice])
        else:
            final_audio = voice

        # 3. Load Video Nền
        bg_video = get_path('assets', 'video', 'podcast_loop_bg_short.mp4')
        if os.path.exists(bg_video):
            clip = VideoFileClip(bg_video).resize((1080, 1920)).loop(duration=duration)
        else:
            clip = ColorClip((1080, 1920), color=(30,30,30), duration=duration)

        elements = [clip]

        # 4. Thêm Text Tiêu Đề ĐỘNG (VỊ TRÍ MỚI)
        if title_text:
            try:
                # Tự động xuống dòng nếu quá dài (đơn giản)
                display_text = title_text
                if len(display_text) > 20 and "\n" not in display_text:
                    mid = len(display_text) // 2
                    # Tìm khoảng trắng gần giữa nhất để ngắt dòng cho đẹp
                    split_idx = display_text.find(' ', mid - 5, mid + 5)
                    if split_idx == -1: split_idx = mid
                    display_text = display_text[:split_idx] + "\n" + display_text[split_idx+1:]

                txt = TextClip(
                    display_text, 
                    fontsize=70, # Tăng size chữ lên một chút cho nổi bật
                    color='yellow', # Đổi màu vàng cho bắt mắt
                    font='Arial-Bold', 
                    method='caption', 
                    size=(950, None), # Chiều ngang tối đa
                    stroke_color='black', 
                    stroke_width=3, # Viền đen dày hơn
                    align='center'
                )
                
                # --- VỊ TRÍ MỚI ---
                # ('center', Y): Căn giữa theo chiều ngang, Y tính từ trên xuống
                # Y = 1280 là khoảng 2/3 từ trên xuống (tức 1/3 từ dưới lên)
                txt = txt.set_pos(('center', 1280)).set_duration(duration)
                
                elements.append(txt)
            except Exception as e:
                logger.warning(f"⚠️ Bỏ qua Text do lỗi ImageMagick: {e}")

        # 5. Render
        final = CompositeVideoClip(elements, size=(1080, 1920)).set_audio(final_audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        
        # Dùng preset ultrafast và threads cao để render nhanh
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', threads=4, logger='bar')
        logger.info(f"📱 Shorts xong (Nhạc nền + Title 1/3 dưới): {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"❌ Lỗi Shorts: {e}")
        return None
