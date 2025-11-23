# scripts/download_drive.py
import os
import logging
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload
import io

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_drive_service():
    """Khởi tạo Google Drive Service bằng Service Account."""
    # Lấy đường dẫn file Service Account từ .env
    service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') 
    if not service_account_file or not os.path.exists(service_account_file):
        logging.error("File Service Account JSON không tồn tại.")
        return None

    try:
        # Khởi tạo credentials với scope chỉ đọc Drive
        credentials = Credentials.from_service_account_file(
            service_account_file,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        logging.error(f"Lỗi khi khởi tạo Google Drive Service: {e}")
        return None

def download_file(drive_service, file_id, file_name, local_path='data/images'):
    """Tải một file từ Google Drive theo ID."""
    try:
        os.makedirs(local_path, exist_ok=True)
        # Đường dẫn lưu file phải được tạo trước
        output_path = os.path.join(local_path, file_name) 
        
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.FileIO(output_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        logging.info(f"Đã tải thành công file {file_name}")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi tải file {file_name} từ Drive: {e}")
        return False

def download_episode_images(image_folder_id: str, episode_id: int):
    """Tìm và tải ảnh nền & micro từ ImageFolder ID."""
    drive_service = get_drive_service()
    if not drive_service: return False
    
    # Tạo thư mục data/images nếu chưa có (utils.setup_environment có tạo, nhưng phòng hờ)
    os.makedirs('data/images', exist_ok=True)
    
    # 1. Tải ảnh nền (Tên file cuối cùng sẽ là background.jpg/png)
    # Lọc các file ảnh trong folder có tên chứa 'background'
    query = f"'{image_folder_id}' in parents and name contains 'background' and mimeType contains 'image/'"
    results = drive_service.files().list(q=query, pageSize=1, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])

    if items:
        background_file = items[0]
        ext = '.png' if background_file['mimeType'] == 'image/png' else '.jpg'
        download_file(drive_service, background_file['id'], f'background{ext}')
    else:
        logging.warning(f"Không tìm thấy ảnh nền trong thư mục {image_folder_id}. Sẽ dùng nền đen.")
        
    # 2. Tải ảnh micro (Tên file cuối cùng sẽ là microphone.jpg/png)
    # Lọc các file ảnh trong folder có tên chứa 'micro' hoặc 'mic'
    query = f"'{image_folder_id}' in parents and (name contains 'micro' or name contains 'mic') and mimeType contains 'image/'"
    results = drive_service.files().list(q=query, pageSize=1, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])

    if items:
        micro_file = items[0]
        ext = '.png' if micro_file['mimeType'] == 'image/png' else '.jpg'
        download_file(drive_service, micro_file['id'], f'microphone{ext}')
    else:
        logging.warning("Không tìm thấy ảnh micro. Sẽ dùng Placeholder.")

    return True
