import logging
import os
from moviepy.editor import AudioFileClip, VideoFileClip, ImageClip, ColorClip, CompositeVideoClip
from utils import get_path

logger = logging.getLogger(__name__)

def create_video(audio_path, episode_id):
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Ưu tiên Video Loop
        bg_video = get_path('assets', 'video', 'podcast_loop_bg_long.mp4')
        bg_img = get_path('assets', 'images', 'default_background.png')
        
        if os.path.exists(bg_video):
            clip = VideoFileClip(bg_video).resize((1920, 1080)).loop(duration=duration)
        elif os.path.exists(bg_img):
            clip = ImageClip(bg_img).set_duration(duration).resize((1920, 1080))
        else:
            clip = ColorClip((1920, 1080), color=(0,0,0), duration=duration)

        # Thêm Mic
        mic_path = get_path('assets', 'images', 'microphone.png')
        if os.path.exists(mic_path):
            mic = ImageClip(mic_path).set_duration(duration).resize(height=400).set_pos('center')
            final = CompositeVideoClip([clip, mic])
        else:
            final = clip
            
        final = final.set_audio(audio)
        out_path = get_path('outputs', 'video', f"{episode_id}_full_169.mp4")
        
        # Render
        final.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', preset='fast', logger=None)
        logger.info(f"🎬 Video 16:9 xong: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"❌ Lỗi Video 16:9: {e}")
        return None
