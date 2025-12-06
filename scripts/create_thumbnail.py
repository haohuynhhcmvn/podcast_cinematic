# scripts/create_thumbnail.py

import os
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from utils import get_path

logger = logging.getLogger(__name__)

def find_font(font_name="Impact.ttf"):
    font_path = get_path('assets', 'fonts', font_name)
    if os.path.exists(font_path):
        return font_path
    return 'DejaVuSans-Bold' 

def add_text_to_thumbnail(image_path, text_content, output_path):
    """
    Thêm text vào Thumbnail, dùng textbbox thay cho textsize (Pillow 10+).
    """
    try:
        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        
        draw = ImageDraw.Draw(img)
        font_path = find_font()
        
        target_font_size = 90
        try:
            font = ImageFont.truetype(font_path, target_font_size)
        except:
            # Fallback nếu không load được font
            font = ImageFont.load_default()

        text_content = text_content.upper() 

        # --- XỬ LÝ TEXT WRAP (XUỐNG DÒNG) - FIX CHO PILLOW 10 ---
        words = text_content.split()
        lines = []
        current_line = ""
        
        max_width = int(width * 0.40) 

        for word in words:
            test_line = current_line + " " + word if current_line else word
            
            # [FIX] Dùng textbbox thay vì textsize
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_w = bbox[2] - bbox[0]
            
            if text_w <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        lines.append(current_line)
        
        # --- VỊ TRÍ TEXT ---
        start_x = int(width * 0.05) 
        start_y = int(height * 0.20)
        line_spacing = target_font_size * 1.2
        
        # --- RENDER TEXT ---
        for i, line in enumerate(lines):
            y_pos = start_y + i * line_spacing
            
            stroke_color = "black"
            text_color = "yellow" 
            stroke_width = 4
            
            for dx in [-stroke_width, stroke_width]:
                for dy in [-stroke_width, stroke_width]:
                    draw.text((start_x + dx, y_pos + dy), line, fill=stroke_color, font=font)
            
            draw.text((start_x, y_pos), line, fill=text_color, font=font)

        img = img.convert("RGB") 
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, quality=90)
        
        return output_path

    except Exception as e:
        logger.error(f"❌ Lỗi tạo Thumbnail: {e}")
        return None
