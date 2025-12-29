# scripts/generate_image.py (FINAL FIXED)

import os
import logging
import requests
from openai import OpenAI
from utils import get_path

logger = logging.getLogger(__name__)

# Cấu hình DALL-E 3
MODEL = "dall-e-3"
# Kích thước 16:9 (Landscape) chuẩn cho Video Youtube
DEFAULT_SIZE = "1792x1024" 

def generate_character_image(character_name, episode_id):
    """
    Gọi DALL-E 3 để tạo ảnh nhân vật.
    Input: Tên nhân vật, ID tập (VD: 79).
    Output: Đường dẫn file ảnh đã lưu.
    """
    try:
        # 1. Tự động tạo đường dẫn lưu file chuẩn xác
        # Kết quả sẽ là: .../podcast_cinematic/assets/images/79_character.png
        filename = f"{episode_id}_character.png"
        output_path = get_path("assets", "images", filename)
        
        # 2. [TIẾT KIỆM TIỀN] Kiểm tra nếu ảnh đã tồn tại thì dùng lại ngay
        if os.path.exists(output_path):
            logger.info(f"✅ Ảnh đã tồn tại (Skip DALL-E): {output_path}")
            return output_path

        # 3. Kiểm tra API Key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ Thiếu OPENAI_API_KEY.")
            return None

        client = OpenAI(api_key=api_key)

        # 4. Prompt tối ưu "Negative Space" (Để chừa chỗ cho text hiển thị)
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

        # 5. Gọi API OpenAI
        response = client.images.generate(
            model=MODEL,
            prompt=prompt,
            size=DEFAULT_SIZE,
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        
        # 6. Tải ảnh về và lưu
        if image_url:
            img_data = requests.get(image_url).content
            
            # Đảm bảo thư mục tồn tại (Fix lỗi No such file)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'wb') as handler:
                handler.write(img_data)
            
            logger.info(f"✅ Ảnh AI đã lưu tại: {output_path}")
            return output_path
        else:
            logger.error("❌ DALL-E không trả về URL.")
            return None

    except Exception as e:
        logger.error(f"❌ Lỗi generate_image: {e}")
        return None
