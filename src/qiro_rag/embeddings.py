"""Persisted local embedding backends.

Default backend is a deterministic hashed vector so tests and offline enterprise
installs work. `sentence-transformers` is optional for real local semantic
embeddings.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable

from qiro_rag.index import EvidenceIndex
from qiro_rag.schemas import EmbeddingBackend, SearchHit
from qiro_rag.utils import tokens

DEFAULT_HASH_MODEL = "hash-256-v1"
DEFAULT_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def build_embedding_index(
    index: EvidenceIndex,
    backend: EmbeddingBackend = "hash",
    model: str | None = None,
    dimensions: int = 256,
) -> int:
    """Embed every indexed chunk and persist vectors in SQLite."""

    chunks = index.all_chunks()
    if not chunks:
        return 0

    model_name = model or (DEFAULT_HASH_MODEL if backend == "hash" else DEFAULT_ST_MODEL)
    vectors = embed_texts([chunk.text for chunk in chunks], backend, model_name, dimensions)
    index.upsert_embeddings(
        backend=backend,
        model=model_name,
        dimensions=len(vectors[0]) if vectors else dimensions,
        vectors={chunk.chunk_id: vector for chunk, vector in zip(chunks, vectors, strict=True)},
    )
    return len(vectors)


def search_persisted_embeddings(
    index: EvidenceIndex,
    query: str,
    backend: str | None = None,
    model: str | None = None,
    limit: int = 8,
    filters: dict[str, str] | None = None,
) -> list[SearchHit]:
    selected = (backend, model) if backend and model else index.default_embedding_backend()
    if not selected:
        return []
    backend_name, model_name = selected
    rows = index.embedding_rows(backend_name, model_name, filters=filters)
    if not rows:
        return []
    query_vector = embed_texts(
        [query],
        backend_name,  # type: ignore[arg-type]
        model_name,
        dimensions=len(rows[0][1]),
    )[0]

    hits: list[SearchHit] = []
    for hit, vector in rows:
        score = dense_cosine(query_vector, vector)
        if score > 0:
            hits.append(hit.model_copy(update={"score": score * 10.0}))
    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:limit]


def embed_texts(
    texts: list[str], backend: EmbeddingBackend, model: str, dimensions: int = 256
) -> list[list[float]]:
    if backend == "hash":
        return [hash_embedding(text, dimensions) for text in texts]
    if backend == "sentence-transformers":
        return sentence_transformer_embeddings(texts, model)
    raise ValueError(f"Unsupported embedding backend: {backend}")


def hash_embedding(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    for token in tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    return normalize(vector)


def sentence_transformer_embeddings(texts: list[str], model: str) -> list[list[float]]:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "sentence-transformers backend requested but not installed. "
            "Install with `uv sync --extra local-embeddings`."
        ) from exc

    encoder = SentenceTransformer(model)
    vectors = encoder.encode(texts, normalize_embeddings=True)
    return [list(map(float, vector)) for vector in vectors]


def dense_cosine(left: Iterable[float], right: Iterable[float]) -> float:
    left_list = list(left)
    right_list = list(right)
    numerator = sum(a * b for a, b in zip(left_list, right_list, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left_list))
    right_norm = math.sqrt(sum(value * value for value in right_list))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]
