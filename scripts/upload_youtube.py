# scripts/upload_youtube.py
import os
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- HẰNG SỐ GIỚI HẠN YOUTUBE API ---
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

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
            except Exception as e:
                logging.error(f"Không thể refresh token: {e}")
                return None
        else:
            logging.error("Token không hợp lệ hoặc không tìm thấy.")
            return None

    return build('youtube', 'v3', credentials=creds)

def upload_video(video_path: str, episode_data: dict):
    """
    Upload video lên YouTube, xử lý Title, Description và Tags an toàn.
    """
    if not video_path or not os.path.exists(video_path):
        logging.error(f"File video không tồn tại: {video_path}")
        return 'FAILED'

    youtube = get_authenticated_service()
    if not youtube:
        return 'FAILED'

    try:
        # Metadata
        title = episode_data.get('Title', 'New Podcast Episode')
        description = episode_data.get('Summary', 'Auto-generated podcast.')
        
        # --- FIX TAGS ---
        tags_raw = episode_data.get('Tags', [])
        if isinstance(tags_raw, list):
            tags = tags_raw
        elif isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(',') if t.strip()]
        else:
            tags = []

        # Truncate Title & Description
        if len(title) > MAX_TITLE_LENGTH:
            title = title[:MAX_TITLE_LENGTH - 3] + "..."
            logging.warning(f"⚠️ Tiêu đề đã bị cắt ngắn do vượt quá {MAX_TITLE_LENGTH} ký tự.")

        if len(description) > MAX_DESCRIPTION_LENGTH:
            description = description[:MAX_DESCRIPTION_LENGTH]
            logging.warning(f"⚠️ Mô tả đã bị cắt ngắn do vượt quá {MAX_DESCRIPTION_LENGTH} ký tự.")

        logging.info(f"Đang chuẩn bị upload: {title}")

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }

        # Upload
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
                logging.info(f"Tiến độ Upload: {int(status.progress() * 100)}%")

        logging.info(f"Upload thành công! Video ID: {response.get('id')}")
        return 'UPLOADED'

    except Exception as e:
        logging.error(f"Lỗi khi upload video: {e}")
        return 'FAILED'

if __name__ == '__main__':
    pass
