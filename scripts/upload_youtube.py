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

# --- [FIXED] THÊM THAM SỐ THUMBNAIL_PATH ---
def upload_video(video_path: str, episode_data: dict, thumbnail_path: str = None):
    """
    Upload video và thumbnail (nếu có) lên YouTube.
    """
    if not video_path or not os.path.exists(video_path):
        logging.error(f"File video không tồn tại: {video_path}")
        return 'FAILED'

    youtube = get_authenticated_service()
    if not youtube:
        logging.error("Lỗi xác thực YouTube.")
        return 'FAILED'

    try:
        title = episode_data.get('Title', 'New Episode')
        description = episode_data.get('Summary', '')
        tags = episode_data.get('Tags', [])

        # Cắt ngắn Title/Description
        if len(title) > MAX_TITLE_LENGTH: title = title[:MAX_TITLE_LENGTH-3] + "..."
        if len(description) > MAX_DESCRIPTION_LENGTH: description = description[:MAX_DESCRIPTION_LENGTH]

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'public', # Để public để đăng luôn
                'selfDeclaredMadeForKids': False
            }
        }

        # 1. Upload Video
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
                logging.info(f"   Upload Video: {int(status.progress() * 100)}%")

        video_id = response.get('id')
        logging.info(f"✅ Upload Video thành công! ID: {video_id}")

        # 2. Upload Thumbnail (Logic Mới)
        if thumbnail_path and os.path.exists(thumbnail_path):
            logging.info(f"🖼️ Đang upload thumbnail: {thumbnail_path}")
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                logging.info("✅ Upload Thumbnail thành công!")
            except Exception as e:
                logging.error(f"⚠️ Lỗi upload thumbnail: {e}")
        
        return {'video_id': video_id}

    except Exception as e:
        logging.error(f"❌ Lỗi Upload: {e}")
        return 'FAILED'
