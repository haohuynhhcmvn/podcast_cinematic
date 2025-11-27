# ./script/generate_script.py (ĐÃ SỬA: Thêm CÂU CHÀO và CÂU KẾT CỐ ĐỊNH)
import os
import logging
import json # Cần import thêm thư viện JSON
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_script(episode_data):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logging.error("Thiếu OPENAI_API_KEY."); return None

    try:
        client = OpenAI(api_key=api_key)
        
        episode_id = episode_data['ID']
        title = episode_data['Name']
        core_theme = episode_data['Core Theme']
        raw_content = episode_data['Content/Input']
        
        # --- 1. ĐỊNH NGHĨA CÂU CHÀO VÀ CÂU KẾT CỐ ĐỊNH ---
        # Bạn có thể thay đổi tên kênh và nội dung này
        CHANNEL_NAME = "Podcast Cinematic" 
        
        PODCAST_INTRO = f"""
Chào mừng bạn đến với {CHANNEL_NAME}. Đây là nơi chúng ta cùng khám phá những câu chuyện lôi cuốn, những bí ẩn chưa được giải mã, và những góc khuất lịch sử ít người biết đến. 
Hôm nay, chúng ta sẽ đi sâu vào hành trình của: {title}.
"""
        
        PODCAST_OUTRO = f"""
Và đó là tất cả những gì chúng ta đã khám phá trong tập {CHANNEL_NAME} ngày hôm nay. 
Nếu bạn thấy nội dung này hữu ích và truyền cảm hứng, đừng quên nhấn nút Đăng ký, chia sẻ và theo dõi để không bỏ lỡ những hành trình tri thức tiếp theo. 
Cảm ơn bạn đã lắng nghe. Hẹn gặp lại bạn trong tập sau!
"""
        
        # --- 2. CẬP NHẬT PROMPT: CHỈ YÊU CẦU NỘI DUNG CHÍNH (core_script) ---
        system_prompt = f"""
        Bạn là **Master Storyteller** (Người kể chuyện bậc thầy) với giọng văn **Nam Trầm, lôi cuốn, có chiều sâu và truyền cảm hứng**.
        Nhiệm vụ của bạn là biến nội dung thô dưới đây thành một **đối tượng JSON** chứa Kịch bản Audio Cinematic (Chỉ phần nội dung chính) và Metadata YouTube đi kèm.

        QUY TẮC TẠO KỊCH BẢN (core_script):
        1. **Giọng văn:** Lôi cuốn, sắc nét, rõ ràng, giàu hình ảnh.
        2. **Thời lượng:** Kịch bản **phần nội dung chính** nên có độ dài khoảng 150 - 200 từ.
        3. **Định dạng:** Chỉ văn bản cần được đọc, KHÔNG bao gồm lời chào/kết.

        QUY TẮC TẠO METADATA YOUTUBE:
        1. **youtube_title:** Tiêu đề hấp dẫn, tối đa 100 ký tự.
        2. **youtube_description:** Mô tả đầy đủ (khoảng 300 từ), bao gồm tóm tắt, kêu gọi hành động (CTA), và hashtag.
        3. **youtube_tags:** Danh sách 10-15 từ khóa liên quan, viết thường, ngăn cách bằng dấu phẩy.

        CHỦ ĐỀ CỐT LÕI CỦA TẬP NÀY: "{core_theme}"
        TÊN NHÂN VẬT/TIÊU ĐỀ: "{title}"
        """

        user_prompt = f"""
        NỘI DUNG THÔ CẦN XỬ LÝ:\n---\n{raw_content}\n---\n
        Hãy tạo Kịch bản **NỘI DUNG CHÍNH** và Metadata YouTube, trả về dưới dạng JSON với 4 trường sau:
        {{
            "core_script": "[Nội dung kịch bản chính, KHÔNG BAO GỒM LỜI CHÀO/KẾT]",
            "youtube_title": "[Tiêu đề video]",
            "youtube_description": "[Mô tả video]",
            "youtube_tags": "[Tags video, ngăn cách bằng dấu phẩy]"
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.7,
            response_format={"type": "json_object"} 
        )
        
        # --- 3. XỬ LÝ VÀ GHÉP KỊCH BẢN CUỐI CÙNG ---
        try:
            json_response = json.loads(response.choices[0].message.content)
            
            core_script = json_response.get('core_script', '')
            youtube_title = json_response.get('youtube_title', '')
            youtube_description = json_response.get('youtube_description', '')
            youtube_tags_raw = json_response.get('youtube_tags', '')
            
        except json.JSONDecodeError as e:
            logging.error(f"Lỗi phân tích cú pháp JSON từ OpenAI: {e}")
            return None

        # GHÉP KỊCH BẢN CUỐI CÙNG: CÂU CHÀO + NỘI DUNG CHÍNH + CÂU KẾT
        script_content = PODCAST_INTRO.strip() + "\n\n" + core_script.strip() + "\n\n" + PODCAST_OUTRO.strip()
        
        # --- 4. LƯU SCRIPT VÀ TRẢ VỀ DATA ---
        output_dir = os.path.join('data', 'episodes')
        os.makedirs(output_dir, exist_ok=True)
        script_filename = f"{episode_id}_script.txt"
        script_path = os.path.join(output_dir, script_filename)
        
        # Lưu toàn bộ kịch bản đã ghép (Intro + Core + Outro)
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        logging.info(f"Đã tạo kịch bản (gồm chào/kết) và metadata thành công. Script lưu tại: {script_path}")
        
        # Trả về Dictionary chứa cả path và metadata
        return {
            'script_path': script_path,
            'youtube_title': youtube_title,
            'youtube_description': youtube_description,
            'youtube_tags': [tag.strip() for tag in youtube_tags_raw.split(',')] 
        }

    except Exception as e:
        logging.error(f"Lỗi tổng quát khi tạo kịch bản: {e}", exc_info=True)
        return None
