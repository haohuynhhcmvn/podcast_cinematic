# scripts/generate_image.py

import os
import logging
import requests
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# Khuyên dùng DALL-E 3 với kích thước 16:9 chuẩn cho Long-form
MODEL = "dall-e-3"
IMAGE_SIZE = "1792x1024" 

def generate_character_image(character_name, output_path):
    """
    Gọi DALL-E 3 để tạo ảnh nhân vật theo bố cục 'Negative Space' 16:9.
    """
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Missing OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # --- PROMPT CHIẾN LƯỢC: BUỘC NHÂN VẬT LỆCH KHUNG ---
        prompt = f"""
        A hyper-realistic, cinematic portrait of {character_name}. 8k resolution, 
        gritty historical documentary atmosphere, dramatic lighting.

        CRITICAL COMPOSITION RULES:
        1. The character MUST be positioned on the FAR RIGHT side of the frame (Rule of Thirds).
        2. The LEFT SIDE (at least 60% of the image) must be EMPTY, DARK, or VAST LANDSCAPE (Negative Space) for text overlay.
        3. Lighting: Strong, dramatic 'Rembrandt lighting' hitting the face from the right. The left side must be in deep shadow or mist.
        4. No text, no logos, no borders.
        """

        logger.info(f"🎨 Đang gọi DALL-E 3 vẽ: {character_name}...")

        response = client.images.generate(
            model=MODEL,
            prompt=prompt,
            size=IMAGE_SIZE,
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        
        # Tải ảnh về bằng thư viện requests
        if image_url:
            img_data = requests.get(image_url).content
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'wb') as handler:
                handler.write(img_data)
            
            logger.info(f"✅ Ảnh AI Raw đã lưu tại: {output_path}")
            return output_path
        else:
            logger.error("❌ DALL-E không trả về URL.")
            return None

    except Exception as e:
        logger.error(f"❌ Lỗi tạo ảnh DALL-E: {e}")
        return None
