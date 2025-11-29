# scripts/glue_pipeline.py
import logging
# ... [các import khác] ...

# --- HÀM CHÍNH: ORCHESTRATOR ---

def main():
    # ... [Setup, Fetch dữ liệu] ...
    
    # 1. Fetch Dữ liệu từ Google Sheet
    task = fetch_content()
    if not task: return
    
    data = task['data']
    eid = data['ID']
    row_idx = task['row_idx']
    worksheet = task['worksheet']

    # ... [Luồng Video Dài bị khóa] ...

    # ====================================================================
    # --- LUỒNG SHORTS (9:16) --- (FIXED FOR UPLOAD)
    # ====================================================================
    logger.info("📱 --- LUỒNG SHORTS (9:16) ĐANG CHẠY VÀ UPLOAD YOUTUBE ---")
    
    # 1. Generate Script Short
    result_shorts = generate_short_script(data)
    
    if result_shorts:
        script_short_path, title_short_path = result_shorts
        
        # Đọc nội dung Tiêu đề Hook
        try:
            with open(title_short_path, 'r', encoding='utf-8') as f:
                hook_title = f.read().strip()
        except:
            hook_title = ""

        # 2. Tạo TTS cho phần nội dung
        tts_short = create_tts(script_short_path, eid, "short")
        
        if tts_short:
            # 3. TẠO SHORTS
            shorts_path = create_shorts(tts_short, hook_title, eid)
            
            # 4. UPLOAD SHORTS (FIX LỖI KEY)
            if shorts_path:
                
                # --- XÂY DỰNG METADATA CHUẨN VỚI KEY MONG ĐỢI CỦA upload_youtube.py ---
                
                # Title: HOOK TITLE + Tên tập + #Shorts
                short_title = f"{hook_title} | {data.get('Name')} #Shorts"
                
                # Summary (Mô tả): Lấy Core Theme và thêm CTA Viral
                # SỬ DỤNG Core Theme VÀ CONTENT INPUT ĐỂ LÀM MÔ TẢ HẤP DẪN HƠN
                short_description = f"🔥 Vén màn bí mật: {data.get('Core Theme', 'Huyền thoại')}\n\n{data.get('Content/Input', 'Video Shorts hấp dẫn, xem ngay!')}\n\nXem toàn bộ câu chuyện và nhiều huyền thoại khác trên kênh Podcast Theo Dấu Chân Huyền Thoại!\n#shorts #viral #podcast"
                
                # Tags: Lấy Tags mặc định
                short_tags = 'shorts, viral, podcast, storytelling, ' + data.get('Core Theme', '')

                # TẠO DICTIONARY VỚI KEY CHÍNH XÁC: Title, Summary, Tags
                upload_data = {
                    'Title': short_title, 
                    'Summary': short_description, 
                    'Tags': short_tags 
                }
                
                # GỌI HÀM UPLOAD (Nó sẽ nhận đúng các key này)
                upload_video(shorts_path, upload_data)

    # 5. Update Sheet
    # ... [Code update status] ...

if __name__ == "__main__":
    main()
