# scripts/get_episode_data.py: Tích hợp logic xử lý Sheet để tránh lỗi ImportError từ read_sheet.py
import os
import logging
import importlib.util
import hashlib
import gspread
from oauth2client.service_account import ServiceAccountCredentials # Cần thiết cho gspread

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. LOGIC HASH ĐỘC LẬP ---
# Tự định nghĩa generate_hash để loại bỏ phụ thuộc vào utils.py
def generate_hash(text: str) -> str:
    """Tạo SHA-256 hash từ chuỗi đầu vào, trả về 8 ký tự đầu."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]

# --- 2. LOGIC KHỞI TẠO GOOGLE SHEET ĐỘC LẬP (Lấy từ read_sheet.py) ---
try:
    # Cấu hình Google Sheet (Giả định các biến này đã được read_sheet.py sử dụng)
    CREDS_FILE = 'service_account.json'
    SHEET_NAME = 'podcast_requests'

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
    CLIENT = gspread.authorize(creds)
    SHEET = CLIENT.open(SHEET_NAME).sheet1
    logging.info("Đã kết nối thành công với Google Sheet.")

except Exception as e:
    logging.error(f"LỖI KHI KẾT NỐI GOOGLE SHEET: {e}", exc_info=True)
    # Khởi tạo SHEET rỗng để tránh lỗi nếu không kết nối được
    SHEET = None


def get_next_episode_data():
    """
    1. Tự thực thi logic tạo hash và folder nếu có hàng 'pending'.
    2. Đọc lại Sheet để tìm hàng vừa được đánh dấu/tạo hash.
    3. Cập nhật trạng thái sang 'PROCESSING' và trả về dữ liệu.
    """
    if SHEET is None:
        return None

    try:
        rows = SHEET.get_all_records()
    except Exception as e:
        logging.error(f"Lỗi khi đọc dữ liệu từ Sheet: {e}", exc_info=True)
        return None
        
    found_pending = False
    
    # 1. Tự thực thi logic tạo hash/folder (Lấy từ read_sheet.py gốc)
    for idx, row in enumerate(rows):
        row_index_in_sheet = idx + 2 # Hàng thực tế trong sheet
        
        # Giả định: Cột G (index 7) lưu hash, Cột F (index 6) lưu status.
        HASH_COL_INDEX = 7 
        STATUS_COL_INDEX = 6 
        
        # GSpread sử dụng __EMPTY_N nếu không có tiêu đề cột
        row_hash = row.get(f'__EMPTY_{HASH_COL_INDEX - 1}', '').strip()
        row_status = row.get('status', '').strip().lower()

        if row_status == 'pending':
            found_pending = True
            
            # Tạo hash mới
            content_to_hash = row['title'] + row['character'] + row['core_theme']
            text_hash = generate_hash(content_to_hash)
            
            # Ghi hash vào Sheet (Cột G)
            try:
                SHEET.update_cell(row_index_in_sheet, HASH_COL_INDEX, text_hash) 
            except Exception as e:
                logging.warning(f"Không thể cập nhật hash cho hàng {row_index_in_sheet}: {e}")
            
            # Tạo folder
            folder_path = os.path.join('assets', text_hash)
            os.makedirs(folder_path, exist_ok=True)
            logging.info(f"Đã tạo hash: {text_hash} và folder tại: {folder_path}")
            
            # Dừng lại ở hàng đầu tiên 'pending' và tiếp tục xử lý ở bước 2

        # 2. TÌM HÀNG VỪA ĐƯỢC XỬ LÝ (hoặc hàng đã có hash mà chưa xong)
        # Sử dụng các khóa chính xác: title, character, core_theme
        if row_hash and row_status != 'processed' and row_status != 'completed' and row_status != 'failed' and row_status != 'processing':
            
            # --- ĐÁNH DẤU TRẠNG THÁI 'PROCESSING' ---
            try:
                SHEET.update_cell(row_index_in_sheet, STATUS_COL_INDEX, 'processing') 
                logging.info(f"Đã đánh dấu hàng {row_index_in_sheet} ('{row.get('title')}') là 'processing'.")
            except Exception as e:
                logging.warning(f"Không thể cập nhật trạng thái 'processing' trên Sheet: {e}")

            # --- TRẢ VỀ DỮ LIỆU ĐÃ TÌM THẤY ---
            episode_data = {
                'ID': row_index_in_sheet,
                'title': row.get('title', '').strip(),
                'character': row.get('character', '').strip(),
                'core_theme': row.get('core_theme', '').strip(),
                'text_hash': row_hash
            }
            return episode_data
    
    # Nếu không tìm thấy hàng 'pending' nào để xử lý, log và kết thúc.
    if not found_pending:
        logging.info("Không tìm thấy tập nào mới để xử lý.")
        
    logging.info("Không tìm thấy tập nào đã được tạo hash mà chưa xử lý.")
    return None


def update_sheet_status(episode_id: int, status: str):
    """Cập nhật trạng thái cuối cùng (processed/failed) trên Google Sheet."""
    if SHEET is None:
        logging.error("Không thể cập nhật trạng thái vì kết nối Sheet thất bại.")
        return
        
    try:
        # Giả định cột status là cột F (index 6)
        SHEET.update_cell(episode_id, 6, status.lower())
        logging.info(f"Đã cập nhật trạng thái cho Episode ID {episode_id} thành '{status.lower()}'.")
    except Exception as e:
        logging.error(f"Lỗi khi cập nhật trạng thái cuối cùng cho Episode ID {episode_id}: {e}")
