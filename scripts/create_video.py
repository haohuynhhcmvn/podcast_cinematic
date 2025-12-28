# === scripts/create_video.py ===
import logging
import os
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, 
    CompositeVideoClip, TextClip, vfx, ColorClip
)
from utils import get_path

logger = logging.getLogger(__name__)

# Thông số khung hình & Tốc độ
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
TARGET_FPS = 12  # Giảm FPS xuống 12 để tăng tốc render gấp đôi

def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        # 1. Tải Audio chính
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"⏳ Audio duration: {duration:.2f}s")

        # 2. Xử lý Video Nền (Vì bạn xác nhận không có âm thanh)
        bg_video_path = get_path("assets", "video", "long_background.mp4")
        
        if os.path.exists(bg_video_path):
            # Lưu ý quan trọng: dùng audio=False để MoviePy bỏ qua hoàn toàn luồng âm thanh
            bg_clip = VideoFileClip(bg_video_path, audio=False)
            
            # Tối ưu: Resize & Crop ngay lập tức
            bg_clip = bg_clip.resize(height=OUTPUT_HEIGHT)
            if bg_clip.w > OUTPUT_WIDTH:
                bg_clip = bg_clip.crop(x_center=bg_clip.w/2, width=OUTPUT_WIDTH)
            
            # Lặp lại video cho đến khi đủ thời lượng audio
            bg_clip = bg_clip.fx(vfx.loop, duration=duration).set_opacity(0.4)
            logger.info("🎬 Đã tải Video Background (Silent Mode)")
        else:
            logger.warning("⚠️ Không tìm thấy file long_background.mp4")
            bg_clip = ColorClip(size=(OUTPUT_WIDTH, OUTPUT_HEIGHT), color=(15, 15, 15)).set_duration(duration)

        # 3. Ảnh nhân vật (Character Overlay)
        layers = [bg_clip]
        if custom_image_path and os.path.exists(custom_image_path):
            char_clip = (
                ImageClip(custom_image_path)
                .set_duration(duration)
                .resize(height=OUTPUT_HEIGHT * 0.9) # Nhân vật chiếm 90% chiều cao
                .set_position(("right", "bottom"))
            )
            layers.append(char_clip)

        # 4. Tiêu đề (Title)
        if title_text:
            try:
                title = (
                    TextClip(
                        title_text.upper(), 
                        fontsize=55, 
                        color='white', 
                        font='DejaVu-Sans-Bold',
                        method='caption',
                        size=(800, None), 
                        align='West'
                    )
                    .set_position((50, 'center'))
                    .set_duration(duration)
                )
                layers.append(title)
            except Exception as e:
                logger.warning(f"⚠️ Title Render Error: {e}")

        # 5. Render Final
        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        out_path = get_path("outputs", "video", f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        logger.info(f"🚀 Bắt đầu Render (FPS={TARGET_FPS}, CRF=32, Preset=ultrafast)...")
        
        final.write_videofile(
            out_path,
            fps=TARGET_FPS,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=4, # GitHub Actions hỗ trợ tốt 4 threads cho tác vụ nén
            ffmpeg_params=["-crf", "32"],
            logger=None # Tắt thanh tiến trình để giảm tải log
        )

        # Giải phóng bộ nhớ (Cực kỳ quan trọng trên CI/CD)
        final.close()
        audio.close()
        bg_clip.close()
        
        logger.info(f"✅ Render thành công: {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng tại create_video: {e}", exc_info=True)
        return False
