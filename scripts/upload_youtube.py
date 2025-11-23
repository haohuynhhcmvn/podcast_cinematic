# Placeholder fofrom googleapiclient.discovery import build
import os

api_key = os.environ.get('YOUTUBE_API_KEY')
youtube = build('youtube','v3',developerKey=api_key)

hash_text = "example_episode"
video_file = f"outputs/videos/{hash_text}_16_9_final.mp4"

request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": f"Podcast {hash_text}",
            "description": "Podcast cinematic tự động",
            "tags": ["podcast","storytelling"]
        },
        "status": {"privacyStatus": "public"}
    },
    media_body=video_file
)
response = request.execute()
print(response)
r upload_youtube.py
