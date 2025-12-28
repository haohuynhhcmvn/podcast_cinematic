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

def upload_video(video_path: str, episode_data: dict, thumbnail_path: str = None, scheduled_time: str = None):
    """
    Upload video với hỗ trợ hẹn giờ (scheduled_time format: ISO 8601 UTC)
    """
    if not video_path or not os.path.exists(video_path):
        logging.error(f"❌ File video không tồn tại: {video_path}")
        return 'FAILED'

    youtube = get_authenticated_service()
    if not youtube:
        logging.error("❌ Lỗi xác thực YouTube.")
        return 'FAILED'

    try:
        title = episode_data.get('Title', 'New Episode')
        description = episode_data.get('Summary', '')
        
        # Cắt ngắn nếu quá dài
        if len(title) > MAX_TITLE_LENGTH: title = title[:MAX_TITLE_LENGTH-3] + "..."
        if len(description) > MAX_DESCRIPTION_LENGTH: description = description[:MAX_DESCRIPTION_LENGTH]

        status_body = {
            'selfDeclaredMadeForKids': False,
            'privacyStatus': 'private' # Bắt buộc là private để hẹn giờ
        }
        
        if scheduled_time:
            status_body['publishAt'] = scheduled_time

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': episode_data.get('Tags', []),
                'categoryId': '22'
            },
            'status': status_body
        }

        logging.info(f"🚀 Đang tải lên: {title}")
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logging.info(f"   Tiến trình: {int(status.progress() * 100)}%")

        video_id = response.get('id')
        logging.info(f"✅ Thành công! Video ID: {video_id}")

        # Upload Thumbnail
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()
                logging.info("🖼️ Đã cập nhật Thumbnail.")
            except Exception as e:
                logging.error(f"⚠️ Lỗi Thumbnail: {e}")
        
        return {'video_id': video_id}

    except Exception as e:
        logging.error(f"❌ Lỗi Upload: {e}")
        return 'FAILED'
