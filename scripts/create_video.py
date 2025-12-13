# === scripts/create_video.py ===

# 1. KHAI BÁO THƯ VIỆN
import logging          # Để ghi lại nhật ký hoạt động (log)
import os               # Để thao tác với file và đường dẫn hệ thống
import numpy as np      # Để tính toán toán học (dùng cho sóng nhạc)
import math             # Các hàm toán học cơ bản (làm tròn, trần...)
from pydub import AudioSegment  # Để đọc và xử lý file âm thanh
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw # Thư viện xử lý ảnh mạnh mẽ

# --- [FIX QUAN TRỌNG] VÁ LỖI PILLOW PHIÊN BẢN MỚI ---
# MoviePy dùng 'ANTIALIAS' nhưng Pillow mới đã đổi tên thành 'LANCZOS'.
# Đoạn này giúp code không bị lỗi khi chạy trên server mới.
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ------------------------------------------------------

# Import các công cụ làm video từ MoviePy
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, VideoClip, TextClip, concatenate_videoclips,
    vfx
)
# Import hàm lấy đường dẫn từ utils của dự án
from utils import get_path

# Khởi tạo logger để in thông báo ra màn hình
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ĐỘ PHÂN GIẢI OUTPUT (HD 720P) ---
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
# -----------------------------------------------


# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT (BÁN TRONG SUỐT)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: 
    1. Đọc ảnh nhân vật từ file.
    2. Thu nhỏ còn 60% chiều cao màn hình.
    3. Đặt vào giữa và sát đáy.
    4. Giảm độ đậm (Opacity) để nhìn xuyên qua (hiệu ứng Ghost).
    """
    logger.info("   (LOG-BG): Bắt đầu xử lý lớp phủ nhân vật (Transparent)...")
    
    # Tạo một tấm nền trống rỗng (trong suốt hoàn toàn) kích thước 1280x720
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    # Kiểm tra xem file ảnh nhân vật có tồn tại không
    if char_path and os.path.exists(char_path):
        try:
            # Mở ảnh và chuyển sang hệ màu RGBA (có kênh trong suốt)
            char_img = Image.open(char_path).convert("RGBA")
            
            # --- [BƯỚC 1] TÍNH TOÁN KÍCH THƯỚC ---
            # Muốn nhân vật cao bằng 60% chiều cao video (0.6)
            scale_factor = 0.5
            new_char_h = int(height * scale_factor)
            
            # Tính chiều rộng mới dựa trên tỷ lệ gốc (để ảnh không bị méo)
            # Công thức: Rộng mới = Rộng cũ * (Cao mới / Cao cũ)
            new_char_w = int(char_img.width * (new_char_h / char_img.height))
            
            # Thực hiện thay đổi kích thước ảnh (Resize) chất lượng cao (LANCZOS)
            char_img = char_img.resize((new_char_w, new_char_h), PIL.Image.LANCZOS)
            
            # --- [BƯỚC 2] TẠO ĐỘ TRONG SUỐT (OPACITY) ---
            # Đây là nơi chỉnh độ "nhìn xuyên thấu".
            # 255 = Đậm đặc (che hết nền).
            # 0   = Tàng hình.
            # 190 = Bán trong suốt (Nhìn thấy nền video phía sau).
            opacity_val = 190 
            
            # Tạo một lớp mặt nạ (Mask) màu xám có độ đậm bằng opacity_val
            mask = Image.new("L", (new_char_w, new_char_h), opacity_val)
            
            # --- [BƯỚC 3] TÍNH VỊ TRÍ DÁN (CENTER - BOTTOM) ---
            # Căn giữa theo chiều ngang: (Rộng màn hình - Rộng ảnh) chia 2
            paste_x = (width - new_char_w) // 2 
            
            # Sát đáy theo chiều dọc: Cao màn hình - Cao ảnh
            paste_y = height - new_char_h       
            
            # Dán ảnh nhân vật vào tấm nền trống tại vị trí đã tính, dùng mask để làm mờ
            final_overlay.paste(char_img, (paste_x, paste_y), mask=mask)
            
            logger.info(f"   (LOG-BG): ✅ Nhân vật đã xử lý: Cao {new_char_h}px, Alpha={opacity_val}.")
            
        except Exception as e:
            logger.error(f"   (LOG-BG): ❌ Lỗi khi xử lý ảnh nhân vật: {e}")

    # Tạo đường dẫn lưu file tạm
    overlay_path = get_path('assets', 'temp', "char_transparent_overlay.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    
    # Lưu file dưới dạng PNG để giữ được sự trong suốt (QUAN TRỌNG)
    final_overlay.save(overlay_path, format="PNG") 
    
    return overlay_path


# ============================================================
# 🎥 HÀM 2: TẠO NỀN VIDEO TỔNG HỢP (HYBRID BACKGROUND)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: Trộn 3 lớp lại với nhau theo thứ tự:
    1. Video động (Dưới cùng).
    2. Ảnh tĩnh (Ở giữa - mờ).
    3. Nhân vật (Trên cùng).
    """
    logger.info("   (LOG-BG): Bắt đầu trộn nền Video...")
    try:
        layers_to_composite = [] # Danh sách chứa các lớp
        base_clip = None         # Biến giữ clip gốc để kiểm tra

        # --- LỚP 1: VIDEO ĐỘNG (Lớp đáy) ---
        try:
            temp_clip = VideoFileClip(video_path)
            
            # Nếu video ngắn hơn thời lượng audio -> Lặp lại (Loop) video
            if temp_clip.duration < duration:
                num_loops = math.ceil(duration / temp_clip.duration)
                looped_clips = [temp_clip] * num_loops
                final_clip = concatenate_videoclips(looped_clips, method="compose")
            else:
                final_clip = temp_clip
            
            # Cắt video đúng bằng thời lượng audio
            base_clip = final_clip.subclip(0, duration)
            
            # Cắt cúp (Crop) video vào giữa để lấp đầy màn hình 16:9
            base_clip = base_clip.resize(height=height) 
            base_clip = base_clip.crop(x_center=base_clip.w/2, y_center=base_clip.h/2, width=width, height=height)
            
            # [CHỈNH MÀU] Giữ độ sáng 90% (0.9) để thấy rõ chuyển động
            base_clip = base_clip.fx(vfx.colorx, factor=0.9)
            
            # Thêm vào danh sách lớp
            layers_to_composite.append(base_clip)
            logger.info("   (LOG-BG): ✅ Lớp 1: Video nền động (Sáng 90%).")
            
        except Exception as video_e:
            logger.error(f"   (LOG-BG): ❌ Lỗi đọc video nền: {video_e}. Sẽ bỏ qua.")
            base_clip = None 

        # --- LỚP 2: HÌNH NỀN TĨNH (Lớp giữa) ---
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            
            # Resize và Crop ảnh cho vừa màn hình
            img_clip = img_clip.resize(height=height)
            img_clip = img_clip.crop(x_center=img_clip.w/2, y_center=img_clip.h/2, width=width, height=height)
            
            # [CHỈNH ĐỘ MỜ] Chỉ để 25% (0.25) để lộ video bên dưới
            if base_clip is not None:
                static_bg_clip = img_clip.set_opacity(0.25) 
            else:
                # Nếu không có video thì để ảnh rõ 100%
                static_bg_clip = img_clip.set_opacity(1.0) 
            
            layers_to_composite.append(static_bg_clip) 
            logger.info("   (LOG-BG): ✅ Lớp 2: Ảnh nền tĩnh (Mờ 25%).")

        # --- LỚP 3: NHÂN VẬT (Lớp trên cùng) ---
        if os.path.exists(char_overlay_path):
            # Load ảnh nhân vật đã xử lý ở Hàm 1
            overlay_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers_to_composite.append(overlay_clip)
            logger.info("   (LOG-BG): ✅ Lớp 3: Nhân vật bán trong suốt.")
        
        # Nếu không có lớp nào -> Trả về màn hình đen (Tránh lỗi crash)
        if not layers_to_composite:
            return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)
            
        # Trộn tất cả các lớp lại thành 1 video duy nhất
        final_bg_clip = CompositeVideoClip(layers_to_composite, size=(width, height))
        return final_bg_clip.set_duration(duration)
        
    except Exception as e:
        logger.error(f"❌ Lỗi tổng hợp nền: {e}", exc_info=True)
        # Fallback an toàn: Trả về nền đen
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)


