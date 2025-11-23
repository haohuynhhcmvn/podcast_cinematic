import os
import json
import gspread
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def authenticate_google_sheet():
    load_dotenv()
    service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not service_account_file or not os.path.exists(service_account_file):
        logging.error(f"File Service Account JSON không tồn tại tại: {service_account_file}")
        return None
    try:
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
            logging.info(f"Tìm thấy tập mới: ID={episode_id}, Title={episode_name}")
            
            # CẬP NHẬT TRẠNG THÁI: Tìm 'pending' và cập nhật thành 'PROCESSING'
            # Giả định cột Status là cột F (cột 6)
            cell = worksheet.find('pending', in_column=6) 
            if cell:
                worksheet.update_cell(cell.row, cell.col, 'PROCESSING')
                logging.info(f"Đã cập nhật trạng thái của tập {episode_id} thành 'PROCESSING'.")

            # CHUẨN HÓA DỮ LIỆU TRẢ VỀ (KHỚP VỚI CẤU TRÚC SHEET)
            processed_data = {
                'ID': episode_id,
                'Name': episode_name,
                'Core Theme': episode_to_process.get('Core Theme', ''),
                'Content/Input': episode_to_process.get('Content/Input', ''),
                'ImageFolder': episode_to_process.get('ImageFolder', ''),
                'Status_Row': cell.row if cell else None
            }
            return processed_data
        else:
            logging.info("Không có tập nào có Status là 'pending'.")
            return None

    except Exception as e:
        logging.error(f"Lỗi trong quá trình lấy nội dung từ Sheet: {e}")
        return None

# (Không cần if __name__ main, được gọi bởi glue_pipeline)
