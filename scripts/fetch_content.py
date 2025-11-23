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
SHEET_NAME = "podcast_requests"   # đổi theo sheet bạn dùng
INPUT_IMAGES_ROOT = "inputs/images"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly"
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
    sh = gc.open(SHEET_NAME)
    sheet = sh.sheet1
    rows = sheet.get_all_records()
    for idx, r in enumerate(rows, start=2):
        if str(r.get("status","")).strip().lower() != "pending":
            continue
        title = r.get("title") or r.get("character") or f"episode_{idx}"
        core_theme = r.get("core_theme","")
        character = r.get("character","")
        folder_link = r.get("img_folder","")
        text_hash = generate_hash(f"{title}|{character}|{core_theme}")
        # write back hash to sheet
        sheet.update_cell(idx, 7, text_hash)  # assuming G column is hash
        target_dir = os.path.join(INPUT_IMAGES_ROOT, text_hash)
        ensure_dir(target_dir)
        if not folder_link:
            continue
        folder_id = get_folder_id_from_url(folder_link)
        files = list_files_in_folder(drive, folder_id)
        # download image files only
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
