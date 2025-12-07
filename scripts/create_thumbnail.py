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
    Thêm text vào Thumbnail với HỘP MÀU ĐỎ (Red Box) phía sau để tăng độ nổi bật (CTR).
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
        
        # Giới hạn chiều rộng text (khoảng 45% chiều rộng ảnh)
        max_width = int(width * 0.45) 

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

        # --- 2. TÍNH TOÁN KÍCH THƯỚC HỘP ĐỎ ---
        start_x = int(width * 0.05)   # Cách lề trái 5%
        start_y = int(height * 0.20)  # Cách lề trên 20%
        line_spacing = target_font_size * 1.2
        
        # Tính chiều rộng lớn nhất của các dòng text
        max_line_width = 0
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            if line_w > max_line_width:
                max_line_width = line_w
        
        total_text_height = len(lines) * line_spacing - (line_spacing - target_font_size) # Ước lượng chiều cao

        # Tạo vùng đệm (padding) cho hộp
        padding = 40
        box_x1 = start_x + max_line_width + padding
        box_y1 = start_y + total_text_height + padding/2 # Thêm chút ở dưới
        
        # Vẽ Hộp Đỏ lên một layer riêng để chỉnh độ trong suốt
        overlay = Image.new('RGBA', img.size, (0,0,0,0))
        draw_ov = ImageDraw.Draw(overlay)
        
        # Màu đỏ (200, 0, 0) với Alpha = 220 (Khá đậm)
        draw_ov.rectangle(
            [(start_x - padding/2, start_y - padding/2), (box_x1, box_y1)], 
            fill=(200, 0, 0, 220)
        )
        
        # Gộp layer hộp đỏ vào ảnh gốc
        img = Image.alpha_composite(img, overlay)
        
        # Tạo lại đối tượng draw trên ảnh mới đã gộp
        draw = ImageDraw.Draw(img)

        # --- 3. VIẾT CHỮ (TEXT RENDER) ---
        for i, line in enumerate(lines):
            y_pos = start_y + i * line_spacing
            
            # Viền đen (Outline) dày để tách biệt với nền đỏ
            stroke_color = "black"
            text_color = "#FFD700" # Vàng Gold
            stroke_width = 4
            
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
        
        logger.info(f"🖼️ Đã tạo Thumbnail (Red Box): {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi tạo Thumbnail: {e}", exc_info=True)
        return None
