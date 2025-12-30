# === scripts/upload_youtube.py ===
import os
import pickle
import logging
import time
import random
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Giới hạn của YouTube
MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 4900

# Các scope cần thiết
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    """Xác thực với YouTube API bằng token.pickle"""
    creds = None
    
    # 1. Tìm file token
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
            
    # 2. Nếu không có hoặc hết hạn -> Refresh hoặc báo lỗi
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("🔄 Đang làm mới Token YouTube...")
            try:
                creds.refresh(Request())
                # Lưu lại token mới nếu môi trường cho phép ghi (Local)
                # Trên GitHub Actions thì không lưu lại được vĩnh viễn, nhưng dùng cho session này ok
                with open("token.pickle", "wb") as f:
                    pickle.dump(creds, f)
            except Exception as e:
                logger.error(f"❌ Lỗi refresh token: {e}")
                return None
        else:
            logger.error("❌ Không tìm thấy token hợp lệ. Hãy chạy script lấy token ở local trước.")
            return None

    return build("youtube", "v3", credentials=creds)

def upload_video(video_path, episode_data, thumbnail_path=None, publish_at=None):
    """
    Hàm chính để upload video.
    Tham số:
      - video_path: Đường dẫn file mp4
      - episode_data: Dict chứa Title, Summary, Tags
      - thumbnail_path: Đường dẫn ảnh thumb
      - publish_at: Thời gian datetime (nếu muốn hẹn giờ)
    """
    if not os.path.exists(video_path):
        logger.error(f"❌ Không tìm thấy file video: {video_path}")
        return "FAILED"

    youtube = get_authenticated_service()
    if not youtube:
        return "FAILED"

    try:
        # 1. Chuẩn bị Metadata
        title = episode_data.get("Title", "New Video")
        description = episode_data.get("Summary", "")
        tags = episode_data.get("Tags", [])
        
        # Cắt ngắn nếu quá dài
        if len(title) > MAX_TITLE_LENGTH:
            title = title[:MAX_TITLE_LENGTH-3] + "..."
            
        # 2. Cấu hình trạng thái (Công khai / Riêng tư / Hẹn giờ)
        # Mặc định là 'private' để an toàn, trừ khi có hẹn giờ
        privacy_status = "private" 
        
        status_body = {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }

        # Xử lý Hẹn giờ (Scheduled Upload)
        if publish_at:
            # YouTube yêu cầu status phải là 'private' khi đặt publishAt
            status_body["privacyStatus"] = "private" 
            # Chuyển đổi sang format ISO 8601 UTC (YYYY-MM-DDThh:mm:ssZ)
            # publish_at truyền vào nên là datetime object
            utc_time = publish_at.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            status_body["publishAt"] = utc_time
            logger.info(f"📅 Đã đặt lịch công chiếu: {utc_time}")

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22" # 22 = People & Blogs, 24 = Entertainment, 27 = Education
            },
            "status": status_body
        }

        # 3. Upload Video
        logger.info(f"🚀 Bắt đầu upload: {title}")
        
        # Chunk size -1 để thư viện tự động chọn, resumable=True để upload file lớn ổn định
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        # Vòng lặp upload để hiện tiến trình
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                # Chỉ log mỗi 20% để đỡ spam log
                if progress % 20 == 0:
                    logger.info(f"   Upload... {progress}%")

        video_id = response.get("id")
        logger.info(f"✅ UPLOAD THÀNH CÔNG! Video ID: {video_id}")

        # 4. Upload Thumbnail (Nếu có)
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                logger.info(f"🖼️ Đang upload thumbnail...")
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumbnail_path)
                ).execute()
                logger.info("✅ Thumbnail đã cập nhật.")
            except Exception as e:
                logger.warning(f"⚠️ Lỗi upload thumbnail (Video vẫn OK): {e}")

        return video_id

    except HttpError as e:
        # Xử lý lỗi Quota hoặc lỗi mạng
        if e.resp.status == 403 and "quotaExceeded" in str(e):
            logger.critical("❌ FATAL: Hết hạn ngạch (Quota) YouTube hôm nay!")
        else:
            logger.error(f"❌ YouTube API Error: {e}")
        return "FAILED"
        
    except Exception as e:
        logger.error(f"❌ Lỗi Upload không xác định: {e}", exc_info=True)
        return "FAILED"
