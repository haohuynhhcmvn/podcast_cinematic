# scripts/auto_music_sfx.py
import os
import logging
import random
from pydub import AudioSegment
from utils import get_path

logger = logging.getLogger(__name__)

# --- CẤU HÌNH ---
VOL_VOICE = 0           # Giọng đọc giữ nguyên
VOL_MUSIC = -20         # Nhạc nền nhỏ xuống -20dB
VOL_INTRO_OUTRO = -5    # Intro/Outro to vừa phải

def load_audio_safe(path):
    if os.path.exists(path):
        try:
            return AudioSegment.from_file(path)
        except Exception as e:
            logger.warning(f"⚠️ File lỗi không đọc được: {path} ({e})")
    return None

def auto_music_sfx(episode_id, voice_path):
    """
    Tự động trộn nhạc nền + Intro + Outro.
    Nếu thiếu file nhạc, nó sẽ tự động bỏ qua để không crash hệ thống.
    """
    logger.info(f"🎚️ Đang xử lý âm thanh cho: {episode_id}")

    if not voice_path or not os.path.exists(voice_path):
        logger.error("❌ Không tìm thấy file giọng đọc đầu vào!")
        return None

    try:
        # 1. Load Giọng đọc (Voice)
        voice = AudioSegment.from_file(voice_path)
        final_audio = voice # Mặc định là giọng mộc nếu không có nhạc
        
        # 2. Load Nhạc nền (Background Music)
        bg_music_dir = get_path('assets', 'background_music')
        bg_music = None
        
        if os.path.exists(bg_music_dir):
            files = [f for f in os.listdir(bg_music_dir) if f.endswith(('.mp3', '.wav'))]
            if files:
                selected_bg = random.choice(files)
                bg_path = os.path.join(bg_music_dir, selected_bg)
                logger.info(f"🎵 Đã chọn nhạc nền: {selected_bg}")
                
                bg_raw = load_audio_safe(bg_path)
                if bg_raw:
                    # Chỉnh âm lượng nhạc nền
                    bg_raw = bg_raw + VOL_MUSIC
                    
                    # Loop nhạc nền cho bằng độ dài giọng đọc
                    while len(bg_raw) < len(voice) + 5000: # Cộng thêm 5s dư
                        bg_raw += bg_raw
                    
                    # Cắt bằng độ dài giọng đọc
                    bg_music = bg_raw[:len(voice)]
                    
                    # Overlay (Trộn)
                    final_audio = voice.overlay(bg_music)
            else:
                logger.warning("⚠️ Thư mục assets/background_music trống. Video sẽ không có nhạc nền.")
        else:
            logger.warning("⚠️ Chưa tạo thư mục assets/background_music.")

        # 3. Thêm Intro (Đầu video)
        intro_path = get_path('assets', 'intro_outro', 'intro.mp3')
        intro = load_audio_safe(intro_path)
        if intro:
            intro += VOL_INTRO_OUTRO
            final_audio = intro + final_audio
            logger.info("✅ Đã thêm Intro.")
        else:
            logger.info("ℹ️ Không tìm thấy Intro (assets/intro_outro/intro.mp3) -> Bỏ qua.")

        # 4. Thêm Outro (Cuối video)
        outro_path = get_path('assets', 'intro_outro', 'outro.mp3')
        outro = load_audio_safe(outro_path)
        if outro:
            outro += VOL_INTRO_OUTRO
            final_audio = final_audio + outro
            logger.info("✅ Đã thêm Outro.")
        else:
            logger.info("ℹ️ Không tìm thấy Outro (assets/intro_outro/outro.mp3) -> Bỏ qua.")

        # 5. Xuất file kết quả
        output_path = get_path('outputs', 'audio', f"{episode_id}_mixed.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final_audio.export(output_path, format="mp3")
        logger.info(f"✅ Hoàn tất mix âm thanh: {output_path}")
        
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi khi trộn âm thanh: {e}", exc_info=True)
        return None # Trả về None sẽ làm dừng pipeline
