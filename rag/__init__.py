"""Lightweight RAG helpers for local knowledge retrieval."""

from .config import DEFAULT_DOC_PATHS, DEFAULT_INDEX_PATH
from .service import build_index, load_index, search_index

__all__ = [
    "DEFAULT_DOC_PATHS",
    "DEFAULT_INDEX_PATH",
    "build_index",
    "load_index",
    "search_index",
]
