"""Paso 1 · La conexión con el modelo.

EmbeddingGemma 2 se ejecuta en tu máquina. La primera vez se descarga de Hugging Face
(unos 1,5 GB) y a partir de ahí funciona sin conexión.
"""

import numpy as np
import torch
from PIL import Image
from sentence_transformers import SentenceTransformer

MODEL_ID = "google/embeddinggemma-2"

# Matryoshka: el vector se puede recortar a 512, 256 o 128 dimensiones.
# Ocupa menos, pero texto e imágenes tienen que usar siempre el mismo tamaño.
DIMS = 768

# Tokens por imagen: 70, 140, 280 (el valor por defecto), 560 o 1120.
# Con 70 indexa unas 8 veces más rápido y, para fotos, los resultados son casi iguales.
VISION_TOKENS = 70


def pick_device() -> tuple[str, torch.dtype]:
    """GPU si la hay. bfloat16 donde está soportado; float16 nunca (el modelo no lo tolera)."""
    if torch.cuda.is_available():
        return "cuda", torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float32
    if torch.backends.mps.is_available():  # Mac con Apple Silicon
        return "mps", torch.bfloat16
    return "cpu", torch.float32


class Embedder:
    def __init__(self) -> None:
        device, dtype = pick_device()
        self.model = SentenceTransformer(
            MODEL_ID,
            device=device,
            # Solo texto e imagen: sin el encoder de audio son 440M parámetros en vez de 740M
            config_kwargs={"audio_config": None},
            model_kwargs={"dtype": dtype},
            processor_kwargs={"max_soft_tokens": VISION_TOKENS},
        )

    def embed_images(self, images: list[Image.Image]) -> np.ndarray:
        """Una fila de DIMS números por imagen. Las imágenes van sin prefijo."""
        return self.model.encode(
            images,
            batch_size=16,
            truncate_dim=DIMS,
            normalize_embeddings=True,  # vuelve a normalizar después de recortar
        )

    def embed_query(self, text: str) -> np.ndarray:
        """El texto de búsqueda lleva el prefijo 'task: search result | query: '."""
        return self.model.encode(
            text,
            prompt_name="SearchQuery",
            truncate_dim=DIMS,
            normalize_embeddings=True,
        )
