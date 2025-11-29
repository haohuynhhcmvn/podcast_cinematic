# scripts/glue_pipeline.py
# Đây là file điều phối (glue) các bước trong pipeline tự động hóa podcast.

import os
import logging
from fetch_content import fetch_pending_episodes, update_episode_status
from upload_youtube import upload_youtube_video
# Cần import các hàm từ các script tạo nội dung. Chúng ta sẽ giả lập chúng ở đây.
# from generate_script import generate_script_and_audio
# from create_video import create_podcast_video
# from create_shorts import create_shorts_video

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def mock_generate_and_create(data: dict) -> tuple[str | None, dict | None]:
    """
    Hàm mô phỏng việc tạo kịch bản, audio, và video.
    Trong môi trường thực, các bước này sẽ được thay thế bằng các hàm gọi API
    và xử lý MoviePy thực tế.
    """
    logging.info("BƯỚC 2 & 3: Bắt đầu tạo nội dung (Mô phỏng)...")
    
    # Định nghĩa các đường dẫn giả định cho các bước tiếp theo
    video_output_path = os.path.join('outputs', 'video', f"{data['ID']}_full_podcast_169.mp4")
    metadata = {
        'title': f"Podcast: {data.get('Name')} | {data.get('Core Theme')}",
        'description': f"Tập podcast mới nhất về chủ đề: {data.get('Core Theme')}. Hash: {data['text_hash']}",
        'tags': ['podcast', 'podcastviet', data.get('Core Theme')]
    }
    
    # Tạo file video giả để mô phỏng thành công
    try:
        os.makedirs(os.path.dirname(video_output_path), exist_ok=True)
        with open(video_output_path, 'w') as f:
            f.write("Mô phỏng nội dung video đã tạo.")
        logging.info(f"Đã tạo file video mô phỏng tại: {video_output_path}")
    except Exception as e:
        logging.error(f"Lỗi tạo file mô phỏng: {e}")
        return None, None
        
    logging.info("Tạo nội dung mô phỏng thành công.")
    return video_output_path, metadata

def run_pipeline():
    """Chạy toàn bộ quy trình tự động hóa."""
    try:
        # BƯỚC 1: LẤY BẢN GHI PENDING
        logging.info("BẮT ĐẦU: Lấy bản ghi 'pending' từ Google Sheet...")
        episode_data = fetch_pending_episodes() # Import chính xác hàm đã tồn tại
        
        if not episode_data:
            logging.info("KẾT THÚC: Không có tập nào cần xử lý.")
            return

        row_index = episode_data['Status_Row']
        
        # BƯỚC 2 & 3: TẠO VIDEO (Thay thế bằng các hàm thực tế)
        video_path, metadata = mock_generate_and_create(episode_data)
        
        if not video_path:
            logging.error("LỖI PIPELINE: Không tạo được video.")
            update_episode_status(row_index, 'FAILED_VIDEO_CREATE')
            return

        # BƯỚC 4: UPLOAD YOUTUBE
        logging.info("BƯỚC 4: Bắt đầu Upload YouTube...")
        upload_success = upload_youtube_video(video_path, metadata)
        
        # BƯỚC 5: CẬP NHẬT TRẠNG THÁI CUỐI CÙNG
        if upload_success:
            update_episode_status(row_index, 'COMPLETED')
        else:
            update_episode_status(row_index, 'FAILED_UPLOAD')
            
        logging.info("KẾT THÚC: Quy trình xử lý tập phim đã hoàn tất.")

    except Exception as e:
        logging.error(f"LỖI KHÔNG XÁC ĐỊNH TRONG PIPELINE: {e}", exc_info=True)

if __name__ == '__main__':
    run_pipeline()
