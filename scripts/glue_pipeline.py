import os
import gspread # Dòng này đã được dùng đúng
import subprocess
import json
from time import sleep

# CONFIG
SERVICE_ACCOUNT_FILE = "service_account.json"
# Kiểm tra lại SHEET_ID của bạn: 1qSbdDEEP6pGvWGBiYdCFroSfjtWbNskwCmEe0vjkQdI
SHEET_ID = "1qSbdDEEP6pGvWGBiYdCFroSfjtWbNskwCmEe0vjkQdI" 

# Cấu hình ánh xạ tên cột (Dựa trên ảnh sheet, các cột Name/CoreTheme/ContentInput/ImageFolder/Status nằm ở A/C/D/E/F)
# Lưu ý: Python dùng index 0, Gspread dùng index 1.
# Cột A = 1, Cột F = 6, Cột G = 7
COLUMN_MAP = {
    "title_key": "Name",
    "character_key": "Name",
    "core_theme_key": "CoreTheme",
    "content_key": "ContentInput",
    "status_key": "Status",
    "hash_column_index": 7,        # Cột G
    "status_column_index": 6       # Cột F
}

def run_script(script_path, args=None):
    """Chạy script Python con thông qua subprocess."""
    cmd = ["python", script_path]
    if args:
        # Thêm các tham số vào lệnh (ví dụ: hash, content)
        cmd.extend(args) 
    print(f"\n--- Running: {' '.join(cmd)} ---")
    try:
        # Sử dụng shell=False là mặc định và an toàn hơn
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        # In ra stdout của script con để debug
        if result.stdout:
            print(f"[STDOUT]\n{result.stdout.strip()}")
        print(f"Script hoàn tất. Mã thoát: {result.returncode}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"!!! ERROR running {script_path} !!!")
        print(f"[STDERR]:\n{e.stderr}")
        raise e

def main_pipeline():
    try:
        # !!! ĐÃ SỬA LỖI MODULE NOT FOUND Ở ĐÂY: Dùng gspread.service_account() thay vì import từ gspread.service_account !!!
        # Khởi tạo kết nối Google Sheet bằng gspread.service_account()
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        sh = gc.open_by_key(SHEET_ID)
        sheet = sh.sheet1
        print("Kết nối Google Sheet thành công.")
    except Exception as e:
        print(f"LỖI KHỞI TẠO: Không thể kết nối Sheet. Lỗi: {e}")
        return

    # --- BƯỚC 1: FETCH CONTENT ---
    print("\n=== BƯỚC 1: FETCH CONTENT (Tải ảnh và Tạo Hash) ===")
    try:
        run_script("scripts/fetch_content.py")
        
        # Reload dữ liệu để lấy Hash mới nhất (bao gồm cột 'Hash' đã được cập nhật)
        sh = gc.open_by_key(SHEET_ID)
        sheet = sh.sheet1
        rows = sheet.get_all_records()
    except Exception as e:
        print(f"Dừng Pipeline: Lỗi Fetch Content.\n{e}")
        return

    # --- BƯỚC 2: XỬ LÝ TỪNG TẬP PENDING ---
    print("\n=== BƯỚC 2: PROCESS PENDING EPISODES ===")
    
    for idx, r in enumerate(rows, start=2):
        row_title = r.get(COLUMN_MAP["title_key"], f"episode_{idx}")
        status = str(r.get(COLUMN_MAP["status_key"], "")).strip().lower()
        # Lấy Hash từ dữ liệu vừa reload, gspread get_all_records() sẽ dùng header row làm key
        episode_hash = str(r.get("Hash", "")).strip() 

        if status != "pending" or not episode_hash:
            continue

        print(f"\n>>> Processing: {row_title} (Hash: {episode_hash})")
        
        try:
            content_input = r.get(COLUMN_MAP["content_key"], "")
            if not content_input:
                print(f"Bỏ qua {row_title}: Cột {COLUMN_MAP['content_key']} trống.")
                continue

            # 1. Generate Script
            run_script("scripts/generate_script.py", [episode_hash, content_input])
            
            # 2. TTS
            run_script("scripts/create_tts.py", [episode_hash])

            # 3. Music/SFX
            run_script("scripts/auto_music_sfx.py", [episode_hash])

            # 4. Subtitle
            run_script("scripts/create_subtitle.py", [episode_hash])
            
            # 5. Video
            run_script("scripts/create_video.py", [episode_hash])

            # 6. Upload (Tùy chọn)
            # run_script("scripts/upload_youtube.py", [episode_hash]) 

            # Cập nhật status thành công
            sheet.update_cell(idx, COLUMN_MAP["status_column_index"], "done")
            print(f"✔ DONE: {row_title}")

        except Exception as e:
            print(f"!!! FAILED: {row_title}. Lỗi chi tiết: {e}")
            try:
                # Cập nhật trạng thái lỗi
                sheet.update_cell(idx, COLUMN_MAP["status_column_index"], "error")
            except Exception as update_err:
                print(f"Lỗi khi cập nhật trạng thái ERROR: {update_err}")

if __name__ == "__main__":
    main_pipeline()import os
import gspread
from gspread.service_account import ServiceAccountCredentials
import subprocess
import json
from time import sleep

# Khai báo cấu hình (Cần đồng bộ với fetch_content.py)
SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_ID = "1qSbdDEEP6pGvWGBiYdCFroSfjtWbNskwCmEe0vjkQdI"

# Cấu hình ánh xạ tên cột (Đảm bảo khớp với fetch_content.py)
COLUMN_MAP = {
    "title_key": "Name",
    "character_key": "Name",
    "core_theme_key": "CoreTheme",
    "content_key": "ContentInput", # Thêm cột ContentInput để lấy prompt cho AI
    "status_key": "Status",
    "hash_column_index": 7,        # Cột G
    "status_column_index": 6       # Cột F
}

# Scope cần cho Sheets (Đọc/Ghi)
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets" 
]

