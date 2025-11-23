import os
from moviepy.editor import VideoFileClip
from utils import ensure_dir

SHORTS_OUT = "outputs/shorts"
ensure_dir(SHORTS_OUT)

def create_short_from_video(video_path, start_sec=0, duration=60, out_path=None):
    clip = VideoFileClip(video_path).subclip(start_sec, min(start_sec+duration, VideoFileClip(video_path).duration))
    if out_path is None:
        base = os.path.basename(video_path)
        out_path = os.path.join(SHORTS_OUT, f"short_{base}")
    clip.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac")
    print("Short created:", out_path)
    return out_path

if __name__ == "__main__":
    # find latest full video
    folder = "outputs/video"
    vids = sorted([os.path.join(folder,f) for f in os.listdir(folder) if f.endswith(".mp4")])
    if vids:
        create_short_from_video(vids[-1], start_sec=30, duration=60)
# Placeholder for create_shorts.py
