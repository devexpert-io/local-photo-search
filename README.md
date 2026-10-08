# Local Photo Search

Busca en tus fotos con lenguaje natural («un perro en la playa», «algo para cenar») sin subir nada a la nube. Usa [EmbeddingGemma 2](https://huggingface.co/google/embeddinggemma-2), el modelo de embeddings multimodal y abierto de Google, que se ejecuta en tu máquina, y guarda los vectores en SQLite con [sqlite-vec](https://github.com/asg017/sqlite-vec).

```
Indexar:  carpeta de fotos ─▶ EmbeddingGemma 2 ─▶ vector (768 números) ─▶ SQLite + sqlite-vec
Buscar:   «un perro»       ─▶ EmbeddingGemma 2 ─▶ vector ─▶ vecinos más cercanos ─▶ fotos
```

Texto e imágenes caen en el mismo espacio vectorial, así que una frase y una foto que hablan de lo mismo quedan cerca.

El paso a paso está explicado en [este vídeo](https://www.youtube.com/watch?v=wjzfEm88j44).

## Requisitos

- [uv](https://docs.astral.sh/uv/)
- Unos 2 GB libres para el modelo, que se descarga la primera vez
- Mac con Apple Silicon, GPU NVIDIA o, más despacio, solo CPU

## Empezar

```bash
uv sync
uv run scripts/download_sample_photos.py   # 400 fotos de Unsplash para probar
uv run photosearch index sample-photos      # o la carpeta con tus fotos
uv run photosearch serve                    # http://127.0.0.1:8000
```

En la web puedes buscar mientras escribes, abrir una foto y pedir «más como esta», o arrastrar una imagen desde el escritorio para encontrar las parecidas. El indexado solo procesa las fotos nuevas, así que puedes relanzarlo cuando añadas más.

## El código, paso a paso

Cada paso tiene su tag (`git checkout paso-1`) y se puede ejecutar por separado.

| Paso | Archivo | Qué hace |
|---|---|---|
| 1 | [`embedder.py`](src/photosearch/embedder.py) | Carga el modelo y convierte fotos y textos en vectores. Pruébalo con `uv run photosearch try "un perro" sample-photos/unsplash-237.jpg sample-photos/unsplash-10.jpg` |
| 2 | [`db.py`](src/photosearch/db.py) | Tabla `photos`, tabla vectorial `photo_vectors` y la búsqueda de vecinos en SQL. Pruébalo con `uv run python -m photosearch.db` |
| 3 | [`indexer.py`](src/photosearch/indexer.py) | Recorre una carpeta, calcula los vectores por lotes y guarda miniaturas |
| 4 | [`app.py`](src/photosearch/app.py) y [`static/`](src/photosearch/static) | La API con FastAPI y la web |

## Ajustes que importan

En [`embedder.py`](src/photosearch/embedder.py):

- **`VISION_TOKENS`**: 70 en este proyecto; el modelo usa 280 por defecto. Con menos tokens por imagen indexa más rápido, y para fotos 70 da resultados casi iguales.
- **`DIMS`**: 768. Gracias a Matryoshka puedes recortar a 512, 256 o 128 dimensiones y ocupar menos. Si lo cambias, vuelve a indexar: consultas y fotos deben tener el mismo tamaño.
- **Precisión:** bfloat16 en GPU y float32 en CPU. Google desaconseja float16 con este modelo.

Detalles que es fácil pasar por alto:

- La consulta de texto lleva el prefijo `task: search result | query: `, que pone `prompt_name="SearchQuery"`. Las imágenes van sin prefijo.
- Para procesar imágenes hace falta `torchvision` además de `sentence-transformers`.
- No se pueden mezclar vectores de modelos distintos. Si cambias de modelo, toca reindexar.

## Rendimiento medido

En un MacBook Pro M5 Pro, con bfloat16 y 70 tokens por imagen:

| | |
|---|---|
| Indexar | unas 26 fotos/s con las fotos de ejemplo (1200×800), contando lectura y miniaturas |
| Buscar por texto | unos 25 ms |
| «Más como esta» | 1 ms: reutiliza el vector guardado y no toca el modelo |
| Memoria de GPU | unos 1,6 GB |

Con la configuración por defecto del modelo (float32 y 280 tokens) indexaba a 3,6 fotos/s.

## Limitaciones

- No sabe contar: «tres personas» puede devolver tres tenedores.
- Entiende mal las negaciones: con «playa sin gente» se cuela alguna playa con gente.
- Siempre devuelve resultados, aunque no haya nada parecido. La puntuación se mueve en una franja estrecha (de 0,60 a 0,75), así que importa más el orden y la distancia entre el primer resultado y el resto que el número en sí.

## Créditos

Las fotos de ejemplo son de [Unsplash](https://unsplash.com/license) y se descargan desde [Lorem Picsum](https://picsum.photos).

## Licencia

El código tiene licencia [MIT](LICENSE). Las fotos de ejemplo no forman parte del repositorio y mantienen la licencia de Unsplash.
