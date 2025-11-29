# ./script/generate_script.py (ĐÃ CẬP NHẬT: Dùng GPT-4o-mini và rút ngắn kịch bản)
import os
import logging
import json 
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION ---
TARGET_WORD_COUNT = 1000 # Rút ngắn kịch bản xuống 800 - 1000 từ (khoảng 5-7 phút)
MODEL = "gpt-4o-mini"    # Sử dụng mô hình tốc độ cao và chi phí thấp

# --- KHAI BÁO HÀM ĐỂ KHỚP VỚI GLUE_PIPELINE.PY ---
# Đã đổi tên hàm từ generate_script thành generate_full_script
def generate_full_script(episode_data):
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logging.error("Thiếu OPENAI_API_KEY."); return None

    try:
        client = OpenAI(api_key=api_key)
        
        # SỬ DỤNG CÁC KEY ĐƯỢC CUNG CẤP TỪ fetch_content.py
        episode_id = episode_data['ID']
        title = episode_data.get('title', 'Unknown Title') # Sử dụng 'title' từ fetch_content
        core_theme = episode_data.get('core_theme', 'Unknown Theme') # Sử dụng 'core_theme' từ fetch_content
        text_hash = episode_data.get('text_hash', str(episode_id)) # Dùng hash để đặt tên file
        
        # --- 1. ĐỊNH NGHĨA CÂU CHÀO VÀ CÂU KẾT CỐ ĐỊNH ---
        CHANNEL_NAME = "Podcast Theo Dấu Chân Huyền Thoại" 
        
        PODCAST_INTRO = f"""
Chào mừng bạn đến với {CHANNEL_NAME}. Đây là nơi chúng ta cùng khám phá những câu chuyện lôi cuốn, những bí ẩn chưa được giải mã, và những góc khuất lịch sử ít người biết đến. 
Hôm nay, chúng ta sẽ đi sâu vào hành trình của: {title}.
"""
        
        PODCAST_OUTRO = f"""
Và đó là tất cả những gì chúng ta đã khám phá trong tập {CHANNEL_NAME} ngày hôm nay. 
Nếu bạn thấy nội dung này hữu ích và truyền cảm hứng, đừng quên nhấn nút Đăng ký, chia sẻ và theo dõi để không bỏ lỡ những hành trình tri thức tiếp theo. 
Cảm ơn bạn đã lắng nghe. Hẹn gặp lại bạn trong tập sau!
"""
        
        # --- 2. CẬP NHẬT PROMPT: YÊU CẦU ĐỘ DÀI KỊCH BẢN CHO GPT-4o-mini ---
        system_prompt = f"""
        Bạn là **Master Storyteller** (Người kể chuyện bậc thầy) với giọng văn **Nam Trầm, lôi cuốn, có chiều sâu và truyền cảm hứng**.
        Nhiệm vụ của bạn là biến nội dung thô dưới đây thành một **đối tượng JSON** chứa Kịch bản Audio Cinematic (Chỉ phần nội dung chính) và Metadata YouTube đi kèm.

        QUY TẮC TẠO KỊCH BẢN (core_script):
        1. **Giọng văn:** Lôi cuốn, sắc nét, rõ ràng, giàu hình ảnh.
        2. **Thời lượng quan trọng (ĐÃ RÚT NGẮN):** Kịch bản **phần nội dung chính** nên có độ dài khoảng **800 - {TARGET_WORD_COUNT} từ**. Đây là yêu cầu cứng để đảm bảo video đạt tối thiểu 5-7 phút. Hãy viết chất lượng, cô đọng để đạt được độ dài này.
        3. **Định dạng:** Chỉ văn bản cần được đọc, KHÔNG bao gồm lời chào/kết.

        QUY TẮC TẠO METADATA YOUTUBE:
        1. **youtube_title:** Tiêu đề hấp dẫn, tối đa 100 ký tự.
        2. **youtube_description:** Mô tả đầy đủ (khoảng 300 từ), bao gồm tóm tắt, kêu gọi hành động (CTA), và hashtag.
        3. **youtube_tags:** Danh sách 10-15 từ khóa liên quan, viết thường, ngăn cách bằng dấu phẩy.

        CHỦ ĐỀ CỐT LÕI CỦA TẬP NÀY: "{core_theme}"
        TÊN NHÂN VẬT/TIÊU ĐỀ: "{title}"
        """

        user_prompt = f"""
        TẬP TRUNG VÀO: Chủ đề '{core_theme}' của tập '{title}'.
        
        Hãy tạo Kịch bản **NỘI DUNG CHÍNH** và Metadata YouTube, trả về dưới dạng JSON với 4 trường sau:
        {{
            "core_script": "[Nội dung kịch bản chính, KHÔNG BAO GỒM LỜI CHÀO/KẾT]",
            "youtube_title": "[Tiêu đề video]",
            "youtube_description": "[Mô tả video]",
            "youtube_tags": "[Tags video, ngăn cách bằng dấu phẩy]"
        }}
        """

        response = client.chat.completions.create(
            model=MODEL, # Dùng GPT-4o-mini
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.7,
            response_format={"type": "json_object"} 
        )
        
        # --- 3. XỬ LÝ VÀ GHÉP KỊCH BẢN CUỐI CÙNG ---
        try:
            json_response = json.loads(response.choices[0].message.content)
            
            core_script = json_response.get('core_script', '')
            youtube_title = json_response.get('youtube_title', title)
            youtube_description = json_response.get('youtube_description', '')
            youtube_tags_raw = json_response.get('youtube_tags', '')
            
        except json.JSONDecodeError as e:
            logging.error(f"Lỗi phân tích cú pháp JSON từ OpenAI: {e}")
            raise # Ném lỗi để bắt ở ngoài

        # GHÉP KỊCH BẢN CUỐI CÙNG: CÂU CHÀO + NỘI DUNG CHÍNH + CÂU KẾT
        script_content = PODCAST_INTRO.replace("{title}", title).strip() + "\n\n" + core_script.strip() + "\n\n" + PODCAST_OUTRO.strip()
        
        # --- 4. LƯU SCRIPT VÀ TRẢ VỀ DATA ---
        output_dir = os.path.join('data', 'episodes')
        os.makedirs(output_dir, exist_ok=True)
        # Đổi tên file để dùng hash
        script_json_path = os.path.join(output_dir, f"{text_hash}_full_script.json")
        script_txt_path = os.path.join(output_dir, f"{text_hash}_full_script.txt")
        
        # Lưu toàn bộ JSON (metadata)
        with open(script_json_path, 'w', encoding='utf-8') as f:
            json_response['full_script_content'] = script_content
            json.dump(json_response, f, ensure_ascii=False, indent=4)
            
        # Lưu toàn bộ kịch bản đã ghép (Intro + Core + Outro)
        with open(script_txt_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        logging.info(f"Đã tạo kịch bản (GPT-4o-mini, ~1000 từ) và metadata thành công. Script lưu tại: {script_txt_path}")
        
        # Trả về Dictionary chứa cả path và metadata
        return {
            'full_script_json_path': script_json_path,
            'full_script_txt_path': script_txt_path,
            'full_title': youtube_title,
            'full_description': youtube_description,
            'youtube_tags': [tag.strip() for tag in youtube_tags_raw.split(',')] 
        }

    except Exception as e:
        logging.error(f"Lỗi tổng quát khi tạo kịch bản: {e}", exc_info=True)
        # Tạo file JSON thất bại để pipeline có artifact để kiểm tra
        if 'text_hash' in locals() and not os.path.exists(script_json_path):
             with open(script_json_path, 'w', encoding='utf-8') as f:
                 json.dump({"error": str(e), "status": "failed", "model": MODEL}, f, ensure_ascii=False, indent=4)
        raise # Ném lại lỗi để glue_pipeline bắt
