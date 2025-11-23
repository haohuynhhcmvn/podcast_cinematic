
---

### `scripts/utils.py`
```python
import hashlib
import os
import re
import io
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

def generate_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def sanitize_filename(name: str) -> str:
    # safe filename
    name = re.sub(r'[^0-9A-Za-zÀ-ỹ\-\_\. ]+', '', name)
    return name.strip().replace(' ', '_')[:200]
