"""Hybrid retrieval over the local evidence index."""

from __future__ import annotations

import math
from collections import Counter

from qiro_rag.index import EvidenceIndex
from qiro_rag.schemas import RetrievalMode, SearchHit
from qiro_rag.utils import tokens


def retrieve(
    index: EvidenceIndex,
    queries: list[str],
    mode: RetrievalMode = "hybrid",
    top_k: int = 8,
    filters: dict[str, str] | None = None,
) -> list[SearchHit]:
    """Retrieve candidate chunks with keyword + persisted/fallback semantic scoring."""

    merged: dict[str, SearchHit] = {}
    for query in queries:
        if mode in {"keyword", "hybrid"}:
            for hit in index.search_keyword(query, limit=max(top_k * 3, 12), filters=filters):
                _merge_hit(merged, hit)
        if mode in {"semantic", "hybrid"}:
            for hit in semantic_search(index, query, limit=max(top_k * 3, 12), filters=filters):
                _merge_hit(merged, hit)

    hits = list(merged.values())
    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:top_k]


def semantic_search(
    index: EvidenceIndex,
    query: str,
    limit: int = 8,
    filters: dict[str, str] | None = None,
) -> list[SearchHit]:
    """Use persisted embeddings when present, otherwise a dependency-free fallback."""

    from qiro_rag.embeddings import search_persisted_embeddings

    persisted = search_persisted_embeddings(index, query, limit=limit, filters=filters)
    if persisted:
        return persisted
    return lexical_semantic_search(index, query, limit=limit, filters=filters)


def lexical_semantic_search(
    index: EvidenceIndex,
    query: str,
    limit: int = 8,
    filters: dict[str, str] | None = None,
) -> list[SearchHit]:
    """Dependency-free local similarity search.

    This is a fallback for fresh packs before `qiro-rag embed` is run.
    """

    query_vector = Counter(tokens(query))
    if not query_vector:
        return []
    hits: list[SearchHit] = []
    for hit in index.all_chunks(filters):
        score = sparse_cosine(query_vector, Counter(tokens(hit.text)))
        if score > 0:
            hits.append(hit.model_copy(update={"score": score * 10.0}))
    hits.sort(key=lambda item: item.score, reverse=True)
    return hits[:limit]


def sparse_cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _merge_hit(merged: dict[str, SearchHit], hit: SearchHit) -> None:
    existing = merged.get(hit.chunk_id)
    if existing is None:
        merged[hit.chunk_id] = hit
    else:
        merged[hit.chunk_id] = existing.model_copy(update={"score": existing.score + hit.score})
