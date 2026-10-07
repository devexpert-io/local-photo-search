"""Descarga fotos de ejemplo de Unsplash (vía picsum.photos) para probar sin usar las tuyas.

    uv run scripts/download_sample_photos.py        # 400 fotos en sample-photos/
    uv run scripts/download_sample_photos.py 100    # solo 100
"""

import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path("sample-photos")
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 400


def photo_ids(count: int) -> list[str]:
    ids: list[str] = []
    page = 1
    while len(ids) < count:
        with urllib.request.urlopen(f"https://picsum.photos/v2/list?page={page}&limit=100") as response:
            items = json.load(response)
        if not items:
            break
        ids += [item["id"] for item in items]
        page += 1
    return ids[:count]


def download(photo_id: str) -> None:
    dest = OUT / f"unsplash-{photo_id}.jpg"
    if not dest.exists():
        urllib.request.urlretrieve(f"https://picsum.photos/id/{photo_id}/1200/800.jpg", dest)


OUT.mkdir(exist_ok=True)
with ThreadPoolExecutor(max_workers=12) as pool:
    list(pool.map(download, photo_ids(COUNT)))
print(f"{len(list(OUT.glob('*.jpg')))} fotos en {OUT}/")
