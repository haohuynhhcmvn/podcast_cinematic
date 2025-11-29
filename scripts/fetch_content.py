import os
import json
import logging
import hashlib
import gspread
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tên file credentials mà gspread sẽ sử dụng
CREDS_FILE = 'service_account.json'

def generate_hash(text: str) -> str:
    """Tạo SHA-256 hash từ chuỗi đầu vào, trả về 8 ký tự đầu."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]

def authenticate_google_sheet():
    """Đảm bảo file credentials tồn tại và trả về gspread client."""
    load_dotenv()
    
    # BƯỚC 1: TẠO FILE CREDENTIALS TỪ BIẾN MÔI TRƯỜNG (Fix lỗi File Not Found)
    service_account_content = os.getenv('SERVICE_ACCOUNT_CONTENT')
    if not service_account_content:
        logging.error("LỖI: Biến môi trường SERVICE_ACCOUNT_CONTENT không được thiết lập.")
        return None
        
    try:
        # Ghi chuỗi JSON thô vào file để gspread sử dụng
        json_data = json.loads(service_account_content)
        with open(CREDS_FILE, 'w') as f:
            json.dump(json_data, f)
        logging.info(f"Đã tạo/cập nhật file {CREDS_FILE} từ biến môi trường.")
    except Exception as e:
        logging.error(f"LỖI KHÔNG THỂ TẠO FILE {CREDS_FILE}. Kiểm tra SERVICE_ACCOUNT_CONTENT: {e}")
        return None
        
    # BƯỚC 2: XÁC THỰC BẰNG FILE VỪA TẠO
    try:
        # gspread.service_account là phương pháp hiện đại và đáng tin cậy
        gc = gspread.service_account(filename=CREDS_FILE)
        logging.info("Xác thực Google Sheet thành công.")
        return gc
    except Exception as e:
        logging.error(f"Lỗi xác thực Google Sheet: {e}")
        return None

def fetch_content():
    """
    Tìm tập 'pending' đầu tiên, tạo hash, tạo folder assets, và cập nhật trạng thái.
    """
    gc = authenticate_google_sheet()
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not gc or not sheet_id: return None

    try:
        sh = gc.open_by_key(sheet_id)
        # Sử dụng get_worksheet(0) để lấy Sheet đầu tiên
        worksheet = sh.get_worksheet(0) 
        list_of_records = worksheet.get_all_records()
        
    except Exception as e:
        logging.error(f"Lỗi khi đọc Sheet ID {sheet_id}: {e}")
        return None

    # Lặp qua các hàng để tìm và xử lý
    for idx, row in enumerate(list_of_records):
        row_index_in_sheet = idx + 2 # Hàng thực tế trong sheet
        
        # Giả định: Cột G (index 7) lưu hash, Cột F (index 6) lưu status.
        HASH_COL_INDEX = 7 
        STATUS_COL_INDEX = 6 
        
        # Lấy status và hash
        row_status = row.get('status', row.get('Status', '')).strip().lower()
        row_hash = row.get('text_hash', row.get('text_hash', '')).strip()

        # 1. Xử lý tập 'pending' hoặc tập cần tạo hash
        if row_status == 'pending':
            
            # --- TẠO HASH VÀ FOLDER ---
            content_to_hash = row.get('title', '') + row.get('character', '') + row.get('core_theme', '')
            text_hash = generate_hash(content_to_hash)
            
            # Cập nhật hash vào Sheet (Cột G)
            worksheet.update_cell(row_index_in_sheet, HASH_COL_INDEX, text_hash) 
            
            # Tạo folder assets
            folder_path = os.path.join('assets', text_hash)
            os.makedirs(folder_path, exist_ok=True)
            logging.info(f"Đã tạo hash: {text_hash} và folder tại: {folder_path}")
            
            # Cập nhật row_hash để hàng này được chọn cho bước tiếp theo
            row_hash = text_hash

        # 2. Xử lý hàng vừa có hash (hoặc đã có hash) và chưa được processed
        if row_hash and row_status != 'processed' and row_status != 'completed' and row_status != 'failed' and row_status != 'processing':
            
            # --- CẬP NHẬT TRẠNG THÁI: 'PROCESSING' ---
            worksheet.update_cell(row_index_in_sheet, STATUS_COL_INDEX, 'processing') 
            logging.info(f"Đã đánh dấu hàng {row_index_in_sheet} ('{row.get('title')}') là 'processing'.")

            # --- TRẢ VỀ DỮ LIỆU ĐÃ TÌM THẤY ---
            episode_data = {
                'ID': row_index_in_sheet,
                'title': row.get('title', '').strip(),
                'character': row.get('character', '').strip(),
                'core_theme': row.get('core_theme', '').strip(),
                'text_hash': row_hash
            }
            return episode_data

    logging.info("Không tìm thấy tập nào mới để xử lý.")
    return None

def update_sheet_status(episode_id: int, status: str):
    """Cập nhật trạng thái cuối cùng (processed/failed) trên Google Sheet."""
    gc = authenticate_google_sheet()
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not gc or not sheet_id: return

    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0)
        # Giả định cột status là cột F (index 6)
        worksheet.update_cell(episode_id, 6, status.lower())
        logging.info(f"Đã cập nhật trạng thái cho Episode ID {episode_id} thành '{status.lower()}'.")
    except Exception as e:
        logging.error(f"Lỗi khi cập nhật trạng thái cuối cùng cho Episode ID {episode_id}: {e}")

if __name__ == "__main__":
    # Ví dụ chạy thử
    data = fetch_content()
    if data:
        logging.info(f"Đã tìm thấy tập để xử lý: {data['title']}")
        # update_sheet_status(data['ID'], 'failed') # Ví dụ cập nhật lại
