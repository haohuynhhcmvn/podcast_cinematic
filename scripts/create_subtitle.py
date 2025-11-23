import re
import os
import subprocess
from datetime import timedelta

def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1", audio_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0.0

def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s]

def format_timestamp(seconds: float):
    td = timedelta(seconds=seconds)
    total_seconds = td.total_seconds()
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    ms = int((total_seconds - int(total_seconds)) * 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def generate_srt_from_text(text, audio_duration, words_per_second=2.5):
    sentences = split_sentences(text)
    total_words = sum(len(s.split()) for s in sentences)
    estimated = total_words / words_per_second if words_per_second>0 else 1
    scale = (audio_duration / estimated) if estimated>0 else 1.0

    srt_blocks = []
    current_time = 0.0
    idx = 1
    for s in sentences:
        words = len(s.split())
        dur = (words / words_per_second) * scale
        start = current_time
        end = start + dur
        srt_blocks.append(f"{idx}\n{format_timestamp(start)} --> {format_timestamp(end)}\n{s}\n")
        current_time = end + 0.25
        idx += 1
    return "\n".join(srt_blocks)

def create_subtitle_for(hash_text:str, audio_path:str, episode_md_path:str, out_dir="outputs/subtitle"):
    os.makedirs(out_dir, exist_ok=True)
    with open(episode_md_path, "r", encoding="utf-8") as f:
        text = f.read()
    duration = get_audio_duration(audio_path)
    srt_text = generate_srt_from_text(text, duration)
    out_path = os.path.join(out_dir, f"{hash_text}.srt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(srt_text)
    print("Subtitle created at", out_path)
    return out_path

if __name__ == "__main__":
    # quick demo usage (adjust names)
    pass
