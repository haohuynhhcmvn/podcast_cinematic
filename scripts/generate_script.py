# scripts/generate_script.py
import os
import logging
import json 
from openai import OpenAI
from utils import get_path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# --- CÁC THAM SỐ CỐ ĐỊNH ---
CHANNEL_NAME = "Podcast Theo Dấu Chân Huyền Thoại"
TARGET_WORD_COUNT = 1200 # Khoảng 800 - 1200 từ cho video dài
TTS_VOICE_NAME = "Alloy" 

def _call_openai(system, user, max_tokens=1000, response_format=None):
    """Hàm gọi API OpenAI chung, cố định model GPT-4o-mini."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: 
        logger.error("❌ Thiếu OPENAI_API_KEY. Không thể gọi AI."); return None
    try:
        client = OpenAI(api_key=api_key)
        
        config = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens
        }
        if response_format:
            config["response_format"] = response_format

        response = client.chat.completions.create(**config)
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"❌ OpenAI Error: {e}"); return None


# ======================================================================================
# --- A. HÀM TẠO SCRIPT DÀI (LONG FORM) ---
# ======================================================================================
def generate_long_script(data): 
    """
    Tạo kịch bản dài (Bao gồm Intro/Outro text cố định) và Metadata YouTube.
    """
    episode_id = data['ID']
    title = data.get('Name', 'Unknown Title') 
    core_theme = data.get('Core Theme', 'Unknown Theme')
    raw_input = data.get('Content/Input', '')
    
    script_path = get_path('data', 'episodes', f"{episode_id}_script_long.txt")
    
    # --- 1. ĐỊNH NGHĨA CÂU CHÀO VÀ CÂU KẾT CỐ ĐỊNH ---
    PODCAST_INTRO = f"""
Chào mừng bạn đến với {CHANNEL_NAME}. Đây là nơi chúng ta cùng khám phá những câu chuyện lôi cuốn, những bí ẩn chưa được giải mã, và những góc khuất lịch sử ít người biết đến. 
Hôm nay, chúng ta sẽ đi sâu vào hành trình của: {title}.
"""
    
    PODCAST_OUTRO = f"""
