# Placeholderimport openai
import re
import os
from pydub import AudioSegment
import subprocess

openai.api_key = os.environ.get("OPENAI_API_KEY")

hash_text = "example_episode"
os.makedirs("audio", exist_ok=True)

with open(f"scripts_output/{hash_text}.md", "r", encoding="utf-8") as f:
    script_text = f.read()

segments = re.split(r'\n\n', script_text)
audio_files = []

for i, seg in enumerate(segments):
    response = openai.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=seg
    )
    out_file = f"audio/{hash_text}_{i}.mp3"
    with open(out_file, "wb") as f:
        f.write(response.read())
    audio_files.append(out_file)

concat_file = f"audio/{hash_text}_segments.txt"
with open(concat_file, "w") as f:
    for af in audio_files:
        f.write(f"file '{af}'\n")

final_output = f"audio/{hash_text}_cinematic.mp3"
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat_file,"-c","copy",final_output])
 for create_tts.py
