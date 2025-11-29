#./scripts/read_sheet.py
import os
import logging
import gspread
import hashlib
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CẤU HÌNH GOOGLE SHEET (DÙNG CỦA NGƯỜI DÙNG) ---
CREDS_FILE = 'service_account.json'
SHEET_NAME = 'podcast_requests'
SHEET_INDEX = 0 # Giả định dữ liệu nằm ở sheet đầu tiên

# --- HÀM KHỞI TẠO CLIENT VÀ SHEET ---
# Sử dụng cơ chế Auth mà người dùng cung cấp (oauth2client)
def initialize_sheet():
    """Khởi tạo và trả về worksheet (sheet1)"""
    load_dotenv()
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # 1. Xác thực bằng file service_account.json
        if not os.path.exists(CREDS_FILE):
             logging.error(f"Lỗi: Không tìm thấy file xác thực '{CREDS_FILE}'.")
             return None

        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
        client = gspread.authorize(creds)
        
        # 2. Mở Spreadsheet và Worksheet đầu tiên
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.get_worksheet(SHEET_INDEX) 
        
        logging.info(f"Đã kết nối thành công tới Sheet: {SHEET_NAME}")
        return worksheet

    except Exception as e:
        logging.error(f"Lỗi khi kết nối hoặc mở Google Sheet: {e}", exc_info=True)
        return None

# --- HÀM CHÍNH ĐƯỢC GỌI BỞI PIPELINE ---
def get_episode_data(episode_id: int):
    """
    Tải tất cả các bản ghi và tìm dữ liệu cho Episode ID cụ thể.
    """
    worksheet = initialize_sheet()
    if not worksheet:
        logging.error("Không thể lấy worksheet. Hủy bỏ quá trình đọc dữ liệu.")
        return None

    try:
        # Lấy tất cả dữ liệu dưới dạng danh sách các dictionary (header làm key)
        rows = worksheet.get_all_records()
        logging.info(f"Đã tải {len(rows)} bản ghi từ Google Sheet.")
        
        # Tìm dữ liệu cho Episode ID cụ thể
        for row in rows:
            # So sánh ID: cần chuyển đổi cả hai về chuỗi hoặc số nguyên cho chắc chắn
            if str(row.get('ID')) == str(episode_id):
                logging.info(f"Đã tìm thấy dữ liệu cho Episode ID {episode_id}.")
                return row
        
        # Nếu không tìm thấy
        logging.error(f"Không tìm thấy bản ghi Episode ID {episode_id} trong Google Sheet.")
        return None

    except Exception as e:
        logging.error(f"Lỗi khi đọc data từ Google Sheet: {e}", exc_info=True)
        return None

# --- LOGIC XỬ LÝ VÀ CẬP NHẬT SHEET CỦA NGƯỜI DÙNG (Đã đưa vào hàm riêng) ---
def generate_hash(text):
    """Tạo hash SHA256 đơn giản cho mục đích tạo thư mục."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:10]

def process_pending_requests():
    """
    Hàm này thực hiện logic cập nhật trạng thái và tạo hash cho các yêu cầu 'pending'.
    (Đây là logic được cung cấp trong yêu cầu của bạn).
    """
    worksheet = initialize_sheet()
    if not worksheet:
        return

    try:
        # Lấy tất cả các giá trị (bao gồm cả header) để có thể xác định chỉ số hàng
        rows_with_headers = worksheet.get_all_values()
        header = rows_with_headers[0]
        rows = worksheet.get_all_records()

        # Giả định cột 'status' là cột thứ N (index 0), 'hash' là cột thứ 7 (index 6)
        # Bắt đầu từ hàng 2 (idx=2) vì hàng 1 là header
        for idx, row in enumerate(rows, start=2):
            if row.get('status', '').lower() == 'pending':
                # Chắc chắn rằng các key tồn tại trước khi nối chuỗi
                title = row.get('title', '')
                character = row.get('character', '')
                core_theme = row.get('core_theme', '')

                text_hash = generate_hash(title + character + core_theme)
                
                # Cập nhật cột HASH (Giả sử cột G là cột 7, index 7, trong gspread là A=1)
                # Cập nhật cell(hàng, cột_số, giá trị)
                worksheet.update_cell(idx, 7, text_hash) 
                logging.info(f"Updated row {idx} with hash: {text_hash}")

                # Tạo thư mục cục bộ
                folder_path = os.path.join('assets', text_hash)
                os.makedirs(folder_path, exist_ok=True)
                logging.info(f"Created asset folder: {folder_path}")

    except Exception as e:
        logging.error(f"Lỗi khi xử lý các yêu cầu pending và cập nhật sheet: {e}", exc_info=True)

if __name__ == '__main__':
    # Ví dụ kiểm tra kết nối và đọc dữ liệu cho Episode ID 1
    # print(get_episode_data(1))
    
    # Ví dụ chạy quá trình cập nhật metadata cho các yêu cầu 'pending'
    # process_pending_requests()
    pass
