# scripts/get_episode_data.py: Module đóng vai trò là cầu nối dữ liệu, KHÔNG SỬA read_sheet.py
import os
import logging
import importlib.util

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_next_episode_data():
    """
    1. Gọi read_sheet.py để thực thi logic tạo hash/thư mục.
    2. Đọc lại Sheet để tìm hàng vừa được đánh dấu/tạo hash.
    3. Cập nhật trạng thái sang 'PROCESSING' và trả về dữ liệu.
    """
    
    # 1. GỌI LOGIC TỪ read_sheet.py (Để đảm bảo hash và folder được tạo)
    logging.info("Đang thực thi logic từ read_sheet.py gốc (tạo hash và folder)...")
    try:
        # Tải và chạy module read_sheet.py
        spec = importlib.util.spec_from_file_location("read_sheet_module", "scripts/read_sheet.py")
        read_sheet_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(read_sheet_module)
        
        # Lấy các biến global từ read_sheet.py
        SHEET = read_sheet_module.sheet
        
        logging.info("Logic tạo hash/folder của read_sheet.py đã hoàn tất.")

    except Exception as e:
        logging.error(f"LỖI KHÔNG THỂ TẢI HOẶC CHẠY read_sheet.py: {e}", exc_info=True)
        return None

    # 2. TÌM HÀNG VỪA ĐƯỢC XỬ LÝ (Tức là hàng có hash mới nhất)
    # Giả định: Cột G (index 7) lưu hash, Cột F (index 6) lưu status.
    HASH_COL_INDEX = 7 
    STATUS_COL_INDEX = 6 
    
    # Đọc lại dữ liệu (vì sheet đã được cập nhật sau khi chạy read_sheet.py)
    rows_updated = SHEET.get_all_records()
    
    for i, row in enumerate(rows_updated):
        row_index_in_sheet = i + 2 # Hàng thực tế trong sheet
        
        # Kiểm tra: Hàng phải có hash (tức là đã được read_sheet.py xử lý) 
        # VÀ Status không phải là 'processed' hoặc 'completed'
        
        # GSpread sử dụng __EMPTY_N cho các cột không có tiêu đề trong hàng đầu tiên. 
        # Giả định cột hash là cột G (index 7), nên khóa có thể là '__EMPTY_6' (index 7 - 1 = 6) hoặc 'text_hash'
        
        # Ta sẽ dùng row.get(key)
        row_hash = row.get(f'__EMPTY_{HASH_COL_INDEX - 1}', '').strip()
        if not row_hash:
             # Thử với khóa 'text_hash' nếu có thể
             row_hash = row.get('text_hash', '').strip()

        row_status = row.get('status', '').strip().lower() # Sử dụng 'status' theo read_sheet.py

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

    logging.info("Không tìm thấy tập nào đã được tạo hash mà chưa xử lý.")
    return None

def update_sheet_status(episode_id: int, status: str):
    """Cập nhật trạng thái cuối cùng (processed/failed) trên Google Sheet."""
    try:
        # Lại phải gọi lại các biến global
        spec = importlib.util.spec_from_file_location("read_sheet_module", "scripts/read_sheet.py")
        read_sheet_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(read_sheet_module)
        SHEET = read_sheet_module.sheet
        
        # Giả định cột status là cột F (index 6)
        SHEET.update_cell(episode_id, 6, status.lower())
        logging.info(f"Đã cập nhật trạng thái cho Episode ID {episode_id} thành '{status.lower()}'.")
    except Exception as e:
        logging.error(f"Lỗi khi cập nhật trạng thái cuối cùng cho Episode ID {episode_id}: {e}")
