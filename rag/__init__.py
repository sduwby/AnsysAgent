"""Lightweight RAG helpers for local knowledge retrieval with vector search support."""

from .config import DEFAULT_DOC_PATHS, DEFAULT_INDEX_PATH, DEFAULT_EMBEDDING_MODEL
from .service import build_index, load_index, search_index, invalidate_cache

__all__ = [
    "DEFAULT_DOC_PATHS",
    "DEFAULT_INDEX_PATH",
    "DEFAULT_EMBEDDING_MODEL",
    "build_index",
    "load_index",
    "search_index",
    "invalidate_cache",
]
