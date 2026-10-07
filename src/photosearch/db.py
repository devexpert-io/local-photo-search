"""Paso 2 · La base de datos: SQLite + sqlite-vec.

Una tabla normal con los datos de cada foto y una tabla virtual (vec0) con su vector.
Todo vive en un único archivo, sin servidor.
"""

import sqlite3
from pathlib import Path

import numpy as np
import sqlite_vec

from .embedder import DIMS

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS photos (
    id        INTEGER PRIMARY KEY,
    path      TEXT NOT NULL UNIQUE,
    taken_at  TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS photo_vectors USING vec0(
    photo_id  INTEGER PRIMARY KEY,
    embedding FLOAT[{DIMS}] distance_metric=cosine
);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.enable_load_extension(True)
    sqlite_vec.load(db)  # añade a SQLite los tipos y funciones de vectores
    db.enable_load_extension(False)
    db.executescript(SCHEMA)
    return db


def add_photo(db: sqlite3.Connection, path: str, taken_at: str | None, vector: np.ndarray) -> int:
    cursor = db.execute("INSERT INTO photos (path, taken_at) VALUES (?, ?)", (path, taken_at))
    db.execute(
        "INSERT INTO photo_vectors (photo_id, embedding) VALUES (?, ?)",
        (cursor.lastrowid, vector.astype(np.float32)),
    )
    return cursor.lastrowid


def search(db: sqlite3.Connection, vector: np.ndarray, k: int = 30, exclude: int | None = None) -> list[dict]:
    """Las k fotos más cercanas al vector. Distancia coseno: 0 es idéntico."""
    rows = db.execute(
        """
        WITH nearest AS (
            SELECT photo_id, distance
            FROM photo_vectors
            WHERE embedding MATCH ? AND k = ?
        )
        SELECT photos.id, photos.path, photos.taken_at, nearest.distance
        FROM nearest
        JOIN photos ON photos.id = nearest.photo_id
        ORDER BY nearest.distance
        """,
        (vector.astype(np.float32), k + 1),
    ).fetchall()
    results = [
        {"id": r["id"], "path": r["path"], "taken_at": r["taken_at"], "score": round(1 - r["distance"], 4)}
        for r in rows
        if r["id"] != exclude
    ]
    return results[:k]


def get_vector(db: sqlite3.Connection, photo_id: int) -> np.ndarray | None:
    row = db.execute("SELECT embedding FROM photo_vectors WHERE photo_id = ?", (photo_id,)).fetchone()
    return np.frombuffer(row["embedding"], dtype=np.float32) if row else None


def get_photo(db: sqlite3.Connection, photo_id: int) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM photos WHERE id = ?", (photo_id,)).fetchone()


def indexed_paths(db: sqlite3.Connection) -> set[str]:
    return {row["path"] for row in db.execute("SELECT path FROM photos")}


def latest(db: sqlite3.Connection, limit: int = 60) -> list[dict]:
    rows = db.execute(
        "SELECT id, path, taken_at FROM photos ORDER BY taken_at IS NULL, taken_at DESC, id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    # Prueba sin modelo: tres vectores al azar en una base de datos en memoria
    db = connect(":memory:")
    print("sqlite-vec", db.execute("SELECT vec_version()").fetchone()[0])

    rng = np.random.default_rng(0)
    vectors = rng.normal(size=(3, DIMS))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    for i, vector in enumerate(vectors):
        add_photo(db, f"foto-{i}.jpg", None, vector)

    query = vectors[1] + 0.01 * rng.normal(size=DIMS)  # casi igual que la foto 1
    for result in search(db, query / np.linalg.norm(query), k=3):
        print(f"  {result['score']:.3f}  {result['path']}")
