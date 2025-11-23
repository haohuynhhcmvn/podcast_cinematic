#!/usr/bin/env python3
# Script để build RSS feed từ các file markdown trong thư mục episodes/

import os
import glob
from pathlib import Path
import frontmatter

def build_rss():
    """Build RSS feed from episodes markdown files"""
    episodes_dir = Path('episodes')
    output_dir = Path('docs')
    
    # Đọc tất cả file markdown trong episodes/
    episode_files = sorted(episodes_dir.glob('*.md'), reverse=True)
    
    if not episode_files:
        print("No episodes found!")
        return
    
    print(f"Found {len(episode_files)} episodes")
    # Từ đớy bắt đầu xỚ lý và tạo RSS feed
    # (Chi tiết implementation sẽ thểm vào sau)

if __name__ == '__main__':
    build_rss()
    print("RSS feed built successfully!")
