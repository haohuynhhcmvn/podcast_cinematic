import os
import json
import gspread
import logging
import hashlib
from dotenv import load_dotenv
from utils import get_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]

def authenticate_google_sheet():
    load_dotenv()
    # Ưu tiên đọc nội dung JSON từ biến môi trường (GitHub Actions)
    creds_content = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT')
    
    # Fallback: Đọc từ file (Local)
    if not creds_content:
        creds_content = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')

    if not creds_content:
        logger.error("❌ Thiếu biến môi trường GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT")
        return None
        
    try:
        if creds_content.strip().startswith('{'):
            creds_dict = json.loads(creds_content)
            return gspread.service_account_from_dict(creds_dict)
        elif os.path.exists(creds_content):
            return gspread.service_account(filename=creds_content)
        else:
            logger.error("❌ Credential không hợp lệ.")
            return None
    except Exception as e:
        logger.error(f"❌ Lỗi Auth Sheet: {e}")
        return None

def fetch_content():
    gc = authenticate_google_sheet()
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not gc or not sheet_id: return None

    try:
        sh = gc.open_by_key(sheet_id)
        ws = sh.get_worksheet(0)
        records = ws.get_all_records()
        
        target_row = None
        row_idx = -1

        for i, row in enumerate(records):
            if row.get('Status', '').strip().lower() == 'pending':
                target_row = row
                row_idx = i + 2 
                break
        
        if not target_row:
            logger.info("ℹ️ Không có task 'pending'.")
            return None

        # Tạo Hash & Folder Assets
        hash_src = f"{target_row.get('Name')}{target_row.get('ContentInput')}"
        text_hash = generate_hash(hash_src)
        os.makedirs(get_path('assets', text_hash), exist_ok=True)

        # Cập nhật Status -> PROCESSING
        try:
            col_idx = ws.find("Status").col
        except:
            col_idx = 6
        ws.update_cell(row_idx, col_idx, 'PROCESSING')
        
        # MAPPING DỮ LIỆU CHUẨN
        return {
            'data': {
                'ID': target_row.get('ID'),
                'Name': target_row.get('Name'),
                'Core Theme': target_row.get('CoreTheme', ''),     # Sửa lỗi tên cột
                'Content/Input': target_row.get('ContentInput', ''), # Sửa lỗi tên cột
                'ImageFolder': target_row.get('ImageFolder', ''),
                'text_hash': text_hash,
            },
            'row_idx': row_idx,
            'col_idx': col_idx,
            'worksheet': ws
        }

    except Exception as e:
        logger.error(f"❌ Lỗi Fetch: {e}")
        return None
