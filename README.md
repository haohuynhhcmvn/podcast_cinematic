# Podcast Nhân Vật Huyền Thoại

Dự án audio podcast kể chuyện về những nhân vật có ảnh hưởng lịch sử, văn hóa Việt Nam. Tập trung vào chất lượng biên tập, âm thanh và hệ thống website—phù hợp phát hành đa nền tảng.

## Cấu Trúc Dự Án

```
podcast-nhan-vat-huyen-thoai/
├── .github/
│   └── workflows/
│       └── publish.yml              # CI: build RSS + deploy to gh-pages
├── episodes/
│   └── 2025-11-23-thanh-giong.md  # mỗi episode là 1 file markdown
├── audio/
│   ├── raw/                         # file ghi thô
│   └── final/                       # MP3/OGG đã master
├── assets/
│   ├── cover.jpg
│   └── episode-templates/
│       ├── show-notes-template.md
│       └── script-template.md
├── scripts/
│   ├── build_rss.py                 # chuyển episodes/*.md -> feed RSS
│   └── convert_metadata.py          # (tùy chọn) helper
├── docs/                             # dùng cho GitHub Pages
├── .gitignore
├── README.md
└── LICENSE
```

## Hướng Dẫn Sử Dụng

### Tạo Episode Mới

1. Tạo file markdown trong thư mục `episodes/` với tên `YYYY-MM-DD-ten-episode.md`
2. Sử dụng template từ `assets/episode-templates/show-notes-template.md`
3. Commit và push lên GitHub

### Chuẩn Bị Kịch Bản

- Tham khảo `assets/episode-templates/script-template.md`
- Chuẩn bị nội dung trước khi ghi âm

### Xử Lý Audio

- File thô lưu trong `audio/raw/`
- File master (MP3/OGG) lưu trong `audio/final/`

### Build RSS Feed

```bash
python scripts/build_rss.py
```

### Triển Khai lên GitHub Pages

- Push lên branch `main`
- GitHub Actions sẽ tự động build RSS và deploy lên `gh-pages`

## Liên Hệ

Email: contact@vietlegends.vn
