# File: ./scripts/fetch_content.py
# Chức năng: Kết nối Google Sheet, lấy danh sách tập 'pending', tạo hash, và cập nhật trạng thái.

import os
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import hashlib
import json
import sys
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- HÀM HỖ TRỢ ---
def create_service_account_file():
    """Tạo file service_account.json từ biến môi trường SERVICE_ACCOUNT_CONTENT."""
    sa_content = os.getenv("SERVICE_ACCOUNT_CONTENT")
    if not sa_content:
        logging.error("Biến môi trường SERVICE_ACCOUNT_CONTENT không được định nghĩa.")
        sys.exit(1) 
    
    try:
        sa_data = json.loads(sa_content)
        with open('service_account.json', 'w', encoding='utf-8') as f:
            json.dump(sa_data, f, ensure_ascii=False, indent=4)
        logging.info("Đã tạo/cập nhật file service_account.json từ biến môi trường.")
        return True
    except Exception as e:
        logging.error(f"Lỗi khi giải mã SERVICE_ACCOUNT_CONTENT. Kiểm tra định dạng JSON. Lỗi: {e}")
        sys.exit(1)
        return False

def generate_hash(text: str) -> str:
    """Tạo SHA256 hash từ chuỗi văn bản."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]

def authorize_gspread():
    """Thực hiện xác thực và trả về client GSpread."""
    # Đảm bảo file credentials tồn tại trước khi authorize
    if not os.path.exists('service_account.json'):
         create_service_account_file()

    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        # Chờ 5 giây để đảm bảo file service_account.json đã được ghi hoàn tất
        time.sleep(5) 
        creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', scope)
        client = gspread.authorize(creds)
        logging.info("Xác thực Google Sheet thành công.")
        return client
    except Exception as e:
        logging.error(f"LỖI XÁC THỰC GOOGLE SHEET: {e}")
        return None

# --- HÀM CHÍNH ---

def fetch_pending_episodes() -> list:
    """
    Lấy danh sách các tập có trạng thái 'pending' từ Google Sheet.
    Cập nhật hash (cột G) và tạo thư mục assets.
    """
    client = authorize_gspread()
    if not client: return []
    
    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            logging.error("Thiếu GOOGLE_SHEET_ID trong biến môi trường.")
            return []
            
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Lấy toàn bộ dữ liệu dưới dạng Dictionary
        rows = sheet.get_all_records()
        
        episodes_to_process = []
        
        # Duyệt qua các hàng (bắt đầu từ hàng 2 trên Sheet vì hàng 1 là header)
        for idx, row in enumerate(rows, start=2):
            if row.get('status', '').lower() == 'pending':
                
                # Cột ID trên sheet là cột A (index 1)
                episode_id = row.get('ID', idx - 1) 
                
                # Các cột cần hash: 'title', 'character', 'core_theme'
                hash_source = str(row.get('title', '')) + str(row.get('character', '')) + str(row.get('core_theme', ''))
                text_hash = generate_hash(hash_source)

                # Cập nhật hash vào Sheet (Giả sử cột Hash là cột G - Index 7)
                sheet.update_cell(idx, 7, text_hash) 
                
                # Tạo folder assets
                folder_path = os.path.join('assets', text_hash)
                os.makedirs(folder_path, exist_ok=True)
                logging.info(f"Đã tạo hash: {text_hash} và folder tại: {folder_path}")
                
                # Thêm dữ liệu vào danh sách xử lý
                row['row_index'] = idx
                row['text_hash'] = text_hash
                row['ID'] = episode_id
                episodes_to_process.append(row)
                
                # Đánh dấu là 'processing' ngay lập tức
                # Cột status là F (Index 6)
                sheet.update_cell(idx, 6, 'processing') 
                logging.info(f"Đã đánh dấu hàng {idx} ('{row.get('title')}') là 'processing'.")

        return episodes_to_process

    except Exception as e:
        logging.error(f"LỖI ĐỌC DỮ LIỆU GOOGLE SHEET: {e}", exc_info=True)
        return []

def update_episode_status(episode_id: int, status: str):
    """Cập nhật trạng thái của tập trên Google Sheet (Cột F)."""
    client = authorize_gspread()
    if not client: return

    try:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            logging.error("Thiếu GOOGLE_SHEET_ID trong biến môi trường.")
            return

        sheet = client.open_by_key(sheet_id).sheet1
        
        # Tìm hàng dựa trên ID (giả sử cột A là cột ID - Index 1)
        cell = sheet.find(str(episode_id), in_column=1) 
        
        if cell:
            row_index = cell.row
            # Cột status là F (Index 6)
            sheet.update_cell(row_index, 6, status) 
            logging.info(f"Đã cập nhật trạng thái cho Episode ID {episode_id} thành '{status}'.")
        else:
            logging.warning(f"Không tìm thấy Episode ID {episode_id} để cập nhật trạng thái.")

    except Exception as e:
        logging.error(f"LỖI CẬP NHẬT TRẠNG THÁI GOOGLE SHEET cho ID {episode_id}: {e}", exc_info=True)
