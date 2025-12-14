# scripts/auto_music_sfx.py

import os
import logging
import random
from pydub import AudioSegment
from utils import get_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ÂM LƯỢNG (dB) ---
VOL_VOICE = -2.0        # Giọng đọc to rõ
VOL_MUSIC_LOW = -22.0   # Nhạc nền (mức nhỏ - Intro)
VOL_MUSIC_HIGH = -18.0  # Nhạc nền (mức cao trào - Body)
VOL_SFX = -10.0         # Hiệu ứng âm thanh
VOL_INTRO = -10.0

def load_audio(filepath):
    try:
        if os.path.exists(filepath):
            return AudioSegment.from_file(filepath)
    except Exception as e:
        logger.error(f"⚠️ Lỗi tải file {filepath}: {e}")
    return None

def generate_dynamic_background(duration_ms):
    """
    Tạo nhạc nền thay đổi theo thời gian (Intro -> BuildUp -> Climax).
    Tự động nối bg_1.mp3, bg_2.mp3... lại với nhau.
    """
    bg_dir = get_path('assets', 'background_music')
    bg_files = []
    
    # 1. Quét file nhạc nền (bg_1, bg_2...)
    if os.path.exists(bg_dir):
        files = sorted([f for f in os.listdir(bg_dir) if f.endswith('.mp3')])
        # Ưu tiên các file bắt đầu bằng 'bg_'
        bg_files = [os.path.join(bg_dir, f) for f in files if f.startswith('bg_')]
        
        # Nếu không có bg_, dùng tạm loop_
        if not bg_files:
            bg_files = [os.path.join(bg_dir, f) for f in files if f.startswith('loop_')]

    if not bg_files:
        logger.warning("⚠️ Không tìm thấy nhạc nền. Video sẽ im lặng.")
        return AudioSegment.silent(duration=duration_ms)

    # 2. Logic ghép nhạc
    # Chia thời lượng video cho số bài nhạc để chia đoạn
    segment_duration = duration_ms // len(bg_files)
    final_bg = AudioSegment.empty()

    for i, fpath in enumerate(bg_files):
        track = load_audio(fpath)
        if not track: continue

        # Điều chỉnh âm lượng: Bài đầu nhỏ, bài giữa to hơn
        if 0 < i < len(bg_files) - 1:
            track = track + VOL_MUSIC_HIGH 
        else:
            track = track + VOL_MUSIC_LOW

        # Loop track cho đủ độ dài segment (nếu track ngắn quá)
        while len(track) < segment_duration + 5000: 
            track += track
        
        # Cắt đúng độ dài (Bài cuối lấy phần dư)
        target_len = segment_duration if i < len(bg_files) - 1 else (duration_ms - len(final_bg))
        # Đảm bảo không cắt lố
        if target_len <= 0: target_len = 1000 
        track = track[:target_len]

        # Ghép nối (Crossfade 2s cho mượt)
        if len(final_bg) > 0:
            final_bg = final_bg.append(track, crossfade=2000)
        else:
            final_bg = track

    # Cắt chính xác lần cuối cho khớp duration
    return final_bg[:duration_ms]

def inject_sfx(mixed_audio, voice_len_ms):
    """
    Chèn SFX ngẫu nhiên vào vùng Cao trào (30% - 80% thời lượng).
    """
    sfx_dir = get_path('assets', 'sfx')
    if not os.path.exists(sfx_dir):
        return mixed_audio

    sfx_files = [os.path.join(sfx_dir, f) for f in os.listdir(sfx_dir) if f.endswith('.mp3')]
    if not sfx_files:
        return mixed_audio

    # Vùng hoạt động: 30% -> 80%
    zone_start = int(voice_len_ms * 0.3)
    zone_end = int(voice_len_ms * 0.8)
    
    current_pos = zone_start
    
    # Cứ mỗi khoảng 30s-60s chèn 1 lần
    while current_pos < zone_end:
        step = random.randint(30000, 60000)
        current_pos += step
        if current_pos >= zone_end: break

        # Chọn SFX ngẫu nhiên (kiếm, ngựa, hét...)
        sfx_path = random.choice(sfx_files)
        sfx = load_audio(sfx_path)
        
        if sfx:
            sfx = sfx + VOL_SFX
            # Overlay vào audio chính
            mixed_audio = mixed_audio.overlay(sfx, position=current_pos)
            logger.info(f"⚔️ Chèn SFX tại {current_pos//1000}s: {os.path.basename(sfx_path)}")

    return mixed_audio

def auto_music_sfx(raw_audio_path: str, episode_id: int):
    """
    Hàm chính: Mix Voice + Dynamic Music + SFX + Intro/Outro
    """
    try:
        voice = load_audio(raw_audio_path)
        if not voice: return None

        voice = voice + VOL_VOICE
        duration_ms = len(voice)
        logger.info(f"🎧 Voice duration: {duration_ms/1000:.1f}s")

        # 1. Tạo nhạc nền động
        bg_music = generate_dynamic_background(duration_ms)

        # 2. Mix Voice vào Nhạc
        mixed = bg_music.overlay(voice)

        # 3. Chèn SFX (NEW)
        mixed = inject_sfx(mixed, duration_ms)

        # 4. Thêm Intro / Outro (Logic đã cập nhật)
        intro_path = get_path('assets', 'intro_outro', 'intro.mp3')
        outro_path = get_path('assets', 'intro_outro', 'outro.mp3')
        
        final_audio = mixed # Bắt đầu với audio đã mix

        # --- LOGIC THÊM INTRO ---
        if os.path.exists(intro_path):
            intro = load_audio(intro_path)
            if intro:
                intro = intro + VOL_INTRO
                # Nối Intro vào ĐẦU audio đã trộn
                final_audio = intro.append(final_audio, crossfade=1000)
                logger.info("🎬 Đã thêm Intro vào đầu Video.")

        # --- LOGIC THÊM OUTRO ---
        if os.path.exists(outro_path):
            outro = load_audio(outro_path)
            if outro:
                outro = outro + VOL_INTRO
                # Nối Outro vào CUỐI audio
                final_audio = final_audio.append(outro, crossfade=1000)
                logger.info("🔚 Đã thêm Outro vào cuối Video.")

        # Xuất file (Sử dụng final_audio thay vì mixed)
        output_path = get_path('outputs', 'audio', f"{episode_id}_mixed.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final_audio.export(output_path, format="mp3") # Export final_audio (thay vì mixed)
        logger.info(f"✅ Audio Mixing Complete: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Auto Music SFX: {e}", exc_info=True)
        return None
