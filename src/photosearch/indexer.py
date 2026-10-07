"""Paso 3 · Indexar: recorrer una carpeta, calcular el vector de cada foto y guardarlo."""

import time
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from . import db as store
from .embedder import Embedder

register_heif_opener()  # para abrir .heic (iPhone y algunas descargas de Google Fotos)

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
BATCH_SIZE = 16
THUMB_SIZE = 512
EXIF_IFD = 0x8769
DATE_TAKEN = 36867  # DateTimeOriginal


def find_photos(folder: Path) -> list[Path]:
    return sorted(path for path in folder.rglob("*") if path.suffix.lower() in EXTENSIONS)


def load_photo(source: Path | BinaryIO) -> tuple[Image.Image, str | None]:
    image = Image.open(source)
    image.draft("RGB", (1024, 1024))  # en JPEG decodifica ya reducida: mucho más rápido
    taken_at = image.getexif().get_ifd(EXIF_IFD).get(DATE_TAKEN)  # "2026:07:15 18:32:10"
    if taken_at:
        taken_at = taken_at.replace(":", "-", 2).replace(" ", "T")
    image = ImageOps.exif_transpose(image).convert("RGB")  # endereza las fotos del móvil
    return image, taken_at


def index_folder(folder: Path, data_dir: Path) -> None:
    thumbs = data_dir / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    db = store.connect(data_dir / "photos.db")

    already_indexed = store.indexed_paths(db)
    pending = [path for path in find_photos(folder) if str(path.resolve()) not in already_indexed]
    print(f"{len(pending)} fotos nuevas en {folder}")
    if not pending:
        return

    embedder = Embedder()
    start = time.perf_counter()
    for i in range(0, len(pending), BATCH_SIZE):
        photos = []
        for path in pending[i : i + BATCH_SIZE]:
            try:
                photos.append((path, *load_photo(path)))
            except Exception as error:  # archivo dañado o formato que Pillow no entiende
                print(f"\n  Me salto {path.name}: {error}")
        if not photos:
            continue

        vectors = embedder.embed_images([image for _, image, _ in photos])

        for (path, image, taken_at), vector in zip(photos, vectors):
            photo_id = store.add_photo(db, str(path.resolve()), taken_at, vector)
            image.thumbnail((THUMB_SIZE, THUMB_SIZE))
            image.save(thumbs / f"{photo_id}.jpg", quality=85)
        db.commit()

        done = min(i + BATCH_SIZE, len(pending))
        print(f"\r  {done}/{len(pending)} · {done / (time.perf_counter() - start):.1f} fotos/s", end="", flush=True)
    print()
