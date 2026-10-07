"""Línea de comandos: `photosearch try | index`."""

import argparse
import time
from pathlib import Path


def cmd_try(args: argparse.Namespace) -> None:
    """Compara un texto con unas cuantas fotos, sin base de datos de por medio."""
    from PIL import Image

    from .embedder import Embedder

    start = time.perf_counter()
    embedder = Embedder()
    print(f"Modelo cargado en {time.perf_counter() - start:.1f} s\n")

    query = embedder.embed_query(args.text)
    preview = ", ".join(f"{x:.3f}" for x in query[:5])
    print(f"«{args.text}» → {len(query)} números: [{preview}, …]\n")

    images = [Image.open(path).convert("RGB") for path in args.photos]
    vectors = embedder.embed_images(images)

    # Los vectores están normalizados: el producto escalar es la similitud coseno
    scores = vectors @ query
    for score, path in sorted(zip(scores, args.photos), reverse=True):
        print(f"  {score:.3f}  {path}")


def cmd_index(args: argparse.Namespace) -> None:
    from .indexer import index_folder

    index_folder(Path(args.folder), Path(args.data))


def main() -> None:
    parser = argparse.ArgumentParser(prog="photosearch")
    parser.add_argument("--data", default="data", help="carpeta del índice y las miniaturas")
    commands = parser.add_subparsers(dest="command", required=True)

    try_cmd = commands.add_parser("try", help="compara un texto con unas fotos")
    try_cmd.add_argument("text")
    try_cmd.add_argument("photos", nargs="+")
    try_cmd.set_defaults(func=cmd_try)

    index_cmd = commands.add_parser("index", help="indexa una carpeta de fotos")
    index_cmd.add_argument("folder")
    index_cmd.set_defaults(func=cmd_index)

    args = parser.parse_args()
    args.func(args)
