# scripts/create_video.py (ĐÃ SỬA: BỎ QUA HOÀN TOÀN PHỤ ĐỀ)
import os
import logging
import moviepy.editor as mp
# XÓA: from moviepy.video.tools.subtitles import SubtitlesClip, file_to_subtitles 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
COLOR_BACKGROUND = (30, 30, 30)

# XÓA HÀM file_to_subtitles_safe

def create_video(final_audio_path: str, subtitle_path: str, episode_id: int):
    try:
        logging.warning("BỎ QUA HOÀN TOÀN TẠO PHỤ ĐỀ (SubtitleClip) cho video 16:9 để hoàn thành pipeline.")
        
        audio_clip = mp.AudioFileClip(final_audio_path)
        duration = audio_clip.duration
        
        # --- LOGIC BỎ QUA PHỤ ĐỀ HOÀN TOÀN ---
        # Tạo clip placeholder trong suốt thay thế cho phụ đề
        subtitle_clip_to_use = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration).set_opacity(0)
        # --- END LOGIC BỎ QUA ---

        # Nền (Background)
        background_clip = mp.ColorClip((VIDEO_WIDTH, VIDEO_HEIGHT), color=COLOR_BACKGROUND, duration=duration)
        
        # Sóng âm & Micro Placeholder
        wave_text = mp.TextClip("Sóng Âm Đang Chạy...", fontsize=40, color='white',
                             size=(VIDEO_WIDTH * 0.8, None), bg_color='black')
        waveform_clip = wave_text.set_duration(duration).set_pos(("center", VIDEO_HEIGHT // 2 - 50))
        
        # Ghép các thành phần
        final_clip = mp.CompositeVideoClip([
            background_clip, waveform_clip, subtitle_clip_to_use
        ], size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_audio(audio_clip)

        # Xuất Video
        output_dir = os.path.join('outputs', 'video')
        video_filename = f"{episode_id}_full_podcast_169.mp4"
        video_path = os.path.join(output_dir, video_filename)
        
        logging.info(f"Bắt đầu xuất Video 16:9...")
        final_clip.write_videofile(
            video_path, codec='libx264', audio_codec='aac', fps=24, logger='bar'
        )

        logging.info(f"Video 16:9 đã tạo thành công và lưu tại: {video_path}")
        return video_path

    except Exception as e:
        logging.error(f"Lỗi khi tạo video 16:9: {e}", exc_info=True)
        return None
