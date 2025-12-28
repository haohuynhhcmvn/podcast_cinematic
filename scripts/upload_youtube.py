# scripts/upload_youtube.py
import os
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- HẰNG SỐ GIỚI HẠN YOUTUBE API ---
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000

def get_authenticated_service():
    """Lấy dịch vụ YouTube đã xác thực từ token.pickle"""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                return None
        else:
            return None
    return build('youtube', 'v3', credentials=creds)

# =========================================================
# 🚀 HÀM UPLOAD CẬP NHẬT: HỖ TRỢ HẸN GIỜ (PUBLISH_AT)
# =========================================================
def upload_video(video_path: str, episode_data: dict, thumbnail_path: str = None, publish_at: str = None):
    """
    Upload video lên YouTube. 
    Nếu có publish_at (ISO 8601), video sẽ được đặt ở chế độ Private và lập lịch đăng.
    """
    if not video_path or not os.path.exists(video_path):
        logging.error(f"❌ File video không tồn tại: {video_path}")
        return 'FAILED'

    youtube = get_authenticated_service()
    if not youtube:
        logging.error("❌ Không thể xác thực YouTube API.")
        return 'FAILED'

    try:
        title = episode_data.get('Title', 'Untitled Video')[:MAX_TITLE_LENGTH]
        description = episode_data.get('Description', '')[:MAX_DESCRIPTION_LENGTH]
        tags = episode_data.get('Tags', [])

        # Cấu hình Body cho Request
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22' # People & Blogs
            },
            'status': {
                # Nếu hẹn giờ, privacyStatus BẮT BUỘC phải là 'private'
                'privacyStatus': 'private' if publish_at else 'public',
                'selfDeclaredMadeForKids': False
            }
        }

        # Thêm thời gian hẹn giờ nếu có (Định dạng: YYYY-MM-DDThh:mm:ssZ)
        if publish_at:
            body['status']['publishAt'] = publish_at
            logging.info(f"📅 Đã thiết lập lịch đăng bài vào: {publish_at}")

        # 1. Thực hiện Upload Video
        logging.info(f"🚀 Đang upload video: {title}")
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logging.info(f"   Tiến độ upload: {int(status.progress() * 100)}%")

        video_id = response.get('id')
        logging.info(f"✅ Upload Video thành công! ID: {video_id}")

        # 2. Upload Thumbnail (Nếu có)
        if thumbnail_path and os.path.exists(thumbnail_path):
            logging.info(f"🖼️ Đang upload thumbnail cho video {video_id}")
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                logging.info("✅ Cập nhật Thumbnail thành công!")
            except Exception as e:
                logging.error(f"⚠️ Lỗi cập nhật thumbnail: {e}")
        
        return {'video_id': video_id}

    except Exception as e:
        logging.error(f"❌ Lỗi Upload YouTube: {e}")
        return 'FAILED'
