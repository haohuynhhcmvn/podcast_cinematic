# === scripts/create_thumbnail.py ===
import os
import logging
from PIL import Image, ImageDraw, ImageFont
from utils import get_path

logger = logging.getLogger(__name__)

def find_font(font_name="Impact.ttf"):
    # Ưu tiên font Impact (đậm, chuẩn meme/thumbnail)
    font_path = get_path('assets', 'fonts', font_name)
    if os.path.exists(font_path):
        return font_path
    
    # Fallback font hệ thống Linux
    return 'DejaVuSans-Bold' 

def add_text_to_thumbnail(image_path, text_content, output_path):
    """
    Thêm text vào Thumbnail (Chữ Vàng, không có hộp đỏ)
    """
    try:
        # Load ảnh
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        
        draw = ImageDraw.Draw(img)
        font_path = find_font()
        
        # Cỡ chữ lớn
        target_font_size = 90
        try:
            font = ImageFont.truetype(font_path, target_font_size)
        except:
            font = ImageFont.load_default()

        text_content = text_content.upper() 

        # --- 1. XỬ LÝ TEXT WRAP (XUỐNG DÒNG) ---
        words = text_content.split()
        lines = []
        current_line = ""
        
        # Giới hạn chiều rộng text (khoảng 50% chiều rộng ảnh)
        max_width = int(width * 0.50) 

        for word in words:
            test_line = current_line + " " + word if current_line else word
            
            # Tính độ rộng dòng thử nghiệm
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_w = bbox[2] - bbox[0]
            
            if text_w <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        lines.append(current_line)
        
        if not lines or (len(lines) == 1 and not lines[0]):
            logger.warning("⚠️ Không có text để ghi lên Thumbnail.")
            img = img.convert("RGB")
            img.save(output_path)
            return output_path

        # --- 2. TÍNH TOÁN VỊ TRÍ (KHÔNG CÒN HỘP ĐỎ) ---
        start_x = int(width * 0.05)   # Cách lề trái 5%
        start_y = int(height * 0.25)  # Cách lề trên 25% (Hạ thấp xuống một chút)
        line_spacing = target_font_size * 1.2
        
        # --- 3. VIẾT CHỮ (TEXT RENDER) TRỰC TIẾP LÊN ẢNH ---
        for i, line in enumerate(lines):
            y_pos = start_y + i * line_spacing
            
            # Viền đen (Outline) dày
            stroke_color = "black"
            text_color = "#FFD700" # Vàng Gold
            stroke_width = 5 # Viền dày hơn chút để nổi trên nền ảnh
            
            # Vẽ viền
            for dx in [-stroke_width, stroke_width]:
                for dy in [-stroke_width, stroke_width]:
                    draw.text((start_x + dx, y_pos + dy), line, fill=stroke_color, font=font)
            
            # Vẽ chữ chính
            draw.text((start_x, y_pos), line, fill=text_color, font=font)

        # Lưu ảnh
        img = img.convert("RGB") 
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, quality=95)
        
        logger.info(f"🖼️ Đã tạo Thumbnail (Classic Style): {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi tạo Thumbnail: {e}", exc_info=True)
        return None
