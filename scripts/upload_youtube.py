#./scripts/upload_youtube.py
import os
import pickle
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Scopes cần thiết cho việc upload video
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    """Lấy dịch vụ YouTube đã xác thực từ token.pickle. 
    Lưu ý: Logic này chỉ hoạt động nếu file token.pickle đã được tạo cục bộ."""
    creds = None
    # File token.pickle nằm ở thư mục gốc (nơi chạy lệnh python)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Nếu không có token hợp lệ, cố gắng refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Lưu lại token mới
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                logging.error(f"Không thể refresh token: {e}")
                return None
        else:
            logging.error("Token không hợp lệ hoặc không tìm thấy. Vui lòng chạy script xác thực cục bộ để tạo token.pickle.")
            return None

    return build('youtube', 'v3', credentials=creds)

# Đã đổi tên hàm thành upload_youtube_video để khớp với glue_pipeline.py
def upload_youtube_video(video_path: str, metadata: dict):
    """
    Tải video lên YouTube bằng Google Data API.
    
    Args:
        video_path (str): Đường dẫn đến file video đã tạo.
        metadata (dict): Chứa title, description, tags, category, privacyStatus.
        
    Returns:
        bool: True nếu upload thành công, False nếu thất bại.
    """
    if not video_path or not os.path.exists(video_path):
        logging.error(f"File video không tồn tại: {video_path}")
        return False

    youtube = get_authenticated_service()
    if not youtube:
        return False

    try:
        # Lấy metadata từ dict đầu vào, cung cấp giá trị mặc định an toàn
        title = metadata.get('title', 'Video Tự Động [No Title]')
        description = metadata.get('description', 'Mô tả tự động.')
        tags = metadata.get('tags', [])
        
        # Mặc định để 'unlisted' hoặc 'private' để kiểm duyệt trong môi trường CI/CD
        privacy_status = metadata.get('privacyStatus', 'unlisted')
        category_id = str(metadata.get('category', '22')) # 22 là Entertainment, 25 là Education

        logging.info(f"Đang chuẩn bị upload: Title='{title}', Status='{privacy_status}'")

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
            part=','.join(body['snippet'].keys()) + ',' + ','.join(body['status'].keys()),
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

if __name__ == '__main__':
    # Code test chạy cục bộ (nếu cần)
    logging.info("Module upload_youtube.py đã sẵn sàng với logic Google API.")
