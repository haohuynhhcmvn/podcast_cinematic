import re
import os
import subprocess
from datetime import timedelta

def get_audio_duration(audio_path):
    """
    Dùng ffprobe để lấy thời lượng audio chính xác đến millisecond
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        print("❌ Lỗi lấy duration audio:", e)
        return 0.0


def split_sentences(text):
    """Tách câu tiếng Việt theo dấu câu."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s]


def format_timestamp(seconds):
    """Convert giây → định dạng SRT"""
    td = timedelta(seconds=seconds)
    srt_time = str(td)
    if "." not in srt_time:
        srt_time += ".000"

    h, m, s = srt_time.split(":")
    sec, ms = s.split(".")
    return f"{int(h):02}:{int(m):02}:{int(sec):02},{int(ms[:3]):03}"


def generate_srt(text, audio_duration, words_per_second=2.5):
    """
    Tạo phụ đề dựa trên tốc độ nói của giọng nam trầm.
    """
    sentences = split_sentences(text)
    srt_lines = []
    current_time = 0.0

    total_words = sum(len(s.split()) for s in sentences)
    estimated_duration = total_words / words_per_second

    scale = audio_duration / estimated_duration

    index = 1

    for sentence in sentences:
        word_count = len(sentence.split())
        sentence_duration = (word_count / words_per_second) * scale

        start = current_time
        end = start + sentence_duration

        srt_lines.append(
            f"{index}\n"
            f"{format_timestamp(start)} --> {format_timestamp(end)}\n"
            f"{sentence}\n"
        )

        current_time = end + 0.25
        index += 1

    return "\n".join(srt_lines)


def save_subtitle(text, audio_path, output_path):
    """
    Tạo file .srt chuẩn, tự đo thời lượng audio.
    """
    audio_duration = get_audio_duration(audio_path)
    print(f"🎧 Duration audio: {audio_duration:.2f}s")

    srt_text = generate_srt(text, audio_duration)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_text)

    print(f"✅ Đã tạo phụ đề: {output_path}")
    return output_path


if __name__ == "__main__":

    # Demo test
    text = "Đây là ví dụ để kiểm tra tạo phụ đề. Giọng đọc nam trầm kể chuyện."
    audio_path = "../outputs/audio/sample.wav"
    output = save_subtitle(text, audio_path, "../outputs/subtitle/sample.srt")
    print("Done:", output)
# Placeholder for create_subtitle.py
