"""Paso 4 · La API y la web: buscar por texto, por foto y «más como esta»."""

import io
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import db as store
from .embedder import Embedder
from .indexer import load_photo

DATA_DIR = Path(os.environ.get("PHOTOSEARCH_DATA", "data"))
STATIC_DIR = Path(__file__).parent / "static"
(DATA_DIR / "thumbs").mkdir(parents=True, exist_ok=True)

state: dict = {}
model_lock = threading.Lock()  # un único modelo compartido por todas las peticiones


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["db"] = store.connect(DATA_DIR / "photos.db")
    state["embedder"] = Embedder()  # se carga una vez, al arrancar
    yield


app = FastAPI(lifespan=lifespan)


def respond(results: list[dict], start: float) -> dict:
    for result in results:
        result["thumb"] = f"/thumbs/{result['id']}.jpg"
    return {"results": results, "ms": round((time.perf_counter() - start) * 1000)}


@app.get("/api/search")
def search(q: str, k: int = 30) -> dict:
    start = time.perf_counter()
    with model_lock:
        vector = state["embedder"].embed_query(q)
    return respond(store.search(state["db"], vector, k), start)


@app.get("/api/similar/{photo_id}")
def similar(photo_id: int, k: int = 30) -> dict:
    start = time.perf_counter()
    vector = store.get_vector(state["db"], photo_id)  # ya está guardado: no hace falta el modelo
    if vector is None:
        raise HTTPException(404, "Foto no encontrada")
    return respond(store.search(state["db"], vector, k, exclude=photo_id), start)


@app.post("/api/search-by-image")
def search_by_image(file: UploadFile, k: int = 30) -> dict:
    start = time.perf_counter()
    image, _ = load_photo(io.BytesIO(file.file.read()))
    with model_lock:
        vector = state["embedder"].embed_images([image])[0]
    return respond(store.search(state["db"], vector, k), start)


@app.get("/api/photos")
def latest(limit: int = 60) -> dict:
    return respond(store.latest(state["db"], limit), time.perf_counter())


@app.get("/api/photos/{photo_id}/original")
def original(photo_id: int) -> Response:
    photo = store.get_photo(state["db"], photo_id)
    if photo is None:
        raise HTTPException(404, "Foto no encontrada")
    path = Path(photo["path"])
    if path.suffix.lower() != ".heic":
        return FileResponse(path)
    image, _ = load_photo(path)  # los navegadores no muestran HEIC: la servimos como JPEG
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90)
    return Response(buffer.getvalue(), media_type="image/jpeg")


app.mount("/thumbs", StaticFiles(directory=DATA_DIR / "thumbs"), name="thumbs")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