# ============================================================
# 🌊 HÀM 3: TẠO SÓNG NHẠC (CIRCULAR WAVEFORM) - TỐI ƯU
# ============================================================
def make_circular_waveform(audio_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: Tạo hiệu ứng sóng tròn đập theo nhạc.
    Tối ưu: Tính toán ở độ phân giải thấp (400x400) để Render nhanh.
    """
    # Kích thước tính toán (Nhỏ để nhanh)
    calc_w, calc_h = 400, 400 
    fps = 20 # Số khung hình mỗi giây của sóng nhạc (20 là đủ mượt)
    
    logger.info("   (LOG-WF): Bắt đầu tạo Waveform...")
    try:
        # Đọc file âm thanh để lấy dữ liệu sóng
        audio = AudioSegment.from_file(audio_path)
        raw_samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        
        # Nếu là stereo (2 kênh) thì gộp lại thành mono
        if audio.channels == 2:
            raw_samples = raw_samples.reshape((-1, 2)).mean(axis=1)
        
        # Lấy mẫu biên độ âm thanh (Envelope)
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

        # Cấu hình vẽ vòng tròn
        waves = 15  # Số lượng vòng sóng
        center = (calc_w // 2, calc_h // 2)
        
        # Tạo lưới toạ độ (Matrix) để tính khoảng cách
        yy, xx = np.ogrid[:calc_h, :calc_w]
        dist_sq = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
        dist_matrix = np.sqrt(dist_sq)

        # Hàm vẽ từng khung hình
        def make_mask_frame(t):
            frame_idx = int(t * fps)
            frame_idx = min(frame_idx, len(envelope) - 1)
            amp = envelope[frame_idx] # Độ lớn âm thanh tại thời điểm t
            
            mask_frame = np.zeros((calc_h, calc_w), dtype=np.float32)
            base_radius = 20 + amp * 50 # Bán kính cơ bản thay đổi theo nhạc
            
            # Vẽ từng vòng sóng
            for i in range(waves):
                radius = base_radius + i * 10 
                opacity = max(0.0, 1.0 - i * 0.08) # Càng ra xa càng mờ
                if opacity <= 0: continue
                
                # Tạo vòng tròn
                ring_mask = (dist_matrix >= radius - 0.8) & (dist_matrix <= radius + 0.8)
                mask_frame[ring_mask] = opacity
            return mask_frame

        # Tạo clip từ hàm vẽ trên (độ phân giải thấp)
        mask_clip_low_res = VideoClip(make_mask_frame, duration=duration, ismask=True).set_fps(fps)
        
        # Phóng to clip lên độ phân giải HD
        mask_clip_high_res = mask_clip_low_res.resize((width, height))
        
        # Tạo clip màu vàng (Gold) và áp dụng mask sóng nhạc lên nó
        color_clip = ColorClip(size=(width, height), color=(255, 215, 0), duration=duration) 
        
        return color_clip.set_mask(mask_clip_high_res)
    
    except Exception as e:
        logger.error(f"❌ Lỗi Waveform: {e}")
        # Trả về clip rỗng nếu lỗi
        return ColorClip(size=(width, height), color=(0, 0, 0), duration=duration)


# ============================================================
# ✨ HÀM 4: TẠO LỚP PHÁT SÁNG (GLOW)
# ============================================================
def make_glow_layer(duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """ Tạo một đốm sáng mờ ảo phía sau sóng nhạc để đẹp hơn. """
    low_w, low_h = 320, 180
    y = np.linspace(0, low_h - 1, low_h)
    x = np.linspace(0, low_w - 1, low_w)
    xx, yy = np.meshgrid(x, y)
    lcx, lcy = low_w // 2, int(low_h * 0.45) 
    radius = int(min(low_w, low_h) * 0.45)
    
    # Tính toán độ sáng giảm dần từ tâm ra ngoài
    dist = np.sqrt((xx - lcx)**2 + (yy - lcy)**2)
    intensity = np.clip(255 - (dist / radius) * 255, 0, 255)
    
    # Tạo màu vàng cam
    glow_low = np.zeros((low_h, low_w, 3), dtype=np.uint8)
    glow_low[:, :, 0] = (intensity * 0.7).astype(np.uint8) # R
    glow_low[:, :, 1] = (intensity * 0.5).astype(np.uint8) # G
    glow_low[:, :, 2] = 0                                  # B
    
    return ImageClip(glow_low).resize((width, height)).set_duration(duration).set_opacity(0.3)

# ============================================================
# 🎬 HÀM CHÍNH: CREATE VIDEO (QUẢN LÝ TỔNG)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    try:
        # BƯỚC 1: XỬ LÝ AUDIO
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"   (LOG): Đang xử lý Audio. Thời lượng = {duration:.2f}s") 

        # BƯỚC 2: TẠO ẢNH NHÂN VẬT (GỌI HÀM 1)
        char_overlay_path = create_static_overlay_image(custom_image_path)
        
        # BƯỚC 3: CHUẨN BỊ TÀI NGUYÊN NỀN
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        static_bg_path = get_path('assets', 'images', 'default_background.png')
        
        # BƯỚC 4: TẠO NỀN TỔNG HỢP (GỌI HÀM 2)
        clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)
        clip = clip.set_duration(duration)

        # BƯỚC 5: TẠO HIỆU ỨNG TRÊN CÙNG (GỌI HÀM 3 & 4)
        glow = make_glow_layer(duration)
        waveform = make_circular_waveform(audio_path, duration)
        
        # [QUAN TRỌNG] Đẩy sóng nhạc lên cao ("top") cách lề trên 50px
        # Lý do: Nhân vật đang ngồi giữa, nếu để center thì sóng đè lên mặt.
        waveform = waveform.set_position(("center", 50))

        # BƯỚC 6: TẠO TIÊU ĐỀ (TEXT)
        title_layer = None
        if title_text:
            try:
                # Đặt text ở góc Trái - Trên (West, 50, 50)
                title_layer = TextClip(
                    title_text.upper(),
                    fontsize=55, font='DejaVu-Sans-Bold', color='#FFD700', stroke_color='black', stroke_width=3,
                    method='caption', align='West', size=(800, None)       
                ).set_position((50, 50)).set_duration(duration)
            except Exception as e:
                logger.warning(f"⚠️ Không tạo được Title: {e}")

        # BƯỚC 7: LOGO KÊNH
        logo_path = get_path('assets', 'images', 'channel_logo.png')
        logo_layer = None
        if os.path.exists(logo_path):
            logo_layer = ImageClip(logo_path).set_duration(duration).resize(height=100).set_position(("right", "top")).margin(right=20, top=20, opacity=0)

        # BƯỚC 8: TỔNG HỢP CUỐI CÙNG (COMPOSITE)
        # Xếp lớp theo thứ tự: Nền -> Sáng -> Sóng nhạc -> Chữ -> Logo
        layers = [clip, glow, waveform]
        if title_layer: layers.append(title_layer)
        if logo_layer: layers.append(logo_layer)
        
        logger.info("   (LOG): Đang ghép tất cả các lớp lại với nhau...")
        final = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        # BƯỚC 9: RENDER (XUẤT RA FILE MP4)
        output = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        logger.info("🚀 PHASE RENDER: Bắt đầu xuất file video (Tối ưu hóa)...")
        
        # Cấu hình Render tối ưu cho GitHub Actions:
        # - fps=20: Đủ dùng, render nhanh.
        # - preset='ultrafast': Tốc độ nhanh nhất.
        # - threads=2: Phù hợp với CPU 2 nhân của gói Free.
        final.write_videofile(
            output, 
            fps=20, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast", 
            threads=2, 
            ffmpeg_params=["-crf", "28"], # Chất lượng trung bình khá, file nhẹ
            logger='bar' 
        )
        logger.info(f"✅ XUẤT VIDEO THÀNH CÔNG: {output}")
        return output

    except Exception as e:
        logger.error(f"❌ LỖI NGHIÊM TRỌNG (FATAL ERROR): {e}", exc_info=True)
        return False