Và đó là tất cả những gì chúng ta đã khám phá trong tập {CHANNEL_NAME} ngày hôm nay. 
Nếu bạn thấy nội dung này hữu ích và truyền cảm hứng, đừng quên nhấn nút Đăng ký, chia sẻ và theo dõi để không bỏ lỡ những hành trình tri thức tiếp theo. 
Cảm ơn bạn đã lắng nghe. Hẹn gặp lại bạn trong tập sau!
"""
    
    # --- LOGIC PROMPT ---
    sys_prompt = f"""
    Bạn là **Master Storyteller + ScriptWriter Cinematic** (giọng Nam Trầm – {TTS_VOICE_NAME}).  
    Nhiệm vụ của bạn là tạo **kịch bản Podcast dài – lôi cuốn – gây nghiện**, giống như một bộ phim tài liệu có nhịp kể chậm rãi, mãnh lực cảm xúc và hình ảnh hoá chi tiết.
    
    PHONG CÁCH KỊCH BẢN:
    • Giọng kể truyền cảm, sâu sắc, nhiều tầng cảm xúc.  
    • Tạo hình ảnh mạnh: âm thanh – ánh sáng – mùi – chuyển động.  
    • Mỗi đoạn phải khiến người nghe *nhìn thấy câu chuyện bằng mắt*, không chỉ bằng ngôn ngữ.  
    
    QUY TẮC VIẾT KỊCH BẢN:
    1. Kịch bản BẮT ĐẦU bằng **HOOK điện ảnh cực mạnh** → gây tò mò cao độ.  
       ❗ Tránh mở bài kiểu giới thiệu lan man, thay bằng:  
       → Câu hỏi nghịch lý  
       → Khoảnh khắc căng thẳng sinh tử  
       → Một bí mật chưa được giải mã  
    2. Văn phong **Visual – Real – Human**, tránh trừu tượng.  
       → Thay vì: "Ông rất thông minh" → dùng cảnh, hành động, biến cố để chứng minh.  
    3. Độ dài ~ 800–{TARGET_WORD_COUNT} từ.  
    4. Nhịp đọc (pacing):  
       — Câu ngắn xen câu dài.  
       — Dùng dấu chấm, phẩy, (...) để tạo khoảng thở.  
       — Tạo cảm giác người nghe đang *bước vào không gian câu chuyện*.  
    5. Không viết Intro/Outro — phần đó đã được lắp sau. Chỉ tạo **core_script**.  
    
    YÊU CẦU VỀ METADATA:
    1. youtube_title ≤ 100 ký tự, chứa **từ khoá chính + yếu tố bí ẩn/đảo ngược logic** + IN HOA các từ quan trọng.  
    2. youtube_description mở đầu bằng **câu sốc – downhill hook**, sau đó triển khai nội dung chặt chẽ, có CTA kêu gọi xem video.  
    3. Bao gồm 5–8 hashtag ngách rộng/hẹp liên quan chủ đề.  
    4. youtube_tags: 10–15 từ khoá — có từ ngắn, từ dài (long-tail), từ trend.
    
    CHỦ ĐỀ: "{core_theme}"  
    TÊN TẬP: "{title}"
    """
    
    user_prompt = f"""
    DỮ LIỆU GỐC TỪ GOOGLE SHEET → {raw_input}
    
    Hãy trả về JSON chuẩn với 4 trường:
    {
        "core_script": "[Mở bằng HOOK – nội dung lôi cuốn – visual mạnh]",
        "youtube_title": "[Tiêu đề TRIGGER CẢM XÚC + SEO + VIRAL]",
        "youtube_description": "[Mô tả gây tò mò + CTA khuyến khích xem đầy đủ]",
        "youtube_tags": "[10–15 tags, cách nhau bằng dấu phẩy]"
    }
    """
    
    raw_json = _call_openai(sys_prompt, user_prompt, max_tokens=16000, response_format={"type": "json_object"})

    try:
        data_json = json.loads(raw_json)
        core_script = data_json.get('core_script', "Nội dung đang cập nhật...")
        
        # GHÉP INTRO/OUTRO VÀO CORE SCRIPT
        full_script = PODCAST_INTRO.strip() + "\n\n" + core_script.strip() + "\n\n" + PODCAST_OUTRO.strip()
        
        with open(script_path, 'w', encoding='utf-8') as f: f.write(full_script)
            
        return {
            'script_path': script_path,
            'metadata': data_json 
        }

    except Exception as e:
        logger.error(f"❌ Lỗi xử lý JSON hoặc lắp ráp kịch bản dài: {e}")
        return None


# ======================================================================================
# --- B. HÀM TẠO SCRIPT NGẮN (SHORTS) - FIX HOOK GÂY SỐC ---
# ======================================================================================
def generate_short_script(data):
    """
    Tạo kịch bản Shorts cô đọng, sử dụng JSON output để đảm bảo định dạng Title và Script.
    """
    episode_id = data['ID']
    script_path = get_path('data', 'episodes', f"{episode_id}_script_short.txt")
    title_path = get_path('data', 'episodes', f"{episode_id}_title_short.txt")
    
    # Kêu gọi hành động cố định cho Shorts
    SHORTS_CTA = "Bạn đã sẵn sàng vén màn bí ẩn này? Hãy **nhấn nút Đăng ký, Theo dõi kênh** ngay để luôn nhận được thông tin mới!"

    # 1. CẤU HÌNH PROMPT VÀ YÊU CẦU JSON OUTPUT
    sys_prompt = f"""
    Bạn là **Video Shorts Script Architect** — chuyên tạo nội dung <60s nhưng sát thương cảm xúc mạnh, gây giật mình ngay 3s đầu.  
    Giọng văn dồn dập – dứt khoát – tấn công thẳng vào cảm xúc.
    
    QUY TẮC BẮT BUỘC:
    1) hook_title = 3–10 từ, **IN HOA, RẤT GIẬT GÂN**, đánh mạnh vào *nỗi sợ – tò mò – bí mật bị che giấu*.  
    2) script_body = 150–200 từ • tốc độ cao • mô tả hành động & hình ảnh • mỗi 2–3 câu phải có "điểm nổ cảm xúc".  
    3) Công thức mở đầu:  
       🎯 Tuyên bố sốc + Giữ bí mật tên nhân vật 1/2 câu để **căng dây tò mò**.  
       Ví dụ: "Ông ta phát minh ra điện xoay chiều, nhưng CHẾT TRONG NGHÈO ĐÓI... đó là Nikola Tesla."  
    4) Cấm triết lý mơ hồ. Mọi câu phải có:  
       → nhân vật, hành động, vật thể, hình ảnh rõ nét.  
    5) Điểm cuối nối với **dynamic_cta** → đẩy người xem hành động (follow/subscribe/tiếp tục xem).
    
    TONE:
    • Nhịp nhanh — cut mạnh — cảm giác *đang rượt đuổi thời gian*.  
    • Dùng câu ngắn. Ngắt nhịp bằng chấm liên tục.  
    • Dồn cảm xúc theo dạng tăng dần → **cao trào cuối**.
    """

    
    user_prompt = f"""
    DỮ LIỆU NGUỒN: {data['Content/Input']}
    
    Trả về JSON chính xác:
    {{
        "hook_title": "[IN HOA – SỐC – TỪ GÂY NGHỊCH LÝ/BI KỊCH]",
        "script_body": "[1 câu hook nổ tung, 150-200 từ — visual rõ, hành động nhanh]",
        "dynamic_cta": "[Kết thúc chốt hạ – ép follow, ép xem tiếp]"
    }}
    """
    
    # 2. GỌI AI VỚI JSON MODE
    raw_json = _call_openai(sys_prompt, user_prompt, max_tokens=600, response_format={"type": "json_object"}) 

    # 3. XỬ LÝ LỖI và TÁCH DỮ LIỆU
    hook_title_fallback = f"BÍ MẬT {data['Name'].upper()} VỪA ĐƯỢC VÉN MÀN!"
    script_body_fallback = "Nội dung đang được cập nhật..."
    
    try:
        data_json = json.loads(raw_json)
        hook_title = data_json.get('hook_title', hook_title_fallback).strip()
        script_body_core = data_json.get('script_body', script_body_fallback).strip()
    except Exception as e:
        logger.error(f"❌ Lỗi parsing JSON từ Shorts API: {e}. Dùng nội dung Fallback.")
        hook_title = hook_title_fallback
        script_body_core = script_body_fallback

    # 4. NỐI KỊCH BẢN VỚI CTA CỐ ĐỊNH
    full_script_for_tts = script_body_core + "\n\n" + SHORTS_CTA

    # 5. LƯU FILE
    with open(script_path, 'w', encoding='utf-8') as f: f.write(full_script_for_tts)
    with open(title_path, 'w', encoding='utf-8') as f: f.write(hook_title)
    
    logger.info(f"✅ Kịch bản Shorts đã hoàn tất.")
    
    return script_path, title_path
