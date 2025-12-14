# === scripts/auto_music_sfx.py (Đã sửa lỗi NameError) ===

import os
import logging
import random
from pydub import AudioSegment
from utils import get_path

# Cần đảm bảo logging đã được cấu hình ở glue_pipeline
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ÂM LƯỢNG (dB) ---
VOL_VOICE = -2.0        
VOL_MUSIC_LOW = -22.0   
VOL_MUSIC_HIGH = -18.0  
VOL_SFX = -10.0         
VOL_INTRO = -10.0

# Hằng số Crossfade an toàn mặc định
MAX_CROSSFADE = 2000 # 2 giây
MIN_CROSSFADE = 100  # 100ms tối thiểu

def load_audio(filepath):
    try:
        if os.path.exists(filepath):
            return AudioSegment.from_file(filepath)
    except Exception as e:
        logger.error(f"⚠️ Lỗi tải file {filepath}: {e}")
    return None

def get_safe_crossfade(clip1_len, clip2_len, max_cf=MAX_CROSSFADE):
    """
    Tính toán Crossfade an toàn. Phải nhỏ hơn 50% độ dài của clip ngắn nhất.
    """
    if clip1_len == 0 or clip2_len == 0:
        return MIN_CROSSFADE
        
    # Lấy 50% độ dài clip ngắn nhất
    max_safe = min(clip1_len, clip2_len) // 2 
    
    # Chọn giá trị nhỏ nhất giữa max mong muốn và max_safe
    crossfade_duration = min(max_cf, max_safe)
    
    # Đảm bảo tối thiểu 100ms
    return max(MIN_CROSSFADE, crossfade_duration)


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
        bg_files = [os.path.join(bg_dir, f) for f in files if f.startswith('bg_')]
        if not bg_files:
            bg_files = [os.path.join(bg_dir, f) for f in files if f.startswith('loop_')]

    if not bg_files:
        logger.warning("⚠️ Không tìm thấy nhạc nền. Video sẽ im lặng.")
        return AudioSegment.silent(duration=duration_ms)

    # 2. Logic ghép nhạc
    segment_duration = duration_ms // len(bg_files)
    final_bg = AudioSegment.empty()
    last_track = None

    for i, fpath in enumerate(bg_files):
        track = load_audio(fpath)
        if not track: continue
        last_track = track

        # Điều chỉnh âm lượng (Giữ nguyên)
        if 0 < i < len(bg_files) - 1:
            track = track + VOL_MUSIC_HIGH 
        else:
            track = track + VOL_MUSIC_LOW

        # Loop track cho đủ độ dài segment 
        while len(track) < segment_duration + 5000: 
            track += track
        
        target_len = segment_duration if i < len(bg_files) - 1 else (duration_ms - len(final_bg))
        if target_len <= 0: target_len = 1000 
        track = track[:target_len]

        # Ghép nối (Crossfade an toàn)
        if len(final_bg) > 0:
            crossfade_duration = get_safe_crossfade(len(final_bg), len(track), max_cf=2000)
            final_bg = final_bg.append(track, crossfade=crossfade_duration)
        else:
            final_bg = track

    # 3. Lặp lại track cuối nếu audio quá ngắn 
    if len(final_bg) < duration_ms and last_track:
        remaining_ms = duration_ms - len(final_bg)
        logger.info(f"   (LOOP): Nhạc nền quá ngắn, lặp lại track cuối ({remaining_ms/1000:.1f}s còn lại).")
        
        if VOL_MUSIC_HIGH < VOL_MUSIC_LOW:
             last_track = last_track + VOL_MUSIC_HIGH
        else:
             last_track = last_track + VOL_MUSIC_LOW 
        
        looped_part = AudioSegment.empty()
        for _ in range(30): 
            if len(looped_part) >= remaining_ms: break
            
            if len(looped_part) > 0:
                 crossfade_duration = get_safe_crossfade(len(looped_part), len(last_track), max_cf=1000) 
                 looped_part = looped_part.append(last_track, crossfade=crossfade_duration)
            else:
                 looped_part = last_track
            
        crossfade_duration = get_safe_crossfade(len(final_bg), len(looped_part[:remaining_ms]), max_cf=2000)
        final_bg = final_bg.append(looped_part[:remaining_ms], crossfade=crossfade_duration)

    # Cắt chính xác lần cuối
    return final_bg[:duration_ms]


# =========================================================
# 🔊 HÀM CHÈN SFX (ĐÃ KHÔI PHỤC VỊ TRÍ)
# =========================================================
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


# =========================================================
# 🎧 MAIN FUNCTION
# =========================================================
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
        # ⚠️ FIX: Giờ đây inject_sfx đã được định nghĩa ở trên.
        mixed = inject_sfx(mixed, duration_ms) 

        # 4. Thêm Intro / Outro 
        intro_path = get_path('assets', 'intro_outro', 'intro.mp3')
        outro_path = get_path('assets', 'intro_outro', 'outro.mp3')
        
        final_audio = mixed 

        # --- LOGIC THÊM INTRO ---
        if os.path.exists(intro_path):
            intro = load_audio(intro_path)
            if intro:
                intro = intro + VOL_INTRO
                crossfade_duration = get_safe_crossfade(len(intro), len(final_audio), max_cf=1000)
                final_audio = intro.append(final_audio, crossfade=crossfade_duration)
                logger.info("🎬 Đã thêm Intro vào đầu Video.")

        # --- LOGIC THÊM OUTRO ---
        if os.path.exists(outro_path):
            outro = load_audio(outro_path)
            if outro:
                outro = outro + VOL_INTRO
                crossfade_duration = get_safe_crossfade(len(final_audio), len(outro), max_cf=1000)
                final_audio = final_audio.append(outro, crossfade=crossfade_duration)
                logger.info("🔚 Đã thêm Outro vào cuối Video.")

        # Xuất file 
        output_path = get_path('outputs', 'audio', f"{episode_id}_mixed.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final_audio.export(output_path, format="mp3") 
        logger.info(f"✅ Audio Mixing Complete: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi Auto Music SFX: {e}", exc_info=True)
        return None
