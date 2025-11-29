# File: ./scripts/finalize_audio.py
# Chức năng: Trộn audio TTS thô với nhạc nền (background music - BGM) để tạo file audio cuối cùng.

import os
import logging
from pydub import AudioSegment
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def finalize_audio(raw_audio_path: str, is_short: bool = False):
    """
    Trộn audio TTS với nhạc nền.
    Đảm bảo TTS bắt đầu ngay lập tức (không dạo nhạc intro) cho cả video dài và ngắn.
    
    Args:
        raw_audio_path (str): Đường dẫn đến file audio TTS thô.
        is_short (bool): Xác định xem đây là Shorts hay Video Dài (ảnh hưởng đến việc cắt BGM).
    
    Returns:
        str: Đường dẫn đến file audio cuối cùng.
    """
    load_dotenv()
    
    # Lấy Episode ID và định nghĩa tên file đầu ra
    episode_id = os.path.basename(raw_audio_path).split('_')[0]
    if is_short:
        # Output: 01_final_podcast_short.mp3
        output_filename = f"{episode_id}_final_podcast_short.mp3"
    else:
        # Output: 01_final_podcast.mp3
        output_filename = f"{episode_id}_final_podcast.mp3"
        
    audio_dir = os.path.join('outputs', 'audio')
    final_audio_path = os.path.join(audio_dir, output_filename)
    
    # Đường dẫn file nhạc nền (background music)
    bgm_path = os.path.join('assets', 'audio', 'background_music.mp3')
    if not os.path.exists(bgm_path):
        logging.error(f"Không tìm thấy nhạc nền tại: {bgm_path}")
        return raw_audio_path # Trả về raw audio nếu không có nhạc nền

    try:
        # Tải các đoạn Audio
        # Yêu cầu pydub và ffmpeg được cài đặt
        raw_audio = AudioSegment.from_mp3(raw_audio_path)
        bgm = AudioSegment.from_mp3(bgm_path)
        
        # Lấy độ dài TTS để căn chỉnh BGM
        tts_duration_ms = len(raw_audio)
        
        if is_short:
            # Đối với Shorts, giới hạn độ dài BGM tối đa 60 giây
            MAX_SHORTS_DURATION_MS = 60000
            bgm = bgm[:min(tts_duration_ms, MAX_SHORTS_DURATION_MS)]
        else:
            # Đối với Video Dài, cắt BGM theo đúng độ dài TTS
            bgm = bgm[:tts_duration_ms]

        # Giảm âm lượng nhạc nền (Mặc định: -15dB)
        BGM_VOLUME_REDUCTION = 15 # giảm 15dB
        bgm_volume_reduced = bgm - BGM_VOLUME_REDUCTION

        # TRỘN AUDIO:
        # Sử dụng .overlay(raw_audio, position=0) để đảm bảo TTS (raw_audio)
        # bắt đầu ở miligiây thứ 0 của BGM.
        final_audio_segment = bgm_volume_reduced.overlay(raw_audio, position=0) 
        
        # Xuất file cuối cùng
        final_audio_segment.export(final_audio_path, format="mp3")
        
        logging.info(f"Audio cuối cùng {'NGẮN' if is_short else 'DÀI'} đã được trộn (TTS bắt đầu ngay lập tức) và lưu tại: {final_audio_path}")
        return final_audio_path
        
    except Exception as e:
        logging.error(f"Lỗi khi trộn audio cho {raw_audio_path}: {e}", exc_info=True)
        return None
