import openai
import os

openai.api_key = os.environ.get("OPENAI_API_KEY")

# Ví dụ dùng hash từ read_sheet.py
hash_text = "example_episode"

# Giả lập dữ liệu
content = "Steve Jobs – Nỗi ám ảnh hoàn hảo"
core_theme = "Nỗi đau tạo ra thiên tài"

script = openai.chat.completions.create(
    model="gpt-5",
    messages=[
        {"role": "system", "content": "Bạn là Master Storyteller & Audio Documentary Director."},
        {"role": "user", "content": f"Viết script cinematic 20 phút cho: {content}, chủ đề: {core_theme}, giọng kể lôi cuốn, markdown, có SFX, nhạc, hướng dẫn giọng đọc."}
    ]
)

os.makedirs('scripts_output', exist_ok=True)
with open(f'scripts_output/{hash_text}.md', 'w', encoding='utf-8') as f:
    f.write(script.choices[0].message.content)
# Placeholder for generate_script.py
