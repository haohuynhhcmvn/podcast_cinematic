# scripts/upload_youtube.py
import os
import pickle
import logging
from datetime import datetime, timezone
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MAX_TITLE_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 5000


def get_authenticated_service():
    logging.info("🔐 YouTube Auth: loading token.pickle")
    creds = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("🔄 Refreshing YouTube token")
            creds.refresh(Request())
        else:
            logging.error("❌ YouTube authentication failed")
            return None

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str,
    episode_data: dict,
    thumbnail_path: str | None = None,
    publish_at: datetime | None = None
):
    logging.info("======================================")
    logging.info("📤 START YOUTUBE UPLOAD")
    logging.info(f"📁 Video: {video_path}")

    if not os.path.exists(video_path):
        logging.error("❌ Video file not found")
        return "FAILED"

    youtube = get_authenticated_service()
    if not youtube:
        return "FAILED"

    title = episode_data.get("Title", "New Video")
    description = episode_data.get("Summary", "")
    tags = episode_data.get("Tags", [])

    if len(title) > MAX_TITLE_LENGTH:
        title = title[:MAX_TITLE_LENGTH - 3] + "..."
    if len(description) > MAX_DESCRIPTION_LENGTH:
        description = description[:MAX_DESCRIPTION_LENGTH]

    status = {
        "privacyStatus": "private",
        "selfDeclaredMadeForKids": False
    }

    if publish_at:
        utc_time = publish_at.astimezone(timezone.utc).isoformat()
        status["publishAt"] = utc_time
        logging.info(f"📅 Scheduled publish at (UTC): {utc_time}")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22"
        },
        "status": status
    }

    logging.info(f"🚀 Uploading video: {title}")
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status_progress, response = request.next_chunk()
        if status_progress:
            logging.info(f"   Upload progress: {int(status_progress.progress() * 100)}%")

    video_id = response.get("id")
    logging.info(f"✅ VIDEO UPLOADED: {video_id}")

    if thumbnail_path and os.path.exists(thumbnail_path):
        logging.info(f"🖼️ Uploading thumbnail: {thumbnail_path}")
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()
        logging.info("✅ Thumbnail uploaded")

    logging.info("📤 END YOUTUBE UPLOAD")
    logging.info("======================================")

    return {"video_id": video_id}
