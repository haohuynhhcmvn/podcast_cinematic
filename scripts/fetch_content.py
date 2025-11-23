import os
import io
import re
import sys
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import gspread # Import gspread

from scripts.utils import generate_hash, ensure_dir, sanitize_filename

# CONFIG
SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_ID = "1qSbdDEEP6pGvWGBiYdCFroSfjtWbNskwCmEe0vjkQdI"
INPUT_IMAGES_ROOT = "inputs/images"

# Cấu hình ánh xạ cột
COLUMN_MAP = {
    "title_key": "Name",
    "character_key": "Name",
    "core_theme_key": "CoreTheme",
    "img_folder_key": "ImageFolder",
    "status_key": "Status",
    "hash_column_index": 7  # Cột G
}

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

def get_drive_service(creds):
    """Khởi tạo dịch vụ Google Drive."""
    return build("drive", "v3", credentials=creds)

def get_sheet_service():
    """
    Khởi tạo kết nối Google Sheet bằng Service Account. 
    (Đã sửa lỗi ModuleNotFoundError bằng cách dùng gspread.service_account)
    """
    return gspread.service_account(filename=SERVICE_ACCOUNT_FILE)

def download_file_from_drive(drive, file_id, dest_path):
    """Tải một file từ Google Drive."""
    request = drive.files().get_media(fileId=file_id)
    fh = io.FileIO(dest_path, mode="wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return dest_path

def list_files_in_folder(drive, folder_id):
    """Liệt kê các file trong một thư mục Drive."""
    files = []
    page_token = None
    q = f"'{folder_id}' in parents and trashed=false"
    while True:
        res = drive.files().list(q=q, spaces='drive', fields='nextPageToken, files(id,name,mimeType)', pageToken=page_token).execute()
        for f in res.get('files', []):
            files.append(f)
        page_token = res.get('nextPageToken', None)
        if page_token is None:
            break
    return files

def get_folder_id_from_url(url: str):
    """Trích xuất ID thư mục từ link Drive."""
    if not url:
        return None
    url = url.strip()
    # Thử trích xuất ID từ URL
    if "folders/" in url:
        m = re.search(r"/folders/([a-zA-Z0-9-_]+)", url)
        if m:
            return m.group(1)
    # Nếu không phải URL đầy đủ, có thể nó đã là ID
    if len(url) > 10: # Độ dài ID Drive thường lớn
        return url
    return None

def fetch_and_download():
    # 1. Khởi tạo dịch vụ
    try:
        # Khởi tạo Creds cho Google API Client (Drive)
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        drive = get_drive_service(creds)
        # Khởi tạo Gspread
        gc = get_sheet_service()
        sh = gc.open_by_key(SHEET_ID)
        sheet = sh.sheet1
        rows = sheet.get_all_records()
    except Exception as e:
        print(f"LỖI KHỞI TẠO DỊCH VỤ: {e}")
        return

    print("Bắt đầu fetch và cập nhật Hash...")
    
    # Bắt đầu duyệt từ hàng thứ 2 (idx=2) vì hàng 1 là tiêu đề
    for idx, r in enumerate(rows, start=2):
        status = str(r.get(COLUMN_MAP["status_key"],"")).strip().lower()
        title = r.get(COLUMN_MAP["title_key"]) or f"episode_{idx}"
        
        # Chỉ xử lý các hàng đang chờ
        if status != "pending":
            continue

        # Lấy các trường dữ liệu để tạo Hash
        character = r.get(COLUMN_MAP["character_key"], "")
        core_theme = r.get(COLUMN_MAP["core_theme_key"], "")
        folder_link = r.get(COLUMN_MAP["img_folder_key"], "")
        
        # Tạo Hash từ các trường quan trọng (đảm bảo tính nhất quán)
        text_hash = generate_hash(f"{title}|{character}|{core_theme}")
        
        # Ghi Hash vào Sheet (Cột G)
        try:
            # Gspread dùng index 1, idx là số hàng thực tế
            sheet.update_cell(idx, COLUMN_MAP["hash_column_index"], text_hash)
            print(f"Cập nhật Hash cho {title}: {text_hash}")
        except Exception as e:
            print(f"Lỗi ghi Hash hàng {idx}: {e}")
            continue
        
        # Tải ảnh
        if not folder_link:
            print(f"Bỏ qua tải ảnh cho {title}: Không có link thư mục ảnh.")
            continue
        
        target_dir = os.path.join(INPUT_IMAGES_ROOT, text_hash)
        ensure_dir(target_dir)
        
        folder_id = get_folder_id_from_url(folder_link)
        if not folder_id:
            # Sửa lỗi thụt lề: Đảm bảo print và continue thụt lề 4 space
            print(f"LỖI: Không trích xuất được Folder ID hợp lệ từ link: {folder_link}")
            continue
             
        try:
            files = list_files_in_folder(drive, folder_id)
            print(f"Tìm thấy {len(files)} file trong thư mục Drive ID: {folder_id}")
            for f in files:
                name = sanitize_filename(f.get("name","unnamed"))
                mime = f.get("mimeType","")
                # Chỉ tải về các file ảnh
                if mime.startswith("image/") or name.lower().endswith((".jpg",".jpeg",".png",".webp")):
                    dest = os.path.join(target_dir, name)
                    if not os.path.exists(dest):
                        print(f"  Downloading image: {name}")
                        download_file_from_drive(drive, f["id"], dest)
        except Exception as e:
            print(f"Lỗi tải ảnh từ Drive Folder ID '{folder_id}': {e}")

    print("Fetch content finished.")

if __name__ == "__main__":
    fetch_and_download()
