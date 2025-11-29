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
    Xác thực gspread bằng cách đọc nội dung JSON trực tiếp từ biến môi trường:
    GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT
    """
    load_dotenv()
    
    # 1. Ưu tiên đọc nội dung JSON Raw từ biến GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT
    creds_content = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT')
    
    # 2. Fallback: Nếu không có, thử tìm biến cũ hoặc đường dẫn file (đề phòng chạy local)
    if not creds_content:
        creds_content = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')

    if not creds_content:
        logging.error("❌ Không tìm thấy biến môi trường GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT.")
        return None
        
    try:
        # TRƯỜNG HỢP 1: Biến chứa nội dung JSON (Bắt đầu bằng dấu {)
        # Đây là cách bạn dùng trên GitHub Actions với Secret
        if creds_content.strip().startswith('{'):
            creds_dict = json.loads(creds_content)
            gc = gspread.service_account_from_dict(creds_dict)
            logging.info("✅ Xác thực thành công bằng NỘI DUNG JSON (từ GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT).")
            return gc

        # TRƯỜNG HỢP 2: Biến là đường dẫn file (Nếu chạy local và trỏ vào file)
        elif os.path.exists(creds_content):
            gc = gspread.service_account(filename=creds_content)
            logging.info(f"✅ Xác thực thành công bằng FILE: {creds_content}")
            return gc
        
        else:
            logging.error("❌ Nội dung biến môi trường không phải là JSON hợp lệ hoặc đường dẫn file không tồn tại.")
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
    Lấy bản ghi 'pending', tạo hash, folder assets và trả về dữ liệu đã map đúng tên cột.
    """
    gc = authenticate_google_sheet()
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not gc or not sheet_id: 
        return None

    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0) 
        list_of_dicts = worksheet.get_all_records() 
        
        episode_to_process = None
        row_to_update = None 
        
        # 1. TÌM KIẾM HÀNG 'PENDING'
        for list_index, row in enumerate(list_of_dicts):
            if row.get('Status', '').strip().lower() == 'pending':
                episode_to_process = row
                row_to_update = list_index + 2 
                break
        
        if episode_to_process and row_to_update:
            episode_id = episode_to_process.get('ID', row_to_update - 1)
            episode_name = episode_to_process.get('Name')
            
            # --- TẠO HASH ---
            # Dùng đúng key từ Sheet của bạn: Name, ContentInput, CoreTheme
            hash_source = str(episode_to_process.get('Name', '')) + \
                          str(episode_to_process.get('ContentInput', '')) + \
                          str(episode_to_process.get('CoreTheme', ''))
            
            text_hash = generate_hash(hash_source)
            episode_to_process['text_hash'] = text_hash
            
            # Tạo folder assets
            folder_path = os.path.join('assets', text_hash)
            os.makedirs(folder_path, exist_ok=True)
            logging.info(f"📂 Hash: {text_hash} | Folder: {folder_path}")
            
            # --- CẬP NHẬT SHEET ---
            status_col = get_column_index(worksheet, 'Status')
            hash_col = get_column_index(worksheet, 'Hash') 

            if status_col:
                worksheet.update_cell(row_to_update, status_col, 'PROCESSING')
                logging.info(f"🔄 Đã cập nhật trạng thái '{episode_name}' -> PROCESSING.")
            
            if hash_col:
                worksheet.update_cell(row_to_update, hash_col, text_hash)

            # --- MAPPING DỮ LIỆU CHUẨN ---
            processed_data = {
                'ID': episode_id,
                'Name': episode_name,
                
                # Mapping đúng cột Sheet (viết liền) -> Biến Code (có dấu / hoặc cách)
                'Core Theme': episode_to_process.get('CoreTheme', ''),
                'Content/Input': episode_to_process.get('ContentInput', ''),
                'ImageFolder': episode_to_process.get('ImageFolder', ''),
                
                'text_hash': text_hash,        
                'Status_Row': row_to_update    
            }
            return processed_data
        else:
            logging.info("ℹ️ Không có tập nào 'pending'.")
            return None

    except Exception as e:
        logging.error(f"❌ Lỗi Fetch Content: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    fetch_content()
