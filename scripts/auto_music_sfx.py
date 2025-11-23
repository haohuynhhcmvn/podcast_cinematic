import os
from pydub import AudioSegment
from utils import ensure_dir

BGM_FOLDER = "audio_assets/bgm"
SFX_FOLDER = "audio_assets/sfx"
AUDIO_IN = "outputs/audio"
AUDIO_OUT = "outputs/audio_final"
ensure_dir(AUDIO_OUT)

def mix_music_for(hash_text:str, bgm_name=None, sfx_names=None):
    base_path = os.path.join(AUDIO_IN, f"{hash_text}.mp3")
    if not os.path.exists(base_path):
        raise FileNotFoundError(base_path)
    base = AudioSegment.from_file(base_path)
    if bgm_name:
        bgm_path = os.path.join(BGM_FOLDER, bgm_name)
        if os.path.exists(bgm_path):
            bgm = AudioSegment.from_file(bgm_path)
            # loop or cut to length
            bgm = bgm - 12  # lower bgm volume
            if len(bgm) < len(base):
                times = int(len(base)/len(bgm)) + 1
                bgm = bgm * times
            bgm = bgm[:len(base)]
            base = base.overlay(bgm)
    if sfx_names:
        for s in sfx_names:
            sfx_path = os.path.join(SFX_FOLDER, s)
            if os.path.exists(sfx_path):
                sfx = AudioSegment.from_file(sfx_path)
                # overlay at start (or can place by timestamps)
                base = base.overlay(sfx)
    outp = os.path.join(AUDIO_OUT, f"{hash_text}.mp3")
    base.export(outp, format="mp3")
    print("Audio final exported:", outp)
    return outp

if __name__ == "__main__":
    # example
    for f in os.listdir(AUDIO_IN):
        if f.endswith(".mp3"):
            key = os.path.splitext(f)[0]
            mix_music_for(key, bgm_name="epic_theme.mp3", sfx_names=["thunder.wav"])
