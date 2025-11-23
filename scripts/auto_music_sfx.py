from pydub import AudioSegment
import os

hash_text = "example_episode"
audio_file = f"audio/{hash_text}_cinematic.mp3"
output_file = f"audio/{hash_text}_cinematic_final.mp3"

base = AudioSegment.from_file(audio_file)

# Ghép nhạc nền
try:
    bgm = AudioSegment.from_file('audio_assets/bgm/epic_theme.mp3') - 6
    base = base.overlay(bgm)
except:
    pass

# Ghép SFX ví dụ
try:
    sfx = AudioSegment.from_file('audio_assets/sfx/thunder.wav')
    base = base.overlay(sfx)
except:
    pass

base.export(output_file, format='mp3')
# Placeholder for auto_music_sfx.py
