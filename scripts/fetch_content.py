# /scripts/fetch_content.py
# Chức năng: Kết nối Google Sheet, lấy bản ghi 'pending', TẠO HASH/THƯ MỤC,
# và cập nhật trạng thái sang 'PROCESSING' một cách an toàn.

import os
import json
import gspread
import logging
import hashlib # Cần thiết cho việc tạo hash
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- HÀM HỖ TRỢ ---

def generate_hash(text: str) -> str:
    """Tạo SHA256 hash 8 ký tự từ chuỗi văn bản."""
    # Đảm bảo các trường Title, Character, Core Theme được kết hợp để tạo hash duy nhất
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:8]

def authenticate_google_sheet():
    """Xác thực gspread bằng Service Account JSON."""
    load_dotenv()
    service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') 
    
    if not service_account_file or not os.path.exists(service_account_file):
        logging.error(f"File Service Account JSON không tồn tại tại: {service_account_file}")
        return None
        
    try:
        gc = gspread.service_account(filename=service_account_file)
        logging.info("Xác thực Google Sheet thành công.")
        return gc
    except Exception as e:
        logging.error(f"Lỗi xác thực Google Sheet: {e}")
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
    load_dotenv()
    gc = authenticate_google_sheet()
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not gc or not sheet_id: 
        return None

    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0) # Lấy sheet đầu tiên
        list_of_dicts = worksheet.get_all_records() # Trả về list of dicts, index bắt đầu từ hàng 2 trên Sheet
        
        episode_to_process = None
        row_to_update = None # Số hàng thực tế trên Sheet (bắt đầu từ 2)
        
        # 1. TÌM KIẾM HÀNG 'PENDING' ĐÁNG TIN CẬY
        # Dùng enumerate để tìm đúng chỉ mục hàng (list_index + 2 = sheet_row_index)
        for list_index, row in enumerate(list_of_dicts):
            # Kiểm tra trạng thái linh hoạt (không phân biệt chữ hoa/thường)
            if row.get('Status', '').strip().lower() == 'pending':
                episode_to_process = row
                row_to_update = list_index + 2 # Hàng thực tế trên Sheet (Hàng 1 là header)
                break
        
        if episode_to_process and row_to_update:
            episode_id = episode_to_process.get('ID', row_to_update - 1)
            episode_name = episode_to_process.get('Name')
            
            # --- TẠO HASH VÀ THƯ MỤC ASSETS (Bước MỚI BẮT BUỘC) ---
            
            # Dùng các trường cốt lõi để tạo hash duy nhất
            hash_source = str(episode_to_process.get('Title', '')) + \
                          str(episode_to_process.get('Character', '')) + \
                          str(episode_to_process.get('Core Theme', ''))
            
            text_hash = generate_hash(hash_source)
            episode_to_process['text_hash'] = text_hash
            
            # Tạo thư mục assets
            folder_path = os.path.join('assets', text_hash)
            os.makedirs(folder_path, exist_ok=True)
            logging.info(f"Đã tạo hash: {text_hash} và folder assets tại: {folder_path}")
            
            # --- CẬP NHẬT TRẠNG THÁI VÀ HASH TRÊN SHEET ---
            
            # 2. Tìm chỉ mục cột Status và Hash an toàn
            status_col = get_column_index(worksheet, 'Status')
            hash_col = get_column_index(worksheet, 'Hash') # Giả định bạn có cột 'Hash'

            if status_col:
                # CẬP NHẬT TRẠNG THÁI: 'pending' -> 'PROCESSING'
                worksheet.update_cell(row_to_update, status_col, 'PROCESSING')
                logging.info(f"Đã cập nhật trạng thái của tập {episode_id} ('{episode_name}') thành 'PROCESSING' tại hàng {row_to_update}.")
            
            if hash_col:
                 # Cập nhật Hash vào cột Hash
                worksheet.update_cell(row_to_update, hash_col, text_hash)
                logging.info(f"Đã cập nhật Hash {text_hash} tại hàng {row_to_update}.")

            # Chuẩn bị dữ liệu trả về
            processed_data = {
                'ID': episode_id,
                'Name': episode_name,
                'Core Theme': episode_to_process.get('Core Theme', ''),
                'Content/Input': episode_to_process.get('Content/Input', ''),
                'ImageFolder': episode_to_process.get('ImageFolder', ''),
                'text_hash': text_hash,        # Hash đã tạo
                'Status_Row': row_to_update    # Lưu lại hàng cần cập nhật cho các bước sau
            }
            return processed_data
        else:
            logging.info("Không có tập nào có Status là 'pending'.")
            return None

    except Exception as e:
        logging.error(f"Lỗi trong quá trình lấy nội dung từ Sheet: {e}", exc_info=True)
        return None

def update_episode_status(row_index: int, status: str):
    """Cập nhật trạng thái của tập trên Google Sheet dựa trên chỉ mục hàng (row_index)."""
    gc = authenticate_google_sheet()
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not gc or not sheet_id: return

    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0)
        
        # Tìm chỉ mục cột Status
        status_col = get_column_index(worksheet, 'Status')
        
        if status_col and row_index > 1:
            worksheet.update_cell(row_index, status_col, status)
            logging.info(f"Đã cập nhật trạng thái hàng {row_index} thành '{status}'.")
        else:
            logging.warning(f"Không thể cập nhật trạng thái '{status}' tại hàng {row_index}. Kiểm tra chỉ mục cột Status.")

    except Exception as e:
        logging.error(f"LỖI CẬP NHẬT TRẠNG THÁI GOOGLE SHEET cho hàng {row_index}: {e}", exc_info=True)

if __name__ == '__main__':
    # Chỉ dùng để kiểm tra hàm khi chạy file trực tiếp
    # data = fetch_content()
    # if data:
    #     print(f"Dữ liệu đã xử lý: {data}")
    #     # Ví dụ: Sau khi xử lý hoàn tất, cập nhật trạng thái:
    #     # update_episode_status(data['Status_Row'], 'COMPLETED')
    pass
