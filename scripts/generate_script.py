import os
import openai
from utils import ensure_dir, generate_hash, sanitize_filename

openai.api_key = os.environ.get("OPENAI_API_KEY")

EPISODES_DIR = "data/episodes"
ensure_dir(EPISODES_DIR)

# For simplicity, process a single pending item from Google Sheet cached file or manual run
# glue_pipeline will pass parameters; here we provide a helper function.

TEMPLATE_SYSTEM = """Bạn là Master Storyteller & Audio Documentary Director.
Viết kịch bản podcast cinematic (dài khoảng 20-25 phút) theo cấu trúc:
Event -> Context/Psychology -> Philosophical Insight.
Tránh liệt kê sự kiện theo Wikipedia; tập trung vào CHỦ ĐỀ CỐT LÕI.
FORMAT: Strict Markdown. Bao gồm SFX/Music cues [SFX: xxx.wav], [Music: epic.mp3] và voice directions [Giọng trầm], [Nhạc nổi lên] cho mỗi đoạn.
Ngôn ngữ: Tiếng Việt, cảm xúc mạnh mẽ, gợi hình."""

def generate_script_for(episode_title: str, character: str, core_theme: str, hash_text: str):
    prompt = f"TÊN: {episode_title}\nNHÂN VẬT: {character}\nCHỦ ĐỀ: {core_theme}\n\nHãy viết kịch bản theo yêu cầu ở trên."
    print("Requesting OpenAI to generate script...")
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role":"system", "content": TEMPLATE_SYSTEM},
            {"role":"user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=4500
    )
    text = resp["choices"][0]["message"]["content"]
    ensure_dir(EPISODES_DIR)
    path = os.path.join(EPISODES_DIR, f"{hash_text}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Script saved to", path)
    return path

# Example local test:
if __name__ == "__main__":
    h = generate_hash("Steve Jobs|Steve Jobs|Sáng tạo")
    generate_script_for("Steve Jobs – Nỗi ám ảnh hoàn hảo", "Steve Jobs", "Sáng tạo vượt giới hạn", h)
