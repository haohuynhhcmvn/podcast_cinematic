import os
import numpy as np
from moviepy.editor import (
    ImageSequenceClip, AudioFileClip, VideoFileClip, ImageClip,
    CompositeVideoClip, concatenate_videoclips
)
from moviepy.video.fx.all import resize, crop
from utils import ensure_dir
from pathlib import Path

INPUT_IMAGES_ROOT = "inputs/images"
AUDIO_OUT = "outputs/audio"
VIDEO_OUT = "outputs/video"
INTRO = "intro_outro/intro.mp4"
OUTRO = "intro_outro/outro.mp4"
LOGO = "logos/logo.png"
MIC_ICON = "logos/micro.png"  # put micro icon here
ensure_dir(VIDEO_OUT)

def make_waveform_clip(audio_path, width=800, height=200, fps=20, duration=None):
    """Create a simple animated waveform clip using moviepy's AudioFileClip.to_soundarray"""
    audio = AudioFileClip(audio_path)
    dur = audio.duration if duration is None else duration
    # Generate frames with amplitude bars
    def make_frame(t):
        arr = audio.subclip(max(0, t-0.05), min(audio.duration, t+0.05)).to_soundarray(fps=44100)
        if arr.size == 0:
            mag = 0.0
        else:
            mag = float(np.abs(arr).mean())
        # create simple image
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        bar_h = int(np.clip(mag * height * 5, 2, height))
        color = (255, 160, 60)
        canvas[height-bar_h:height, width//2-5:width//2+5] = color
        return canvas
    from moviepy.video.VideoClip import VideoClip
    clip = VideoClip(make_frame, duration=dur)
    clip = clip.set_fps(fps)
    return clip

def create_video_from(hash_text:str):
    images_dir = os.path.join(INPUT_IMAGES_ROOT, hash_text)
    audio_file = os.path.join(AUDIO_OUT, f"{hash_text}.mp3")
    md_file = os.path.join("data/episodes", f"{hash_text}.md")
    if not os.path.exists(images_dir):
        raise FileNotFoundError("Images folder not found: " + images_dir)
    imgs = sorted([str(p) for p in Path(images_dir).iterdir() if p.suffix.lower() in [".jpg",".jpeg",".png",".webp"]])
    if not imgs:
        raise FileNotFoundError("No images found in " + images_dir)
    audio = AudioFileClip(audio_file)
    # each image duration chosen so total matches audio length
    per_img = max(4, audio.duration / max(1, len(imgs)))
    slide = ImageSequenceClip(imgs, durations=[per_img]*len(imgs)).set_audio(audio).set_duration(audio.duration)
    # add intro/outro
    clips = []
    if os.path.exists(INTRO):
        clips.append(VideoFileClip(INTRO))
    clips.append(slide)
    if os.path.exists(OUTRO):
        clips.append(VideoFileClip(OUTRO))
    final = concatenate_videoclips(clips, method="compose")
    # overlay logo
    if os.path.exists(LOGO):
        logo = ImageClip(LOGO).resize(width=140).set_pos(("right","top")).set_duration(final.duration)
        final = CompositeVideoClip([final, logo])
    # overlay waveform center-bottom
    wf = make_waveform_clip(audio_file, width=600, height=160, fps=20, duration=final.duration)
    wf = wf.set_position(("center","center"))
    # overlay micro icon above waveform
    if os.path.exists(MIC_ICON):
        mic = ImageClip(MIC_ICON).resize(width=100).set_pos(("center","bottom")).set_duration(final.duration)
        final = CompositeVideoClip([final, wf, mic])
    else:
        final = CompositeVideoClip([final, wf])
    out_path = os.path.join(VIDEO_OUT, f"{hash_text}_16_9.mp4")
    final.write_videofile(out_path, fps=24, codec="libx264", audio_codec="aac", threads=4)
    print("Video written to", out_path)
    # create short: center crop to 9:16
    short_out = os.path.join("outputs/shorts", f"{hash_text}_9_16.mp4")
    ensure_dir(os.path.dirname(short_out))
    wide = final.resize(height=1920)  # ensure tall
    w = wide.w
    # crop center to width matching 9:16
    crop_w = int(w * 9/16) if (w * 9/16) < wide.w else wide.w
    cropped = wide.crop(x_center=wide.w/2, width=crop_w, height=wide.h)
    cropped.write_videofile(short_out, fps=24, codec="libx264", audio_codec="aac", threads=4)
    print("Short written to", short_out)
    return out_path, short_out

if __name__ == "__main__":
    # quick test: iterate outputs/audio files
    for f in os.listdir("outputs/audio"):
        if f.endswith(".mp3"):
            key = os.path.splitext(f)[0]
            create_video_from(key)
