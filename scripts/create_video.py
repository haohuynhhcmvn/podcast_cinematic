# === scripts/create_video.py ===
# ĐÂY LÀ PHIÊN BẢN ĐÃ FIX LỖI RENDER VÀ TỐI ƯU HÓA CHO PYTHON 3.12

# 1. KHAI BÁO THƯ VIỆN (IMPORTS)
import logging  # Thư viện ghi nhật ký hoạt động (Log)
import os       # Thư viện tương tác với hệ điều hành (File/Folder)
import numpy as np # Thư viện xử lý toán học và ma trận ảnh
import math     # Các hàm toán học cơ bản
from pydub import AudioSegment # Thư viện xử lý file âm thanh
# Thư viện xử lý ảnh tĩnh (Pillow)
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageChops

# --- [FIX QUAN TRỌNG] VÁ LỖI TƯƠNG THÍCH PILLOW/MOVIEPY ---
# Nguyên nhân: MoviePy 1.0.3 sử dụng 'ANTIALIAS' để làm mượt ảnh khi resize.
# Tuy nhiên, các phiên bản Pillow mới (10.0+) đã xóa bỏ 'ANTIALIAS'.
# Giải pháp: Ta kiểm tra xem nếu thiếu thì tự động gán lại bằng hằng số mới (LANCZOS).
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    if hasattr(PIL.Image, 'Resampling') and hasattr(PIL.Image.Resampling, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS
    elif hasattr(PIL.Image, 'LANCZOS'):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# -----------------------------------------------------------

# Import thư viện dựng phim MoviePy
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, VideoClip, TextClip, concatenate_videoclips,
    vfx # Module chứa các hiệu ứng hình ảnh (Video Effects)
)
from utils import get_path # Hàm tiện ích lấy đường dẫn file

# Thiết lập Logger để ghi lại lỗi và thông tin
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ĐỘ PHÂN GIẢI VIDEO (HD 720p) ---
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
# ---------------------------------------------


# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT (KỸ THUẬT: DOUBLE EXPOSURE BLEND)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: Xử lý ảnh nhân vật để hòa trộn vào nền một cách nghệ thuật.
    Kỹ thuật: Tạo Mask làm mềm viền (Soft Edge) và giảm độ đậm (Opacity).
    """
    logger.info("   (LOG-BG): Bắt đầu xử lý ảnh nhân vật (Double Exposure Mix)...")
    
    # Tạo một ảnh rỗng trong suốt (RGBA) để làm canvas
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            # Load ảnh nhân vật gốc
            char_img = Image.open(char_path).convert("RGBA")
            
            # --- Bước 1: Resize ảnh ---
            # Tính toán tỷ lệ để ảnh cao bằng khung hình video (Fill Height)
            new_char_h = height 
            new_char_w = int(char_img.width * (new_char_h / char_img.height))
            # Dùng LANCZOS để ảnh sắc nét sau khi resize
            char_img = char_img.resize((new_char_w, new_char_h), Image.LANCZOS)
            
            # --- Bước 2: Tạo Mask Hòa Trộn (Quan trọng) ---
            
            # Lấy kênh Alpha (độ trong suốt) của ảnh gốc
            original_alpha = char_img.getchannel("A")
            
            # Thu nhỏ vùng hiển thị vào trong 25 pixel (để loại bỏ viền răng cưa)
            shrink_radius = 25
            eroded_mask = original_alpha.filter(ImageFilter.MinFilter(shrink_radius))
            
            # Làm mờ biên cực mạnh (45px) để tạo hiệu ứng "tan biến" vào nền
            blur_radius = 45 
            soft_edge_mask = eroded_mask.filter(ImageFilter.GaussianBlur(blur_radius))
            
            # --- Bước 3: Giảm độ đậm toàn thân ---
            # Tạo một lớp mặt nạ xám (giá trị 190/255 -> khoảng 75% độ đậm)
            blend_opacity = 190 
            opacity_layer = Image.new("L", soft_edge_mask.size, blend_opacity)
            
            # Kết hợp Mask viền mềm và Mask độ đậm lại với nhau
            final_mask = ImageChops.multiply(soft_edge_mask, opacity_layer)

            # --- Bước 4: Đặt vị trí ---
            # Canh giữa theo chiều ngang, sát đáy theo chiều dọc
            paste_x = (width - new_char_w) // 2 
            paste_y = height - new_char_h       
            
            # Dán ảnh nhân vật lên canvas rỗng, sử dụng final_mask để cắt
            final_overlay.paste(char_img, (paste_x, paste_y), mask=final_mask)
            logger.info(f"   (LOG-BG): ✅ Nhân vật đã Blend: Alpha={blend_opacity}, SoftBlur={blur_radius}.")
            
        except Exception as e:
            logger.error(f"   (LOG-BG): ❌ Lỗi xử lý nhân vật: {e}")

    # Lưu kết quả ra file tạm (PNG giữ kênh Alpha)
    overlay_path = get_path('assets', 'temp', "char_blend_mix.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    
    return overlay_path


# ============================================================
# 🎥 HÀM 2: TẠO NỀN "DREAMY CINEMATIC" (PHỐI CẢNH 3 LỚP)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: Tạo nền động phức hợp.
    Cấu trúc Layer (từ dưới lên trên):
    1. Ảnh nền tĩnh (Background) - Tăng độ tương phản.
    2. Ảnh nhân vật (Middleground) - Đã xử lý ở hàm trên.
    3. Video hiệu ứng (Foreground) - Mây bay/bụi, phủ mờ lên trên cùng.
    """
    logger.info("   (LOG-BG): Bắt đầu phối cảnh (Cinematic Layering)...")
    try:
        layers_to_composite = []

        # --- LỚP 1: ẢNH NỀN TĨNH (ĐÁY) ---
        if static_bg_path and os.path.exists(static_bg_path):
            # Tạo clip từ ảnh, kéo dài thời lượng bằng audio
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            # Resize và Crop để lấp đầy màn hình 16:9
            img_clip = img_clip.resize(height=height)
            img_clip = img_clip.crop(x_center=img_clip.w/2, y_center=img_clip.h/2, width=width, height=height)
            
            # Hiệu chỉnh màu: Giảm sáng (0.9) và Tăng tương phản (0.2) để làm nền tối đi
            img_clip = img_clip.fx(vfx.colorx, factor=0.9).fx(vfx.lum_contrast, contrast=0.2)
            layers_to_composite.append(img_clip)
            logger.info("   (LOG-BG): ✅ [Lớp 1] Ảnh nền tĩnh (Contrast Tăng).")

        # --- LỚP 2: NHÂN VẬT (GIỮA) ---
        if os.path.exists(char_overlay_path):
            char_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers_to_composite.append(char_clip)
            logger.info("   (LOG-BG): ✅ [Lớp 2] Nhân vật (Đã Blend).")

        # --- LỚP 3: VIDEO HIỆU ỨNG (TRÊN CÙNG) ---
        try:
            temp_clip = VideoFileClip(video_path)
            
            # Logic lặp: Nếu video ngắn hơn audio, nối lặp lại (Loop)
            if temp_clip.duration < duration:
                num_loops = math.ceil(duration / temp_clip.duration)
                looped_clips = [temp_clip] * num_loops
                final_video = concatenate_videoclips(looped_clips, method="compose")
            else:
                final_video = temp_clip
            
            # Cắt đúng thời lượng và Resize
            video_layer = final_video.subclip(0, duration)
            video_layer = video_layer.resize(height=height) 
            video_layer = video_layer.crop(x_center=video_layer.w/2, y_center=video_layer.h/2, width=width, height=height)
            
            # Làm mờ video này (Opacity 35%) để nó không che mất nhân vật
            # Tăng sáng (1.1) để tạo cảm giác lung linh (dreamy)
            video_layer = video_layer.set_opacity(0.35).fx(vfx.colorx, factor=1.1)

            layers_to_composite.append(video_layer)
            logger.info("   (LOG-BG): ✅ [Lớp 3] Video Overlay (Mờ ảo).")
            
        except Exception as e:
            logger.error(f"   (LOG-BG): ❌ Lỗi video overlay: {e}")

        # Nếu không có layer nào, trả về màn hình đen (Fallback)
        if not layers_to_composite:
            return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)
            
        # Tổng hợp 3 lớp lại thành 1 video clip
        final_bg_clip = CompositeVideoClip(layers_to_composite, size=(width, height))
        return final_bg_clip.set_duration(duration)
        
    except Exception as e:
        logger.error(f"❌ Lỗi tổng hợp nền: {e}", exc_info=True)
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)


