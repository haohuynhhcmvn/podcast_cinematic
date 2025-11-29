import os
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                logging.error(f"Không thể refresh token: {e}")
                return None
        else:
            logging.error("Token không hợp lệ hoặc không tìm thấy. Vui lòng chạy script xác thực cục bộ.")
            return None

    return build('youtube', 'v3', credentials=creds)

# Đã đổi tên hàm thành upload_youtube_video để khớp với glue_pipeline.py
def upload_youtube_video(video_path: str, metadata: dict):
    """
    Tải video lên YouTube bằng Google Data API.
    """
    if not video_path or not os.path.exists(video_path):
        logging.error(f"File video không tồn tại: {video_path}")
        return False

    youtube = get_authenticated_service()
    if not youtube:
        return False

    try:
        # Lấy metadata an toàn
        title = metadata.get('title', 'Video Podcast Tự Động')
        description = metadata.get('description', 'Mô tả tự động.')
        tags = metadata.get('tags', [])
        
        # Mặc định để 'unlisted' hoặc 'private' để kiểm duyệt
        privacy_status = metadata.get('privacyStatus', 'unlisted')
        category_id = '22' 

        logging.info(f"Đang chuẩn bị upload: Title='{title}'")

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
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
        return True

    except Exception as e:
        logging.error(f"Lỗi khi upload video: {e}", exc_info=True)
        return False
