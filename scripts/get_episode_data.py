# scripts/get_episode_data.py
import os
import logging
import gspread
import importlib.util

# Tải read_sheet.py để sử dụng các biến global đã được kết nối
spec = importlib.util.spec_from_file_location("read_sheet_module", "scripts/read_sheet.py")
read_sheet_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(read_sheet_module)

# Các biến global từ read_sheet.py
SHEET = read_sheet_module.sheet
ROWS = read_sheet_module.rows

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_next_episode_data():
    """
    Tìm hàng đầu tiên có status là 'pending' (hoặc trống) và trả về dữ liệu đó.
    
    LƯU Ý: File này TỰ ĐỘNG gọi các biến global từ read_sheet.py.
    """
    logging.info("Bắt đầu tìm kiếm tập cần xử lý từ Google Sheet...")
    
    # Sử dụng ROWS đã được tải từ read_sheet.py
    for i, row in enumerate(ROWS):
        # i+2 là số hàng thực tế trong sheet (bỏ qua hàng tiêu đề)
        row_index_in_sheet = i + 2
        row_status = row.get('Status', '').strip().upper() # Sử dụng 'Status' theo Sheet

        # Kiểm tra điều kiện:
        if row_status == 'PENDING' or row_status == '':
            
            # --- TẠM THỜI ĐÁNH DẤU TRẠNG THÁI 'PROCESSING' ---
            # Cột Status là cột F (index 6, vì GSpread tính từ 1 và F là cột thứ 6)
            # Ta dùng tên cột để tìm index chính xác (đảm bảo an toàn)
            try:
                # Tìm index cột 'Status'
                status_col_index = SHEET.find('Status').col
                SHEET.update_cell(row_index_in_sheet, status_col_index, 'PROCESSING')
                logging.info(f"Đã đánh dấu hàng {row_index_in_sheet} ('{row.get('Name')}') là 'PROCESSING'.")
            except Exception as e:
                logging.warning(f"Không thể cập nhật trạng thái 'PROCESSING' trên Sheet: {e}")

            # --- TRẢ VỀ DỮ LIỆU ĐÃ TÌM THẤY ---
            # Sử dụng tên cột theo ảnh Sheet bạn cung cấp:
            episode_data = {
                'ID': row_index_in_sheet,
                'Name': row.get('Name', f"Episode {row_index_in_sheet}").strip(),
                'CoreTheme': row.get('CoreTheme', '').strip(),
                'ContentInput': row.get('ContentInput', '').strip(),
                'ImageFolder': row.get('ImageFolder', '').strip(),
                'Status': 'PROCESSING'
            }
            return episode_data

    logging.info("Hoàn thành: Không tìm thấy tập nào có status 'pending' hoặc trống.")
    return None

def update_sheet_status(episode_id: int, status: str):
    """Cập nhật trạng thái cuối cùng (COMPLETED/FAILED) trên Google Sheet."""
    try:
        status_col_index = SHEET.find('Status').col
        SHEET.update_cell(episode_id, status_col_index, status.upper())
        logging.info(f"Đã cập nhật trạng thái cho Episode ID {episode_id} thành '{status.upper()}'.")
    except Exception as e:
        logging.error(f"Lỗi khi cập nhật trạng thái cuối cùng cho Episode ID {episode_id}: {e}")
