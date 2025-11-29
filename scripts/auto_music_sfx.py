# ./script/auto_music_sfx.py
import os
import logging
from pydub import AudioSegment
from utils import get_path # Đảm bảo file utils được import để dùng get_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CẤU HÌNH ÂM LƯỢNG MỚI ---
VOLUME_VOICE = -3.0      # SỬA LỖI: Tăng Giọng nói lên 5dB để to và rõ hơn
VOLUME_BG_MUSIC = -25.0  # Nhạc nền (giữ nguyên độ nhỏ để không át giọng)
VOLUME_INTRO_OUTRO = -15.0 # Intro/Outro

def load_audio(filepath, target_volume=None):
    """Tải và chuẩn hóa âm lượng file audio."""
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
    intro_path = get_path('assets', 'intro_outro', 'intro.mp3')
    outro_path = get_path('assets', 'intro_outro', 'outro.mp3')
    bg_music_path = get_path('assets', 'background_music', 'loop_1.mp3')
    
    # Load các thành phần
    intro_audio = load_audio(intro_path, target_volume=VOLUME_INTRO_OUTRO)
    outro_audio = load_audio(outro_path, target_volume=VOLUME_INTRO_OUTRO)
    bg_music_loop = load_audio(bg_music_path, target_volume=VOLUME_BG_MUSIC)
    
    # Logic mixing (Giả định logic này đã hoàn chỉnh)
    if not voice_audio: return None

    # Xử lý Nhạc nền
    total_body_duration = len(voice_audio)
    bg_music = bg_music_loop * (total_body_duration // len(bg_music_loop) + 1)
    bg_music = bg_music[:total_body_duration] 

    # Trộn nhạc nền và giọng nói (Voice đã to hơn)
    body_segment = bg_music.overlay(voice_audio)

    # Kết nối các phân đoạn (Không có Intro text/audio)
    final_podcast = body_segment + outro_audio 

    # Xuất file cuối cùng
    output_path = get_path('outputs', 'audio', f"final_mix_{episode_id}.mp3")
    final_podcast.export(output_path, format="mp3")
    logging.info(f"✅ Audio mix hoàn tất cho tập {episode_id}.")
    return output_path
