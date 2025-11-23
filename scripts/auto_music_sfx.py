import os
import logging
from pydub import AudioSegment

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VOLUME_VOICE = -10.0  # Giọng nói
VOLUME_BG_MUSIC = -25.0  # Nhạc nền
VOLUME_INTRO_OUTRO = -15.0 # Intro/Outro

def load_audio(filepath, target_volume=None):
    try:
        audio = AudioSegment.from_file(filepath)
        if target_volume is not None:
            change_in_dBFS = target_volume - audio.dBFS
            audio = audio.apply_gain(change_in_dBFS)
        return audio
    except Exception as e:
        logging.error(f"Lỗi khi tải file audio {filepath}: {e}")
        return None

def auto_music_sfx(raw_audio_path: str, episode_id: int):
    voice_audio = load_audio(raw_audio_path, target_volume=VOLUME_VOICE)
    
    # Định nghĩa đường dẫn các file cố định
    intro_path = os.path.join('assets', 'intro_outro', 'intro.mp3')
    outro_path = os.path.join('assets', 'intro_outro', 'outro.mp3')
    bg_music_path = os.path.join('assets', 'background_music', 'loop_1.mp3')
    
    intro_audio = load_audio(intro_path, target_volume=VOLUME_INTRO_OUTRO)
    outro_audio = load_audio(outro_path, target_volume=VOLUME_INTRO_OUTRO)
    bg_music_loop = load_audio(bg_music_path, target_volume=VOLUME_BG_MUSIC)
    
    if not (voice_audio and intro_audio and outro_audio and bg_music_loop):
        logging.error("Thiếu thành phần audio cần thiết cho hậu kỳ.")
        return None

    # Xử lý Nhạc nền
    total_body_duration = len(voice_audio)
    bg_music = bg_music_loop * (total_body_duration // len(bg_music_loop) + 1)
    bg_music = bg_music[:total_body_duration] 

    # Trộn nhạc nền và giọng nói (Ducking được xử lý qua điều chỉnh volume)
    body_segment = bg_music.overlay(voice_audio)

    # Kết nối các phân đoạn (Intro + Body + Outro)
    final_podcast = intro_audio + body_segment + outro_audio

    # Xuất file cuối cùng
    output_dir = os.path.join('outputs', 'audio')
    final_filename = f"{episode_id}_final_podcast.mp3"
    final_path = os.path.join(output_dir, final_filename)

    logging.info(f"Bắt đầu xuất file podcast cuối cùng...")
    final_podcast.export(final_path, format="mp3", parameters=["-ac", "2", "-b:a", "192k"])

    logging.info(f"Podcast hoàn chỉnh đã lưu tại: {final_path}")
    return final_path
