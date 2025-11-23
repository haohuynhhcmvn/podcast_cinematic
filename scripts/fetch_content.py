import os
import io
import re
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
import gspread
from utils import generate_hash, ensure_dir, sanitize_filename

# CONFIG
SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_ID = "1qSbdDEEP6pGvWGBiYdCFroSfjtWbNskwCmEe0vjkQdI"
INPUT_IMAGES_ROOT = "inputs/images"

# Cấu hình tên cột trong Google Sheet của bạn
COLUMN_MAP = {
    "title_key": "Name",          # Cột B: Dùng cho tiêu đề/tên tập
    "character_key": "Name",      # Cột B: Dùng cho Tên nhân vật (vì bạn không có cột Character)
    "core_theme_key": "CoreTheme",# Cột C: Dùng cho Chủ đề cốt lõi
    "img_folder_key": "ImageFolder", # Cột E: Dùng cho Link thư mục ảnh
    "status_key": "Status",       # Cột F: Dùng để kiểm tra trạng thái
    "hash_column_index": 7        # Cột G: Vị trí cột HASH (Bắt đầu từ 1. Cột G là 7)
}

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets" # Quyền ĐỌC VÀ GHI
]

def get_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive = build("drive", "v3", credentials=creds)
    return drive, creds

def download_file_from_drive(drive, file_id, dest_path):
    request = drive.files().get_media(fileId=file_id)
    fh = io.FileIO(dest_path, mode="wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return dest_path

def list_files_in_folder(drive, folder_id):
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
    # accept drive folder url or bare id
    if "folders/" in url:
        m = re.search(r"/folders/([a-zA-Z0-9-_]+)", url)
        if m:
            return m.group(1)
    return url.strip()

def fetch_and_download():
    drive, creds = get_service()
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    sh = gc.open_by_key(SHEET_ID)
    
    # Giả định dữ liệu nằm ở Sheet đầu tiên (sheet1)
    sheet = sh.sheet1
    
    # get_all_records() trả về dictionary sử dụng tiêu đề cột làm key
    rows = sheet.get_all_records()
    
    # gspread bắt đầu đếm hàng từ 1. get_all_records() bỏ qua hàng 1 (tiêu đề).
    # Hàng 1 trong Python (idx=0) tương ứng với Hàng 2 trong Sheet.
    for idx, r in enumerate(rows, start=2):
        # Sử dụng COLUMN_MAP để lấy tên cột từ Sheet của bạn
        status = str(r.get(COLUMN_MAP["status_key"],"")).strip().lower()
        if status != "pending":
            continue

        title = r.get(COLUMN_MAP["title_key"]) or f"episode_{idx}"
        character = r.get(COLUMN_MAP["character_key"], "")
        core_theme = r.get(COLUMN_MAP["core_theme_key"], "")
        folder_link = r.get(COLUMN_MAP["img_folder_key"], "")
        
        # Tạo hash từ dữ liệu
        text_hash = generate_hash(f"{title}|{character}|{core_theme}")
        
        # Ghi lại hash vào Sheet (Cột G)
        hash_col = COLUMN_MAP["hash_column_index"]
        sheet.update_cell(idx, hash_col, text_hash)
        
        target_dir = os.path.join(INPUT_IMAGES_ROOT, text_hash)
        ensure_dir(target_dir)
        
        if not folder_link:
            print(f"Bỏ qua '{title}': Không có link ImageFolder.")
            continue
        
        folder_id = get_folder_id_from_url(folder_link)
        files = list_files_in_folder(drive, folder_id)
        
        # Tải file ảnh
        for f in files:
            name = sanitize_filename(f.get("name","unnamed"))
            mime = f.get("mimeType","")
            if mime.startswith("image/") or name.lower().endswith((".jpg",".jpeg",".png",".webp")):
                dest = os.path.join(target_dir, name)
                if not os.path.exists(dest):
                    print(f"Downloading {name} to {dest}")
                    download_file_from_drive(drive, f["id"], dest)
    print("Fetch content finished.")

if __name__ == "__main__":
    fetch_and_download()
