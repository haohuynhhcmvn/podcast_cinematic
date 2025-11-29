import logging
import os
from moviepy.editor import AudioFileClip, VideoFileClip, ImageClip, ColorClip, TextClip, CompositeVideoClip
from utils import get_path

logger = logging.getLogger(__name__)

def create_shorts(audio_path, episode_id):
    try:
        audio = AudioFileClip(audio_path)
        duration = min(audio.duration, 60) # Max 60s
        audio = audio.subclip(0, duration)
        
        bg_video = get_path('assets', 'video', 'podcast_loop_bg_short.mp4')
        
        if os.path.exists(bg_video):
            clip = VideoFileClip(bg_video).resize((1080, 1920)).loop(duration=duration)
        else:
            clip = ColorClip((1080, 1920), color=(30,30,30), duration=duration)

        elements = [clip]

        # Thêm Text (Try/Except để tránh lỗi ImageMagick)
        try:
            txt = TextClip("THEO DẤU CHÂN\nHUYỀN THOẠI", fontsize=70, color='white', font='Arial-Bold', method='caption', size=(900, None))
            txt = txt.set_pos(('center', 200)).set_duration(duration)
            elements.append(txt)
        except:
            logger.warning("⚠️ Bỏ qua Text (Lỗi ImageMagick).")

        final = CompositeVideoClip(elements, size=(1080, 1920)).set_audio(audio)
        out_path = get_path('outputs', 'shorts', f"{episode_id}_shorts.mp4")
        
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='ultrafast', logger=None)
        logger.info(f"📱 Shorts xong: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"❌ Lỗi Shorts: {e}")
        return None
