# Local Photo Search

Busca en tus fotos con lenguaje natural, 100% en local, con [EmbeddingGemma 2](https://huggingface.co/google/embeddinggemma-2).

## Requisitos

- [uv](https://docs.astral.sh/uv/)
- Unos 2 GB libres para el modelo
- Mac con Apple Silicon, GPU NVIDIA o, más despacio, solo CPU

## Paso 1 · Conectar con el modelo

```bash
uv sync
uv run scripts/download_sample_photos.py
uv run photosearch try "un perro" sample-photos/unsplash-237.jpg sample-photos/unsplash-10.jpg
```
