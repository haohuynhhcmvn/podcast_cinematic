import os
import re
import subprocess
import openai
from utils import ensure_dir
from pathlib import Path

openai.api_key = os.environ.get("OPENAI_API_KEY")

EPISODES_DIR = "data/episodes"
AUDIO_OUT = "outputs/audio"
ensure_dir(AUDIO_OUT)

def split_into_segments(text, max_words=28):
    # Tách thành các đoạn ~max_words từ để giọng đọc mượt và có pause tự nhiên
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    segments = []
    cur = ""
    for s in sentences:
        if not s.strip():
            continue
        if len((cur + " " + s).split()) <= max_words:
            cur = (cur + " " + s).strip()
        else:
            if cur:
                segments.append(cur.strip())
            cur = s.strip()
    if cur:
        segments.append(cur.strip())
    return segments

def tts_from_script(hash_text: str):
    md_path = os.path.join(EPISODES_DIR, f"{hash_text}.md")
    if not os.path.exists(md_path):
        raise FileNotFoundError(md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    segments = split_into_segments(text, max_words=28)
    out_files = []
    for i, seg in enumerate(segments):
        # Optionally remove SFX/Music tags for pure narration
        seg_clean = re.sub(r"\[SFX:.*?\]|\[Music:.*?\]|\[.*?Giọng.*?\]","", seg)
        print(f"TTS segment {i+1}/{len(segments)} (words={len(seg_clean.split())})")
        resp = openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=seg_clean
        )
        out_path = os.path.join(AUDIO_OUT, f"{hash_text}_{i}.mp3")
        with open(out_path, "wb") as f:
            f.write(resp.read())
        out_files.append(out_path)
    # concat into single mp3 via ffmpeg
    list_file = os.path.join(AUDIO_OUT, f"{hash_text}_parts.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in out_files:
            f.write(f"file '{Path(p).as_posix()}'\n")
    final_audio = os.path.join(AUDIO_OUT, f"{hash_text}.mp3")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i", list_file, "-c","copy", final_audio], check=True)
    print("Final TTS saved:", final_audio)
    return final_audio

if __name__ == "__main__":
    # quick local test if you have an episode file in data/episodes
    for f in os.listdir(EPISODES_DIR):
        if f.endswith(".md"):
            key = os.path.splitext(f)[0]
            tts_from_script(key)
