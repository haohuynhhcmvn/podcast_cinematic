# === scripts/create_video.py ===

# 1. KHAI BÁO THƯ VIỆN
import logging          # Để ghi lại nhật ký hoạt động (log)
import os               # Để thao tác với file và đường dẫn hệ thống
import numpy as np      # Để tính toán toán học (dùng cho sóng nhạc)
import math             # Các hàm toán học cơ bản (làm tròn, trần...)
from pydub import AudioSegment  # Để đọc và xử lý file âm thanh
# Import các công cụ xử lý ảnh từ thư viện Pillow (PIL)
# ImageChops được thêm vào để xử lý chồng lớp mask
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageChops

# --- [FIX QUAN TRỌNG] VÁ LỖI PILLOW PHIÊN BẢN MỚI ---
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
# ------------------------------------------------------

# Import các công cụ làm video từ thư viện MoviePy
from moviepy.editor import (
    AudioFileClip, VideoFileClip, ImageClip, ColorClip,
    CompositeVideoClip, VideoClip, TextClip, concatenate_videoclips,
    vfx
)
# Import hàm lấy đường dẫn chuẩn từ file utils của dự án
from utils import get_path

# Khởi tạo đối tượng logger để ghi thông báo ra màn hình console
logger = logging.getLogger(__name__)

# --- CẤU HÌNH ĐỘ PHÂN GIẢI ĐẦU RA (CHUẨN HD 720P) ---
OUTPUT_WIDTH = 1280
OUTPUT_HEIGHT = 720
# -----------------------------------------------------