# ============================================================
# 🌊 HÀM 3: TẠO SÓNG NHẠC (AUDIO VISUALIZER)
# ============================================================
def make_circular_waveform(audio_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: Tạo hiệu ứng sóng nhạc hình tròn đập theo điệu nhạc.
    Cách hoạt động: Đọc file âm thanh -> Lấy biên độ (Volume) -> Vẽ vòng tròn bán kính thay đổi.
    """
    calc_w, calc_h = 500, 500 # Kích thước khung vẽ tạm thời
    fps = 20 # Tốc độ khung hình của sóng nhạc
    
    logger.info("   (LOG-WF): Tạo Waveform (Elegant Mode)...")
    try:
        # Đọc dữ liệu âm thanh thô
        audio = AudioSegment.from_file(audio_path)
        raw_samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        # Nếu là stereo (2 kênh), lấy trung bình cộng để thành mono
        if audio.channels == 2:
            raw_samples = raw_samples.reshape((-1, 2)).mean(axis=1)
        
        # Tính toán biên độ trung bình cho từng khung hình (Envelope)
        num_frames = int(duration * fps) + 1
        envelope = []
        step = len(raw_samples) // num_frames
        if step == 0: step = 1
        for i in range(0, len(raw_samples), step):
            chunk = raw_samples[i:i+step]
            if len(chunk) > 0: envelope.append(np.mean(np.abs(chunk)))
            if len(envelope) >= num_frames: break
        
        # Chuẩn hóa dữ liệu về khoảng 0.0 - 1.0
        envelope = np.array(envelope)
        max_val = np.max(envelope) if len(envelope) > 0 else 1
        if max_val > 0: envelope = envelope / max_val 

        # --- Chuẩn bị ma trận khoảng cách để vẽ hình tròn ---
        waves = 8  # Số lượng vòng tròn
        center = (calc_w // 2, calc_h // 2)
        yy, xx = np.ogrid[:calc_h, :calc_w]
        dist_sq = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
        dist_matrix = np.sqrt(dist_sq)

        # Hàm vẽ cho từng khung hình (Frame Generator)
        def make_mask_frame(t):
            frame_idx = int(t * fps)
            frame_idx = min(frame_idx, len(envelope) - 1)
            amp = envelope[frame_idx] # Biên độ tại thời điểm t
            
            # Tạo khung hình đen
            mask_frame = np.zeros((calc_h, calc_w), dtype=np.float32)
            
            # Bán kính cơ bản + độ nảy theo âm nhạc
            base_radius = 40 + amp * 60 
            
            for i in range(waves):
                # Mỗi vòng cách nhau 25px
                radius = base_radius + i * 25 
                
                # Độ mờ giảm dần ra xa tâm
                opacity = max(0.0, 1.0 - i * 0.12)
                if opacity <= 0: continue
                
                # Vẽ vòng tròn (Ring) mảnh (độ dày 0.6)
                ring_mask = (dist_matrix >= radius - 0.3) & (dist_matrix <= radius + 0.3)
                mask_frame[ring_mask] = opacity
            return mask_frame

        # Tạo VideoClip từ hàm vẽ trên (đây là Clip mặt nạ đen trắng)
        mask_clip_low_res = VideoClip(make_mask_frame, duration=duration, ismask=True).set_fps(fps)
        mask_clip_high_res = mask_clip_low_res.resize((width, height))
        
        # Tạo Clip màu Vàng Gold
        color_clip = ColorClip(size=(width, height), color=(255, 215, 0), duration=duration) 
        
        # Áp dụng mặt nạ vào Clip màu -> Chỉ hiện màu vàng ở nơi có vòng tròn
        return color_clip.set_mask(mask_clip_high_res)
    
    except Exception as e:
        logger.error(f"❌ Lỗi Waveform: {e}")
        return ColorClip(size=(width, height), color=(0, 0, 0, 0), duration=duration)


# ============================================================
# ✨ HÀM 4: LỚP GLOW (HIỆU ỨNG SÁNG TÂM)
# ============================================================
def make_glow_layer(duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: Tạo một vùng sáng nhẹ ở giữa và tối dần ra xung quanh (Vignette).
    Mục đích: Tập trung sự chú ý vào nhân vật ở trung tâm.
    """
    low_w, low_h = 320, 180 # Vẽ ở độ phân giải thấp cho nhanh
    y = np.linspace(0, low_h - 1, low_h)
    x = np.linspace(0, low_w - 1, low_w)
    xx, yy = np.meshgrid(x, y)
    
    # Tâm sáng lệch lên trên một chút (nơi khuôn mặt nhân vật)
    lcx, lcy = low_w // 2, int(low_h * 0.45) 
    radius = int(min(low_w, low_h) * 0.45)
    dist = np.sqrt((xx - lcx)**2 + (yy - lcy)**2)
    
    # Tính toán độ sáng (Càng xa tâm càng tối)
    intensity = np.clip(255 - (dist / radius) * 255, 0, 255)
    
    # Tạo ảnh màu vàng cam nhạt
    glow_low = np.zeros((low_h, low_w, 3), dtype=np.uint8)
    glow_low[:, :, 0] = (intensity * 0.7).astype(np.uint8) # Red
    glow_low[:, :, 1] = (intensity * 0.5).astype(np.uint8) # Green
    glow_low[:, :, 2] = 0                                  # Blue
    
    return ImageClip(glow_low).resize((width, height)).set_duration(duration).set_opacity(0.3)

# ============================================================
# 🎬 HÀM CHÍNH: TẠO VIDEO (MAIN PIPELINE)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        # Bước 1: Đọc file âm thanh
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"   (LOG): Audio Duration = {duration:.2f}s") 

        # Bước 2: Tạo các lớp hình ảnh (Assets Generation)
        # - Lớp Nhân vật
        char_overlay_path = create_static_overlay_image(custom_image_path)
        
        # - Đường dẫn tài nguyên tĩnh
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        static_bg_path = get_path('assets', 'images', 'default_background.png')
        
        # - Lớp Nền Phức hợp (Hybrid Background)
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)
        background_clip = background_clip.set_duration(duration)

        # - Lớp Hiệu ứng (Glow & Waveform)
        glow_layer = make_glow_layer(duration)
        #waveform_layer = make_circular_waveform(audio_path, duration)
        
        # --- [FIX LỖI QUAN TRỌNG: i8 & AXES DON'T MATCH] ---
        
        # 1. Hàm ép kiểu dữ liệu an toàn
        # MoviePy đôi khi trả về kiểu dữ liệu int64 gây lỗi cho bộ render, ta ép về uint8.
        def force_frame_uint8(get_frame, t):
            frame = get_frame(t)
            if frame.ndim == 3 and frame.dtype != np.uint8:
                return frame.astype(np.uint8)
            return frame
        
        # Áp dụng hàm ép kiểu cho waveform
        #waveform_layer = waveform_layer.fl(force_frame_uint8)
        
        # 2. VÔ HIỆU HÓA XOAY (DISABLED ROTATION)
        # Nguyên nhân lỗi "axes don't match array": Xoay layer chứa Mask 2D gây xung đột trục.
        # Giải pháp: Tắt xoay. Vì Waveform là hình tròn đồng tâm, xoay nó cũng không thay đổi gì về thị giác.
        # waveform_layer = waveform_layer.fx(vfx.rotate, angle=lambda t: t * 1) <--- ĐÃ TẮT
        
        # Đặt vị trí sóng nhạc ở giữa màn hình
        #waveform_layer = waveform_layer.set_position(("center", 50)) 

        # Bước 3: Thêm Tiêu đề (Text Overlay)
        title_layer = None
        if title_text:
            try:
                title_layer = TextClip(
                    title_text.upper(),
                    fontsize=55, font='DejaVu-Sans-Bold', color='#FFD700', 
                    stroke_color='black', stroke_width=3, # Viền đen cho chữ dễ đọc
                    method='caption', align='West', size=(800, None)       
                ).set_position((50, 50)).set_duration(duration)
            except Exception as e:
                logger.warning(f"⚠️ Title Error: {e}")

        # Bước 4: Thêm Logo Kênh (Watermark)
        logo_path = get_path('assets', 'images', 'channel_logo.png')
        logo_layer = None
        if os.path.exists(logo_path):
            logo_layer = ImageClip(logo_path).set_duration(duration).resize(height=100).set_position(("right", "top")).margin(right=20, top=20, opacity=0)

        # Bước 5: Tổng hợp tất cả các lớp (Compositing)
        # Thứ tự danh sách quyết định thứ tự vẽ (Layer sau đè lên Layer trước)
        final_layers = [background_clip, glow_layer, waveform_layer]
        if title_layer: final_layers.append(title_layer)
        if logo_layer: final_layers.append(logo_layer)
        
        logger.info("   (LOG): Compositing...")
        # Tạo video cuối cùng và gắn âm thanh vào
        final_video = CompositeVideoClip(final_layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        # Bước 6: Xuất file (Rendering)
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        logger.info(f"🚀 RENDER START: {output_path}")
        # Cấu hình FFmpeg tối ưu tốc độ:
        # - fps=20: Đủ mượt cho dạng video tĩnh, render nhanh.
        # - preset="ultrafast": Ưu tiên tốc độ render.
        # - threads=2: Dùng 2 nhân CPU (phù hợp máy ảo miễn phí).
        final_video.write_videofile(
            output_path, fps=20, codec="libx264", audio_codec="aac", 
            preset="ultrafast", threads=4, ffmpeg_params=["-crf", "28"], logger='bar' 
        )
        logger.info(f"✅ RENDER SUCCESS!")
        return output_path

    except Exception as e:
        logger.error(f"❌ FATAL ERROR: {e}", exc_info=True)
        return False
