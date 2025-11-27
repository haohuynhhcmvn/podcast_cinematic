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

# Scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    """Lấy dịch vụ YouTube đã xác thực từ token.pickle"""
    creds = None
    # File token.pickle nằm ở thư mục gốc (nơi chạy lệnh python)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Nếu không có token hợp lệ, pipeline sẽ thất bại (vì không thể tương tác trên GitHub Actions)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Không thể refresh token: {e}")
                return None
        else:
            logging.error("Token không hợp lệ hoặc không tìm thấy. Vui lòng chạy script xác thực cục bộ.")
            return None

    return build('youtube', 'v3', credentials=creds)

def upload_video(video_path: str, episode_data: dict, youtube_metadata: dict): # <<< THÊM ARGUMENT MỚI >>>
    """
    Hàm upload video lên YouTube.
    Args:
        video_path (str): Đường dẫn đến file video.
        episode_data (dict): Dữ liệu tập (Giữ lại để tương thích, không dùng để lấy metadata).
        youtube_metadata (dict): Metadata tự động (title, description, tags).
    Returns:
        str: 'UPLOADED' nếu thành công, 'FAILED' nếu thất bại.
    """
    if not video_path or not os.path.exists(video_path):
        logging.error(f"File video không tồn tại: {video_path}")
        return 'FAILED'

    youtube = get_authenticated_service()
    if not youtube:
        return 'FAILED'

    try:
        # <<< SỬ DỤNG METADATA TỰ ĐỘNG TẠO >>>
        title = youtube_metadata['title']
        description = youtube_metadata['description']
        tags = youtube_metadata['tags']
        # Xóa các dòng xử lý title, description, tags thủ công cũ
        
        logging.info(f"Đang chuẩn bị upload: {title}")

        body = {
            'snippet': {
                'title': title, # Tiêu đề tự động
                'description': description, # Mô tả tự động
                'tags': tags, # Tags tự động (đã là list)
                'categoryId': '22' # Category 22 = People & Blogs
            },
            'status': {
                'privacyStatus': 'public', # Mặc định để Private để kiểm duyệt
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
        logging.error(f"Lỗi khi upload video: {e}", exc_info=True)
        return 'FAILED'

if __name__ == '__main__':
    # Code test chạy cục bộ (nếu cần)
    pass
