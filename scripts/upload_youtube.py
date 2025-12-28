# scripts/upload_youtube.py
import os
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000

def get_authenticated_service():
    """Xác thực YouTube API qua token.pickle."""
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

def upload_video(video_path: str, episode_data: dict, thumbnail_path: str = None):
    """
    Upload video và thumbnail.
    Dùng cho cả Video Dài và Video Shorts.
    """
    if not video_path or not os.path.exists(video_path):
        logging.error(f"❌ File video không tồn tại: {video_path}")
        return 'FAILED'

    youtube = get_authenticated_service()
    if not youtube:
        logging.error("❌ Lỗi xác thực YouTube (token.pickle có thể đã hết hạn).")
        return 'FAILED'

    try:
        title = episode_data.get('Title', 'New Episode')
        description = episode_data.get('Summary', '')
        tags = episode_data.get('Tags', [])

        # Kiểm tra giới hạn ký tự YouTube
        if len(title) > MAX_TITLE_LENGTH: title = title[:MAX_TITLE_LENGTH-3] + "..."
        if len(description) > MAX_DESCRIPTION_LENGTH: description = description[:MAX_DESCRIPTION_LENGTH]

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22' # People & Blogs
            },
            'status': {
                'privacyStatus': 'private', # Bạn nên để private để kiểm tra trước khi công khai
                'selfDeclaredMadeForKids': False
            }
        }

        # --- Bước 1: Upload Video ---
        logging.info(f"🚀 Đang tải lên: {title}")
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
                logging.info(f"   Tiến trình: {int(status.progress() * 100)}%")

        video_id = response.get('id')
        logging.info(f"✅ Tải lên video thành công! ID: {video_id}")

        # --- Bước 2: Upload Thumbnail (Nếu có) ---
        if thumbnail_path and os.path.exists(thumbnail_path):
            logging.info(f"🖼️ Đang tải lên thumbnail: {thumbnail_path}")
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                logging.info("✅ Tải lên thumbnail thành công!")
            except Exception as e:
                logging.error(f"⚠️ Lỗi upload thumbnail: {e}")
        
        return {'video_id': video_id}

    except Exception as e:
        logging.error(f"❌ Lỗi Upload YouTube: {e}")
        return 'FAILED'