# ============================================================
# 🎨 HÀM 1: XỬ LÝ ẢNH NHÂN VẬT (LÀM MỀM VIỀN BÁM SÁT NHÂN VẬT)
# ============================================================
def create_static_overlay_image(char_path, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: Tạo lớp ảnh nhân vật.
    - Tính toán kích thước (thu nhỏ 60%).
    - [MỚI] Tạo mask làm mềm viền bám sát theo đường nét nhân vật (Contour Soft Edge).
    - Căn giữa và đặt sát đáy.
    """
    logger.info("   (LOG-BG): Bắt đầu xử lý ảnh nhân vật (Contour Soft Edge)...")
    
    # Tạo tấm nền trong suốt
    final_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    
    if char_path and os.path.exists(char_path):
        try:
            # Mở ảnh RGBA
            char_img = Image.open(char_path).convert("RGBA")
            
            # --- [BƯỚC 1] TÍNH TOÁN KÍCH THƯỚC (GIỮ NGUYÊN) ---
            scale_factor = 0.6 # Đặt chiều cao bằng 60% màn hình
            new_char_h = int(height * scale_factor)
            # Tính chiều rộng theo tỉ lệ ảnh gốc
            new_char_w = int(char_img.width * (new_char_h / char_img.height))
            
            # Resize ảnh chất lượng cao
            char_img = char_img.resize((new_char_w, new_char_h), PIL.Image.LANCZOS)
            
            # --- [BƯỚC 2] TẠO MASK LÀM MỀM VIỀN BÁM SÁT NHÂN VẬT (THUẬT TOÁN MỚI) ---
            
            # 2.1. Lấy kênh Alpha gốc: Đây là hình dáng chính xác của nhân vật (trắng) trên nền trong suốt (đen).
            original_alpha = char_img.getchannel("A")
            
            # 2.2. Co lại (Erosion): Dùng MinFilter để làm vùng trắng thu hẹp vào bên trong.
            # 'radius=15' nghĩa là làm mềm lấn vào trong nhân vật khoảng 15 pixel.
            shrink_radius = 15
            eroded_mask = original_alpha.filter(ImageFilter.MinFilter(shrink_radius))
            
            # 2.3. Làm mờ (Gaussian Blur): Làm mờ vùng đã co lại để tạo viền mềm mại.
            blur_radius = 15
            soft_shape_mask = eroded_mask.filter(ImageFilter.GaussianBlur(blur_radius))
            
            # 2.4. Áp dụng độ trong suốt tổng thể (Optional)
            # Nếu bạn vẫn muốn nhân vật hơi trong suốt để nhìn xuyên nền:
            opacity_val = 190 # Mức độ hiển thị (0-255). 190 là hơi trong suốt.
            # Tạo một lớp màu xám có độ đậm mong muốn
            opacity_layer = Image.new("L", (new_char_w, new_char_h), opacity_val)
            # Nhân chồng lớp hình dáng mềm (soft_shape_mask) với lớp độ đậm (opacity_layer)
            final_mask = ImageChops.multiply(soft_shape_mask, opacity_layer)

            # --- [BƯỚC 3] TÍNH VỊ TRÍ DÁN (CENTER - BOTTOM) ---
            paste_x = (width - new_char_w) // 2 
            paste_y = height - new_char_h       
            
            # --- [BƯỚC 4] DÁN ẢNH SỬ DỤNG MASK MỚI ---
            # Sử dụng final_mask vừa tạo để dán nhân vật.
            final_overlay.paste(char_img, (paste_x, paste_y), mask=final_mask)
            
            logger.info(f"   (LOG-BG): ✅ Nhân vật đã xử lý: Soft contour edge, Alpha={opacity_val}.")
            
        except Exception as e:
            logger.error(f"   (LOG-BG): ❌ Lỗi khi xử lý ảnh nhân vật: {e}")

    # Lưu file PNG để giữ trong suốt
    overlay_path = get_path('assets', 'temp', "char_contour_soft_overlay.png")
    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    final_overlay.save(overlay_path, format="PNG") 
    
    return overlay_path


# ============================================================
# 🎥 HÀM 2: TẠO NỀN VIDEO TỔNG HỢP (HYBRID BACKGROUND)
# ============================================================
def make_hybrid_video_background(video_path, static_bg_path, char_overlay_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: Trộn 3 lớp: Video động (đáy) + Ảnh tĩnh (giữa, mờ) + Nhân vật (trên cùng).
    """
    logger.info("   (LOG-BG): Bắt đầu trộn các lớp nền Video...")
    try:
        layers_to_composite = [] 
        base_clip = None         

        # --- LỚP 1: VIDEO ĐỘNG (Lớp đáy) ---
        try:
            temp_clip = VideoFileClip(video_path)
            # Xử lý loop video nếu ngắn
            if temp_clip.duration < duration:
                num_loops = math.ceil(duration / temp_clip.duration)
                looped_clips = [temp_clip] * num_loops
                final_clip = concatenate_videoclips(looped_clips, method="compose")
            else:
                final_clip = temp_clip
            
            # Cắt, resize, crop video nền
            base_clip = final_clip.subclip(0, duration)
            base_clip = base_clip.resize(height=height) 
            base_clip = base_clip.crop(x_center=base_clip.w/2, y_center=base_clip.h/2, width=width, height=height)
            
            # Giữ độ sáng 90%
            base_clip = base_clip.fx(vfx.colorx, factor=0.9)
            layers_to_composite.append(base_clip)
            logger.info("   (LOG-BG): ✅ Lớp 1: Video nền động (Sáng 90%).")
            
        except Exception as video_e:
            logger.error(f"   (LOG-BG): ❌ Lỗi đọc video nền: {video_e}. Bỏ qua.")
            base_clip = None 

        # --- LỚP 2: HÌNH NỀN TĨNH (Lớp giữa) ---
        if static_bg_path and os.path.exists(static_bg_path):
            img_clip = ImageClip(static_bg_path).set_duration(duration)
            img_clip = img_clip.resize(height=height)
            img_clip = img_clip.crop(x_center=img_clip.w/2, y_center=img_clip.h/2, width=width, height=height)
            
            # Chỉnh độ mờ 25% nếu có video nền
            if base_clip is not None:
                static_bg_clip = img_clip.set_opacity(0.25) 
            else:
                static_bg_clip = img_clip.set_opacity(1.0) 
            
            layers_to_composite.append(static_bg_clip) 
            logger.info(f"   (LOG-BG): ✅ Lớp 2: Ảnh nền tĩnh (Opacity={static_bg_clip.opacity}).")

        # --- LỚP 3: NHÂN VẬT (Lớp trên cùng) ---
        if os.path.exists(char_overlay_path):
            # Sử dụng ảnh PNG nhân vật đã xử lý viền mềm ở Hàm 1
            overlay_clip = ImageClip(char_overlay_path).set_duration(duration)
            layers_to_composite.append(overlay_clip)
            logger.info("   (LOG-BG): ✅ Lớp 3: Nhân vật (Contour Soft Edge).")
        
        if not layers_to_composite:
            return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)
            
        # Trộn các lớp
        final_bg_clip = CompositeVideoClip(layers_to_composite, size=(width, height))
        return final_bg_clip.set_duration(duration)
        
    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng khi tổng hợp nền: {e}", exc_info=True)
        return ColorClip(size=(width, height), color=(15, 15, 15), duration=duration)


