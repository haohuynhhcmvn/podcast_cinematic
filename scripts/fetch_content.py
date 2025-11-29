# /scripts/fetch_content.py
import os
import json
import gspread
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def authenticate_google_sheet():
    load_dotenv()
    # Đường dẫn file JSON được đọc từ .env (tên file: service-account.json)
    service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON') 
    
    # Kiểm tra file đã được giải mã/tạo chưa
    if not service_account_file or not os.path.exists(service_account_file):
        logging.error(f"File Service Account JSON không tồn tại tại: {service_account_file}")
        return None
        
    try:
        # gspread sẽ sử dụng file này để xác thực
        gc = gspread.service_account(filename=service_account_file)
        return gc
    except Exception as e:
        logging.error(f"Lỗi xác thực Google Sheet: {e}")
        return None

def fetch_content():
    load_dotenv()
    gc = authenticate_google_sheet()
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not gc or not sheet_id: return None

    try:
        sh = gc.open_by_key(sheet_id)
        worksheet = sh.get_worksheet(0) # Lấy sheet đầu tiên
        list_of_dicts = worksheet.get_all_records()
        
        # Lọc tập cần xử lý: Status 'pending'
        episode_to_process = next((row for row in list_of_dicts if row.get('Status', '').lower() == 'pending'), None)
        
        if episode_to_process:
            episode_id = episode_to_process.get('ID')
            episode_name = episode_to_process.get('Name')
            
            # Lấy số hàng để cập nhật trạng thái sau này
            cell = worksheet.find('pending', in_column=6) # Giả định cột Status là cột F (cột 6)
            
            # CẬP NHẬT TRẠNG THÁI: 'pending' -> 'PROCESSING'
            if cell:
                row_to_update = cell.row
                worksheet.update_cell(row_to_update, cell.col, 'PROCESSING')
                logging.info(f"Đã cập nhật trạng thái của tập {episode_id} thành 'PROCESSING'.")
            else:
                row_to_update = None

            processed_data = {
                'ID': episode_id,
                'Name': episode_name,
                'Core Theme': episode_to_process.get('Core Theme', ''),
                'Content/Input': episode_to_process.get('Content/Input', ''),
                'ImageFolder': episode_to_process.get('ImageFolder', ''),
                'Status_Row': row_to_update # Lưu lại hàng cần cập nhật
            }
            return processed_data
        else:
            logging.info("Không có tập nào có Status là 'pending'.")
            return None

    except Exception as e:
        logging.error(f"Lỗi trong quá trình lấy nội dung từ Sheet: {e}")
        return None
