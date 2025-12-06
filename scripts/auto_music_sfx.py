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
VOL_MUSIC_LOW = -22.0   # Nhạc nền (mức nhỏ)
VOL_MUSIC_HIGH = -18.0  # Nhạc nền (mức cao trào)
VOL_SFX = -10.0         # Hiệu ứng âm thanh (không được át giọng)
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
    Tạo nhạc nền thay đổi theo thời gian (Intro -> BuildUp -> Climax -> End).
    Nếu không đủ file, sẽ fallback về loop cơ bản.
    """
    # Tìm các file nhạc theo thứ tự ưu tiên
    # Bạn hãy đổi tên file trong thư mục assets/background_music/ thành bg_1.mp3, bg_2.mp3...
    bg_files = []
    bg_dir = get_path('assets', 'background_music')
    
    # Quét tất cả file bắt đầu bằng 'bg_' hoặc 'loop_'
    if os.path.exists(bg_dir):
        files = sorted([f for f in os.listdir(bg_dir) if f.endswith('.mp3')])
        # Ưu tiên bg_1, bg_2...
        bg_files = [os.path.join(bg_dir, f) for f in files if f.startswith('bg_')]
        if not bg_files:
            # Fallback về loop_1.mp3 cũ nếu chưa đổi tên
            bg_files = [os.path.join(bg_dir, f) for f in files if f.startswith('loop_')]

    if not bg_files:
        logger.warning("⚠️ Không tìm thấy nhạc nền nào. Video sẽ không có nhạc.")
        return AudioSegment.silent(duration=duration_ms)

    # Logic ghép nhạc: Chia thời lượng cho số bài nhạc và ghép nối
    segment_duration = duration_ms // len(bg_files)
    final_bg = AudioSegment.empty()

    for i, fpath in enumerate(bg_files):
        track = load_audio(fpath)
        if not track: continue

        # Chuẩn hóa âm lượng
        # Nếu là bài giữa (Cao trào), cho to hơn chút
        if 0 < i < len(bg_files) - 1:
            track = track + VOL_MUSIC_HIGH 
        else:
            track = track + VOL_MUSIC_LOW

        # Loop track cho đủ độ dài segment
        while len(track) < segment_duration + 5000: # +5s để crossfade
            track += track
        
        # Cắt đúng độ dài cần thiết
        # Bài cuối cùng sẽ lấy phần dư còn lại
        target_len = segment_duration if i < len(bg_files) - 1 else (duration_ms - len(final_bg))
        track = track[:target_len]

        # Crossfade (Trộn chồng mép 2 giây)
        if len(final_bg) > 0:
            final_bg = final_bg.append(track, crossfade=2000)
        else:
            final_bg = track

    # Cắt chính xác lần cuối
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

    # Vùng hoạt động của SFX: Từ 30% đến 80% thời lượng video
    zone_start = int(voice_len_ms * 0.3)
    zone_end = int(voice_len_ms * 0.8)
    
    # Cứ mỗi 45 giây chèn 1 hiệu ứng (tránh spam)
    current_pos = zone_start
    while current_pos < zone_end:
        # Nhảy cóc ngẫu nhiên 30s - 60s
        step = random.randint(30000, 60000)
        current_pos += step
        
        if current_pos >= zone_end: break

        # Chọn 1 sfx ngẫu nhiên
        sfx_path = random.choice(sfx_files)
        sfx = load_audio(sfx_path)
        
        if sfx:
            # Giảm volume SFX để không át giọng
            sfx = sfx + VOL_SFX 
            # Overlay
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

        # 1. Chuẩn hóa giọng đọc
        voice = voice + VOL_VOICE
        duration_ms = len(voice)
        logger.info(f"🎧 Voice duration: {duration_ms/1000:.1f}s")

        # 2. Tạo nhạc nền Dynamic (Nhiều bài ghép lại)
        bg_music = generate_dynamic_background(duration_ms)

        # 3. Mix Voice vào Nhạc nền
        # (Nhạc nền đã được chỉnh volume trong hàm generate)
        mixed = bg_music.overlay(voice)

        # 4. [NEW] Chèn SFX vào vùng cao trào
        mixed = inject_sfx(mixed, duration_ms)

        # 5. Thêm Intro / Outro (Giữ nguyên logic cũ)
        intro_path = get_path('assets', 'intro_outro', 'intro.mp3') # Nếu có
        outro_path = get_path('assets', 'intro_outro', 'outro.mp3')
        
        final_mix = mixed

        if os.path.exists(outro_path):
            outro = load_audio(outro_path)
            if outro:
                outro = outro + VOL_INTRO
                final_mix = final_mix.append(outro, crossfade=1000)

        # 6. Xuất file
        output_path = get_path('outputs', 'audio', f"{episode_id}_mixed.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final_mix.export(output_path, format="mp3")
        logger.info(f"✅ Audio Mixing Complete: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Auto Music SFX: {e}", exc_info=True)
        return None
