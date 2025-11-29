# scripts/fetch_content.py
import os
import json
import gspread
import logging
import hashlib
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- HÀM HỖ TRỢ ---

def generate_hash(text: str) -> str:
    """Tạo SHA256 hash 8 ký tự từ chuỗi văn bản."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]

def authenticate_google_sheet():
    """
    Xác thực gspread linh hoạt:
    1. Kiểm tra nếu biến môi trường là nội dung JSON (String).
    2. Nếu không, kiểm tra nếu nó là đường dẫn file (Path).
    """
    load_dotenv()
    
    # Lấy giá trị từ biến môi trường (có thể là đường dẫn HOẶC nội dung JSON raw)
    creds_raw = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    
    if not creds_raw:
        logging.error("❌ Biến môi trường GOOGLE_SERVICE_ACCOUNT_JSON chưa được cài đặt.")
        return None
        
    try:
        # TRƯỜNG HỢP 1: Biến môi trường chứa toàn bộ nội dung JSON (Thường dùng trên GitHub Actions)
        if creds_raw.strip().startswith('{'):
            creds_dict = json.loads(creds_raw)
            gc = gspread.service_account_from_dict(creds_dict)
            logging.info("✅ Xác thực thành công bằng nội dung JSON (Environment Variable).")
            return gc

        # TRƯỜNG HỢP 2: Biến môi trường là đường dẫn file (File Path)
        elif os.path.exists(creds_raw):
            gc = gspread.service_account(filename=creds_raw)
            logging.info(f"✅ Xác thực thành công bằng file: {creds_raw}")
            return gc
        
        else:
            logging.error(f"❌ Không tìm thấy file hoặc nội dung JSON không hợp lệ: {creds_raw}")
            return None

    except Exception as e:
        logging.error(f"❌ Lỗi xác thực Google Sheet: {e}")
        return None

def get_column_index(worksheet, header_name):
    """Tìm chỉ mục cột (1-based) dựa trên tiêu đề cột linh hoạt."""
    try:
        headers = worksheet.row_values(1) # Hàng 1 là headers
        for idx, header in enumerate(headers, start=1):
            if str(header).strip().lower() == header_name.lower():
                return idx
        return None
    except Exception as e:
        logging.error(f"Lỗi khi tìm chỉ mục cột '{header_name}': {e}")
        return None

# --- HÀM CHÍNH ---

def fetch_content():
    """
    Lấy bản ghi 'pending', tạo hash, tạo thư mục assets và chuyển trạng thái sang 'PROCESSING'.
    """
    # authenticate_google_sheet đã tự gọi load_dotenv
    gc = authenticate_google_sheet()
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not gc or not sheet_id: 
        return None

    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0) # Lấy sheet đầu tiên
        list_of_dicts = worksheet.get_all_records() 
        
        episode_to_process = None
        row_to_update = None 
        
        # 1. TÌM KIẾM HÀNG 'PENDING'
        for list_index, row in enumerate(list_of_dicts):
            if row.get('Status', '').strip().lower() == 'pending':
                episode_to_process = row
                row_to_update = list_index + 2 # Hàng thực tế trên Sheet (Hàng 1 là header)
                break
        
        if episode_to_process and row_to_update:
            episode_id = episode_to_process.get('ID', row_to_update - 1)
            episode_name = episode_to_process.get('Name')
            
            # --- TẠO HASH VÀ THƯ MỤC ASSETS ---
            # Tạo chuỗi nguồn để hash (kết hợp Title, Character, Theme) để đảm bảo duy nhất
            hash_source = str(episode_to_process.get('Name', '')) + \
                          str(episode_to_process.get('ContentInput', '')) + \
                          str(episode_to_process.get('CoreTheme', ''))
            
            text_hash = generate_hash(hash_source)
            
            # Lưu hash vào dictionary data để các bước sau dùng
            episode_to_process['text_hash'] = text_hash
            
            # Tạo thư mục assets/{hash}
            folder_path = os.path.join('assets', text_hash)
            os.makedirs(folder_path, exist_ok=True)
            logging.info(f"📂 Đã tạo hash: {text_hash} và folder: {folder_path}")
            
            # --- CẬP NHẬT TRẠNG THÁI VÀ HASH TRÊN SHEET ---
            
            # Tìm cột Status và Hash động (tránh hardcode số cột)
            status_col = get_column_index(worksheet, 'Status')
            hash_col = get_column_index(worksheet, 'Hash') # Nếu bạn có cột Hash trên sheet

            if status_col:
                worksheet.update_cell(row_to_update, status_col, 'PROCESSING')
                logging.info(f"🔄 Đã cập nhật trạng thái tập '{episode_name}' -> PROCESSING.")
            
            if hash_col:
                worksheet.update_cell(row_to_update, hash_col, text_hash)
                logging.info(f"📝 Đã ghi Hash vào Sheet.")

            # --- CHUẨN BỊ DỮ LIỆU TRẢ VỀ (MAPPING CHUẨN) ---
            # Mapping lại tên cột từ Sheet (ContentInput) sang tên biến code dùng (Content/Input)
            processed_data = {
                'ID': episode_id,
                'Name': episode_name,
                
                'Core Theme': episode_to_process.get('CoreTheme', ''),
                'Content/Input': episode_to_process.get('ContentInput', ''),
                'ImageFolder': episode_to_process.get('ImageFolder', ''),
                
                'text_hash': text_hash,        
                'Status_Row': row_to_update    
            }
            return processed_data
        else:
            logging.info("ℹ️ Không có tập nào có Status là 'pending'.")
            return None

    except Exception as e:
        logging.error(f"❌ Lỗi trong quá trình lấy nội dung từ Sheet: {e}", exc_info=True)
        return None

def update_episode_status(row_index: int, status: str):
    """Cập nhật trạng thái của tập trên Google Sheet."""
    gc = authenticate_google_sheet()
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not gc or not sheet_id: return

    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0)
        
        status_col = get_column_index(worksheet, 'Status')
        
        if status_col and row_index > 1:
            worksheet.update_cell(row_index, status_col, status)
            logging.info(f"✅ Đã cập nhật trạng thái hàng {row_index} thành '{status}'.")
        else:
            logging.warning(f"⚠️ Không tìm thấy cột Status hoặc hàng không hợp lệ.")

    except Exception as e:
        logging.error(f"❌ LỖI CẬP NHẬT TRẠNG THÁI: {e}")

if __name__ == '__main__':
    # Test chạy thử
    fetch_content()
