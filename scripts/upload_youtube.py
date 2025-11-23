import os
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import pickle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    credentials = None
    
    # Tải token đã lưu
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    # Nếu token hết hạn hoặc không tồn tại, cần xác thực lại (yêu cầu chạy tương tác lần đầu)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            logging.error("Thiếu hoặc hết hạn token. Vui lòng chạy tương tác lần đầu để tạo token.pickle và client_secrets.json.")
            return None # Bỏ qua upload

    return build('youtube', 'v3', credentials=credentials)

def upload_youtube(video_path: str, episode_data: dict):
    if not os.path.exists(video_path):
        logging.error(f"File video không tồn tại tại: {video_path}")
        return "Failed: File not found"

    youtube = get_authenticated_service()
    if not youtube: return "Failed: Authentication failed or token expired."

    title = f"[PODCAST] {episode_data['Name']} | {episode_data['Core Theme']} (Tập {episode_data['ID']})"
    description = f"Nghe trọn vẹn câu chuyện về {episode_data['Name']}. {episode_data['Content/Input'][:200]}..."
    
    # Tạm thời dùng tiêu đề và tên làm tags (cần chỉnh sửa sau)
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
        logging.info(f"Upload thành công! Video ID: {video_id}. Link: https://youtu.be/{video_id}")
        return f"Success: Video ID {video_id}"
    
    except Exception as e:
        logging.error(f"Lỗi khi upload lên YouTube: {e}")
        return "Failed: Check logs for details"
