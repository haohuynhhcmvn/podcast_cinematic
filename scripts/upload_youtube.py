import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
VIDEO_FOLDER = "outputs/video"

def upload_video_simple(video_path, title, description, tags=["podcast","storytelling"]):
    youtube = build("youtube","v3", developerKey=YOUTUBE_API_KEY)
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    body = {
        "snippet": {"title": title, "description": description, "tags": tags, "categoryId": "22"},
        "status": {"privacyStatus": "public"}
    }
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    res = req.execute()
    print("Uploaded:", res.get("id"))
    return res

if __name__ == "__main__":
    # demo: upload last video
    vids = sorted([os.path.join(VIDEO_FOLDER,f) for f in os.listdir(VIDEO_FOLDER) if f.endswith(".mp4")])
    if vids:
        upload_video_simple(vids[-1], "Demo Podcast", "Auto upload demo")
