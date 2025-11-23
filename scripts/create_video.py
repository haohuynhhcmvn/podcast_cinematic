import os
from moviepy.editor import *

hash_text = "example_episode"
image_folder = f"assets/{hash_text}"
audio_file = f"audio/{hash_text}_cinematic.mp3"
intro_file = "intro_outro/intro.mp4"
outro_file = "intro_outro/outro.mp4"
logo_file = "logos/logo.png"
micro_icon = "assets/micro.png"

output_16_9 = f"outputs/videos/{hash_text}_16_9_final.mp4"
output_9_16 = f"outputs/videos/{hash_text}_9_16_final.mp4"

img_files = sorted([os.path.join(image_folder, f) for f in os.listdir(image_folder) if f.endswith(('.jpg','.png'))])
slide_clip = ImageSequenceClip(img_files, durations=[5]*len(img_files))
audio = AudioFileClip(audio_file)
slide_clip = slide_clip.set_audio(audio).set_duration(audio.duration)

# Overlay logo
if os.path.exists(logo_file):
    logo = ImageClip(logo_file).resize(width=120).set_pos(("right","top")).set_duration(slide_clip.duration)
    slide_clip = CompositeVideoClip([slide_clip, logo])

# Overlay micro icon
if os.path.exists(micro_icon):
    mic = ImageClip(micro_icon).resize(width=80).set_pos(("center","bottom")).set_duration(slide_clip.duration)
    slide_clip = CompositeVideoClip([slide_clip, mic])

slide_clip.write_videofile(output_16_9, fps=30, codec="libx264", audio_codec="aac")

# Shorts 9:16
short_clip = slide_clip.resize(height=1080).crop(x_center=slide_clip.w/2, width=608)
short_clip.write_videofile(output_9_16, fps=30, codec="libx264", audio_codec="aac")