def run_script(script_path, args=None):
    """Chạy script Python con và kiểm tra lỗi."""
    cmd = ["python", script_path]
    if args:
        cmd.extend(args)
    print(f"\n--- Bắt đầu chạy: {' '.join(cmd)} ---")
    try:
        # Sử dụng subprocess.run để bắt đầu một tiến trình mới
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Lệnh hoàn tất. Mã thoát: {result.returncode}")
        # print("Output:")
        # print(result.stdout)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"!!! LỖI khi chạy {script_path} !!!")
        print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{e.stderr}")
        raise e
    except FileNotFoundError:
        print(f"LỖI: File {script_path} không tồn tại.")
        raise

def main_pipeline():
    try:
        # 1. Khởi tạo kết nối Google Sheet
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        sh = gc.open_by_key(SHEET_ID)
        sheet = sh.sheet1
        rows = sheet.get_all_records()

    except Exception as e:
        print("LỖI KHỞI TẠO: Không thể kết nối với Google Sheet. Kiểm tra service_account.json và SHEET_ID.")
        raise e

    # 2. Bước FETCH content (luôn chạy để đảm bảo có hash và ảnh mới)
    print("=== BƯỚC 1: FETCH CONTENT VÀ CẬP NHẬT HASH ===")
    try:
        # Chạy script fetch_content.py để tải ảnh và cập nhật hash/status
        run_script("scripts/fetch_content.py")
        
        # Cập nhật lại dữ liệu sau khi fetch để lấy Hash mới nhất
        rows = sheet.get_all_records()
    except Exception as e:
        print("Pipeline dừng: Lỗi ở bước Fetch Content.")
        return

    # 3. Lặp qua các hàng có Hash đã tạo (Sau khi fetch)
    print("\n=== BƯỚC 2: XỬ LÝ CÁC EPISODE CÓ HASH ===")
    
    # Hàng 1 trong Python (idx=0) tương ứng với Hàng 2 trong Sheet.
    for idx, r in enumerate(rows, start=2):
        
        row_title = r.get(COLUMN_MAP["title_key"], f"episode_{idx}")
        current_status = str(r.get(COLUMN_MAP["status_key"], "")).strip().lower()
        episode_hash = str(r.get("Hash", "")).strip() # Giả định cột tiêu đề là 'Hash'

        if not episode_hash:
            # Hash chưa được tạo hoặc chưa chạy fetch_content thành công
            continue

        if current_status == "done" or current_status == "error":
            # Bỏ qua các hàng đã hoàn thành hoặc lỗi
            continue
            
        if current_status != "pending":
            # Chỉ xử lý các hàng đang ở trạng thái "pending"
            continue


        print(f"\n--- Bắt đầu xử lý Episode: {row_title} (Hash: {episode_hash}) ---")
        
        try:
            # --- CÁC BƯỚC XỬ LÝ (Điều phối) ---
            
            # Lấy prompt từ cột ContentInput để truyền vào generate_script
            content_input = r.get(COLUMN_MAP["content_key"], "")
            if not content_input:
                print(f"Bỏ qua {row_title}: Cột ContentInput trống.")
                continue

            # BƯỚC 3: Generate Script
            # Script này nhận hash và prompt từ content_input
            run_script("scripts/generate_script.py", [episode_hash, content_input])
            
            # BƯỚC 4: Create TTS Audio
            run_script("scripts/create_tts.py", [episode_hash])

            # BƯỚC 5: Auto Music SFX (Trộn nhạc nền và hiệu ứng)
            run_script("scripts/auto_music_sfx.py", [episode_hash])

            # BƯỚC 6: Create Subtitle (.srt)
            run_script("scripts/create_subtitle.py", [episode_hash])
            
            # BƯỚC 7: Create Video (Tạo cả 16:9 và 9:16)
            run_script("scripts/create_video.py", [episode_hash])

            # BƯỚC 8: Upload YouTube
            # Tùy chọn: nếu bạn muốn upload shorts/full video
            # run_script("scripts/upload_youtube.py", [episode_hash]) 
            
            # --- KẾT THÚC XỬ LÝ ---
            
            # Cập nhật trạng thái 'done' (thành công)
            sheet.update_cell(idx, COLUMN_MAP["status_column_index"], "done")
            print(f"Hoàn thành episode: {row_title}")

        except Exception as e:
            # Cập nhật trạng thái 'error' nếu bất kỳ bước nào thất bại
            sheet.update_cell(idx, COLUMN_MAP["status_column_index"], "error")
            print(f"!!! Xử lý Episode {row_title} thất bại. Đã đặt status là 'error'.")
            continue

if __name__ == "__main__":
    main_pipeline()
