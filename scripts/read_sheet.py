import gspread
from oauth2client.service_account import ServiceAccountCredentials
from utils import generate_hash
import os

# Cấu hình Google Sheet
CREDS_FILE = 'service_account.json'
SHEET_NAME = 'podcast_requests'

scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

rows = sheet.get_all_records()

for idx, row in enumerate(rows, start=2):
    if row.get('status') == 'pending':
        text_hash = generate_hash(row['title'] + row['character'] + row['core_theme'])
        sheet.update_cell(idx, 7, text_hash)  # giả sử cột G lưu hash
        folder_path = os.path.join('assets', text_hash)
        os.makedirs(folder_path, exist_ok=True)
# Placeholder for read_sheet.py
