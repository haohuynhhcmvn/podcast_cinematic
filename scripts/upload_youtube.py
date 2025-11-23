import os
import logging
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    credentials = None
    
    # Tìm file token.pickle ở thư mục gốc
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            # Nếu chạy trên Actions, bước này sẽ không chạy được nếu token hết hạn.
            logging.error("Thiếu hoặc hết hạn token. Vui lòng tạo/cập nhật token.pickle.")
            return None 

    return build('youtube', 'v3', credentials=credentials)

def upload_youtube(video_path: str, episode_data: dict):
    if not os.path.exists(video_path): return "Failed: File not found"

    youtube = get_authenticated_service()
    if not youtube: return "Failed: Authentication failed or token expired."

    title = f"[PODCAST] {episode_data['Name']} | {episode_data['Core Theme']} (Tập {episode_data['ID']})"
    # Giả định có trường 'Content/Input' để làm mô tả
    description = f"Nghe trọn vẹn câu chuyện về {episode_data['Name']}. {episode_data['Content/Input'][:200]}..."
    
    tags = [episode_data['Name'].replace(' ', ''), 'podcast', 'nhanvathuyenthoai'] 

    request_body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': 'private' 
        },
        'notifySubscribers': False 
    }

    media_file = MediaFileUpload(video_path, chunksize=-1, resumable=True)

    try:
        response = youtube.videos().insert(
            part=','.join(request_body.keys()),
            body=request_body,
            media_body=media_file
        ).execute()

        video_id = response.get('id')
        return f"Success: Video ID {video_id}"
    
    except Exception as e:
        logging.error(f"Lỗi khi upload lên YouTube: {e}")
        return "Failed: Check logs for details"