# ============================================================
# 🌊 HÀM 3: TẠO SÓNG NHẠC (CIRCULAR WAVEFORM) - TỐI ƯU
# ============================================================
def make_circular_waveform(audio_path, duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """
    Chức năng: Tạo hiệu ứng sóng tròn. Tối ưu hóa tính toán ở độ phân giải thấp.
    """
    calc_w, calc_h = 400, 400 # Kích thước tính toán nhỏ
    fps = 20 
    
    logger.info("   (LOG-WF): Bắt đầu tạo Waveform (Chế độ tối ưu)...")
    try:
        # Xử lý audio lấy mẫu
        audio = AudioSegment.from_file(audio_path)
        raw_samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        if audio.channels == 2:
            raw_samples = raw_samples.reshape((-1, 2)).mean(axis=1)
        
        # Tính biên độ (envelope)
        num_frames = int(duration * fps) + 1
        envelope = []
        step = len(raw_samples) // num_frames
        if step == 0: step = 1
        for i in range(0, len(raw_samples), step):
            chunk = raw_samples[i:i+step]
            if len(chunk) > 0: envelope.append(np.mean(np.abs(chunk)))
            if len(envelope) >= num_frames: break
        envelope = np.array(envelope)
        max_val = np.max(envelope) if len(envelope) > 0 else 1
        if max_val > 0: envelope = envelope / max_val 

        # Cấu hình vẽ sóng
        waves = 15
        center = (calc_w // 2, calc_h // 2)
        yy, xx = np.ogrid[:calc_h, :calc_w]
        dist_sq = (xx - center[0]) ** 2 + (yy - center[1]) ** 2
        dist_matrix = np.sqrt(dist_sq)

        # Hàm vẽ khung hình
        def make_mask_frame(t):
            frame_idx = int(t * fps)
            frame_idx = min(frame_idx, len(envelope) - 1)
            amp = envelope[frame_idx]
            mask_frame = np.zeros((calc_h, calc_w), dtype=np.float32)
            base_radius = 20 + amp * 50 
            for i in range(waves):
                radius = base_radius + i * 10 
                opacity = max(0.0, 1.0 - i * 0.08)
                if opacity <= 0: continue
                ring_mask = (dist_matrix >= radius - 0.8) & (dist_matrix <= radius + 0.8)
                mask_frame[ring_mask] = opacity
            return mask_frame

        # Tạo clip và resize
        mask_clip_low_res = VideoClip(make_mask_frame, duration=duration, ismask=True).set_fps(fps)
        mask_clip_high_res = mask_clip_low_res.resize((width, height))
        color_clip = ColorClip(size=(width, height), color=(255, 215, 0), duration=duration) 
        final_waveform = color_clip.set_mask(mask_clip_high_res)
        
        logger.info("   (LOG-WF): ✅ Waveform clip hoàn tất.")
        return final_waveform
    
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo Waveform: {e}")
        return ColorClip(size=(width, height), color=(0, 0, 0, 0), duration=duration)


# ============================================================
# ✨ HÀM 4: TẠO LỚP PHÁT SÁNG NỀN (GLOW LAYER)
# ============================================================
def make_glow_layer(duration, width=OUTPUT_WIDTH, height=OUTPUT_HEIGHT):
    """ Tạo đốm sáng mờ ảo màu vàng cam ở giữa. """
    low_w, low_h = 320, 180
    y = np.linspace(0, low_h - 1, low_h)
    x = np.linspace(0, low_w - 1, low_w)
    xx, yy = np.meshgrid(x, y)
    lcx, lcy = low_w // 2, int(low_h * 0.45) 
    radius = int(min(low_w, low_h) * 0.45)
    dist = np.sqrt((xx - lcx)**2 + (yy - lcy)**2)
    intensity = np.clip(255 - (dist / radius) * 255, 0, 255)
    
    glow_low = np.zeros((low_h, low_w, 3), dtype=np.uint8)
    glow_low[:, :, 0] = (intensity * 0.7).astype(np.uint8) # R
    glow_low[:, :, 1] = (intensity * 0.5).astype(np.uint8) # G
    glow_low[:, :, 2] = 0                                  # B
    
    # Độ mờ 30%
    return ImageClip(glow_low).resize((width, height)).set_duration(duration).set_opacity(0.3)

# ============================================================
# 🎬 HÀM CHÍNH: CREATE VIDEO (QUẢN LÝ QUY TRÌNH TỔNG)
# ============================================================
def create_video(audio_path, episode_id, custom_image_path=None, title_text="LEGENDARY FOOTSTEPS"):
    """ Hàm chính điều phối việc tạo video. """
    try:
        # BƯỚC 1: XỬ LÝ AUDIO
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        logger.info(f"   (LOG): Đang xử lý Audio. Thời lượng = {duration:.2f}s") 

        # BƯỚC 2: TẠO LỚP ẢNH NHÂN VẬT (GỌI HÀM 1 MỚI)
        char_overlay_path = create_static_overlay_image(custom_image_path)
        
        # BƯỚC 3: CHUẨN BỊ TÀI NGUYÊN NỀN
        base_video_path = get_path('assets', 'video', 'long_background.mp4') 
        static_bg_path = get_path('assets', 'images', 'default_background.png')
        
        # BƯỚC 4: TẠO NỀN TỔNG HỢP (GỌI HÀM 2)
        background_clip = make_hybrid_video_background(base_video_path, static_bg_path, char_overlay_path, duration)
        background_clip = background_clip.set_duration(duration)

        # BƯỚC 5: TẠO HIỆU ỨNG TRÊN CÙNG
        glow_layer = make_glow_layer(duration)
        waveform_layer = make_circular_waveform(audio_path, duration)
        # Đặt sóng nhạc ở giữa, cách lề trên 50px
        waveform_layer = waveform_layer.set_position(("center", 50))

        # BƯỚC 6: TẠO TIÊU ĐỀ
        title_layer = None
        if title_text:
            try:
                title_layer = TextClip(
                    title_text.upper(),
                    fontsize=55, font='DejaVu-Sans-Bold', color='#FFD700', stroke_color='black', stroke_width=3,
                    method='caption', align='West', size=(800, None)       
                ).set_position((50, 50)).set_duration(duration)
            except Exception as e:
                logger.warning(f"⚠️ Không tạo được tiêu đề: {e}")

        # BƯỚC 7: LOGO
        logo_path = get_path('assets', 'images', 'channel_logo.png')
        logo_layer = None
        if os.path.exists(logo_path):
            logo_layer = ImageClip(logo_path).set_duration(duration).resize(height=100).set_position(("right", "top")).margin(right=20, top=20, opacity=0)

        # BƯỚC 8: TỔNG HỢP CUỐI CÙNG
        final_layers = [background_clip, glow_layer, waveform_layer]
        if title_layer: final_layers.append(title_layer)
        if logo_layer: final_layers.append(logo_layer)
        
        logger.info("   (LOG): Đang ghép (Composite) tất cả các lớp...")
        final_video = CompositeVideoClip(final_layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT)).set_audio(audio)
        
        # BƯỚC 9: XUẤT FILE VIDEO (RENDERING)
        output_path = get_path('outputs', 'video', f"{episode_id}_video.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        logger.info(f"🚀 PHASE RENDER: Bắt đầu xuất file video (Cấu hình tối ưu)...")
        final_video.write_videofile(
            output_path, fps=20, codec="libx264", audio_codec="aac", preset="ultrafast", threads=2, ffmpeg_params=["-crf", "28"], logger='bar' 
        )
        logger.info(f"✅ XUẤT VIDEO THÀNH CÔNG!")
        return output_path

    except Exception as e:
        logger.error(f"❌ LỖI NGHIÊM TRỌNG TRONG CREATE_VIDEO: {e}", exc_info=True)
        return False
