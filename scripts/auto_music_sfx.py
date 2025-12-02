# ./scripts/auto_music_sfx.py
import os
import logging
from pydub import AudioSegment
from utils import get_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VOLUME_VOICE = -3.0
VOLUME_BG_MUSIC = -25.0
VOLUME_INTRO_OUTRO = -15.0


def load_audio(filepath, target_volume=None):
    try:
        audio = AudioSegment.from_file(filepath)
        if target_volume is not None:
            change = target_volume - audio.dBFS
            audio = audio.apply_gain(change)
        return audio
    except Exception as e:
        logging.error(f"Lỗi khi tải file: {filepath} – {e}")
        return None


def auto_music_sfx(raw_audio_path: str, episode_id: int):
    voice = load_audio(raw_audio_path, target_volume=VOLUME_VOICE)
    if not voice:
        return None

    outro_path = get_path('assets', 'intro_outro', 'outro.mp3')
    bg_path = get_path('assets', 'background_music', 'loop_1.mp3')

    outro = load_audio(outro_path, target_volume=VOLUME_INTRO_OUTRO)
    bg_music = load_audio(bg_path, target_volume=VOLUME_BG_MUSIC)

    # ⭐ Không bao giờ kéo dài audio!
    # Nhạc nền phải cắt đúng bằng độ dài voice
    if bg_music:
        bg_extended = (bg_music * (len(voice) // len(bg_music) + 1))[:len(voice)]
        body = voice.overlay(bg_extended, loop=False)
    else:
        body = voice

    # Thêm outro nếu có
    if outro:
        body = body + outro

    out_path = get_path('outputs', 'audio', f"final_mix_{episode_id}.mp3")
    body.export(out_path, format="mp3")

    logging.info(f"🎧 Final audio length: {len(body)/1000:.2f}s (KHÔNG ép ≥ 10 phút)")
    return out_path