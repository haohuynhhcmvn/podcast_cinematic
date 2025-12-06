# scripts/create_thumbnail.py

import os
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils import get_path

logger = logging.getLogger(__name__)

def find_font(font_name="Impact.ttf"):
    """
    Tìm kiếm font chữ hệ thống hoặc font mặc định.
    Để hoạt động 100% trên GitHub Actions, bạn nên upload 1 font .ttf vào thư mục assets/fonts
    """
    font_path = get_path('assets', 'fonts', font_name)
    if os.path.exists(font_path):
        return font_path
    
    # Fallback về font hệ thống (có thể không hoạt động trên GitHub Runner)
    return 'DejaVuSans-Bold' # Tên font chung trên Linux

def add_text_to_thumbnail(image_path, text_content, output_path):
    """
    Thêm text (Title) vào Thumbnail, sử dụng bố cục 1/3 bên trái.
    """
    try:
        # Load ảnh Raw từ DALL-E
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        
        draw = ImageDraw.Draw(img)
        font_path = find_font()
        
        # Cấu hình Text (Text phải to và nổi bật)
        target_font_size = 90
        font = ImageFont.truetype(font_path, target_font_size)
        text_content = text_content.upper() # In hoa để gây chú ý

        # --- XỬ LÝ TEXT WRAP (XUỐNG DÒNG) ---
        words = text_content.split()
        lines = []
        current_line = ""
        
        # Giới hạn chiều rộng chữ ở 40% màn hình (Tức là vùng Negative Space)
        max_width = int(width * 0.40) 

        for word in words:
            # Đo kích thước dòng mới nếu thêm từ này
            test_line = current_line + " " + word if current_line else word
            text_w, text_h = draw.textsize(test_line, font=font)
            
            if text_w <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        lines.append(current_line)
        
        # --- VỊ TRÍ TEXT ---
        # Đặt ở góc 1/4 trên bên trái
        start_x = int(width * 0.05) 
        start_y = int(height * 0.20)
        line_spacing = target_font_size * 1.2
        
        # --- RENDER TEXT (Màu VÀNG trên nền TỐI) ---
        for i, line in enumerate(lines):
            y_pos = start_y + i * line_spacing
            
            # Text Outline (Viền đen) - Bắt buộc cho CTR cao
            stroke_color = "black"
            text_color = "yellow" 
            stroke_width = 4
            
            # Vẽ viền (Vẽ text màu đen 4 lần xung quanh)
            for dx in [-stroke_width, stroke_width]:
                for dy in [-stroke_width, stroke_width]:
                    draw.text((start_x + dx, y_pos + dy), line, fill=stroke_color, font=font)
            
            # Vẽ text chính (Màu Vàng)
            draw.text((start_x, y_pos), line, fill=text_color, font=font)

        # Lưu file cuối cùng
        img = img.convert("RGB") # Chuyển lại RGB trước khi lưu JPEG
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, quality=90)
        
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi tạo Thumbnail: {e}")
        return None
