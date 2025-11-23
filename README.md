# Podcast Nhân Vật Huyền Thoại

Dự án audio podcast kể chuyện về những nhân vật có ảnh hưởng lịch sử, văn hóa Việt Nam. Tập trung vào chất lượng biên tập, âm thanh và hệ thống website—phù hợp phát hành đa nền tảng.


## Hướng Dẫn Sử Dụng

# Podcast Generator — Full Pipeline

Auto pipeline tạo podcast cinematic:
- đọc yêu cầu từ Google Sheet
- tải ảnh từ Google Drive folder
- tạo script cinematic bằng OpenAI
- tạo TTS (OpenAI TTS) giọng nam trầm
- tạo subtitle (.srt)
- dựng video 16:9 + Shorts 9:16 (waveform + micro icon + logo)
- ghép nhạc / SFX
- upload lên YouTube (tùy chọn)

## Cài đặt nhanh
1. Tạo `service_account.json` (Google Cloud) & share Google Sheet + Drive folders với email service account.
2. Thêm secrets vào GitHub: `OPENAI_API_KEY`, `YOUTUBE_API_KEY`.
3. Tạo Google Sheet theo định dạng:
   - columns: id,title,character,core_theme,img_folder,status,hash
   - `status` = `pending` cho dòng mới
4. Đặt assets: `intro_outro/intro.mp4`, `intro_outro/outro.mp4`, `logos/logo.png`, `inputs/images/` (nếu muốn)
5. Push repo → chạy workflow (manual dispatch hoặc theo schedule)

## Chạy local
```bash
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
python scripts/glue_pipeline.py
