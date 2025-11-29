import os
import logging
from pydub import AudioSegment
from utils import get_path

logger = logging.getLogger(__name__)

def auto_music_sfx(voice_path, episode_id):
    try:
        # Load Voice
        voice = AudioSegment.from_file(voice_path) - 5
        
        # Load Assets (An toàn)
        def load_safe(p): return AudioSegment.from_file(p) if os.path.exists(p) else AudioSegment.silent(0)
        
        intro = load_safe(get_path('assets', 'intro_outro', 'intro.mp3'))
        outro = load_safe(get_path('assets', 'intro_outro', 'outro.mp3'))
        bg_music = load_safe(get_path('assets', 'background_music', 'loop_1.mp3')) - 25

        # Loop Background Music
        if len(bg_music) > 0:
            loops = int(len(voice) / len(bg_music)) + 2
            bg_final = (bg_music * loops)[:len(voice) + 2000]
            body = voice.overlay(bg_final)
        else:
            body = voice

        final = intro + body + outro
        out_path = get_path('outputs', 'audio', f"{episode_id}_final_mix.mp3")
        final.export(out_path, format="mp3")
        
        logger.info(f"🎵 Audio Mix xong: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"❌ Lỗi Audio Mix: {e}")
        return None
