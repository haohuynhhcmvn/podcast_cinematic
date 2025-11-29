# scripts/upload_youtube.py
import os
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

# QUAN TRỌNG: Tên hàm phải là 'upload_video' để khớp với glue_pipeline.py
def upload_video(video_path: str, episode_data: dict):
    if not video_path or not os.path.exists(video_path):
        logging.error(f"File video không tồn tại: {video_path}")
        return 'FAILED'

    youtube = get_authenticated_service()
    if not youtube:
        return 'FAILED'

    try:
        # Chuẩn bị Metadata
        title = episode_data.get('Name', 'New Podcast Episode')
        # Cắt ngắn tiêu đề nếu quá 100 ký tự
        if len(title) > 100:
            title = title[:97] + "..."
            
        description = episode_data.get('Content/Input', 'Auto-generated podcast.')[:5000]
        tags = ['podcast', 'ai']
        
        logging.info(f"Đang chuẩn bị upload: {title}")

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': 'private', # Để private để kiểm duyệt
                'selfDeclaredMadeForKids': False
            }
        }

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
                logging.info(f"Upload: {int(status.progress() * 100)}%")

        logging.info(f"Upload thành công! Video ID: {response.get('id')}")
        return 'UPLOADED'

    except Exception as e:
        logging.error(f"Lỗi upload: {e}")
        return 'FAILED'
