"""RAG index build/load/search service with vector support."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import DEFAULT_DOC_PATHS, DEFAULT_INDEX_PATH, DEFAULT_EMBEDDING_MODEL, EMBEDDING_PROVIDER, SILICONFLOW_EMBEDDING_MODEL
from .ingest import build_chunks
from .retriever import retrieve

_index_cache: dict | None = None
_index_cache_path: str | None = None


def build_index(
    doc_paths: list[str | Path] | None = None,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    with_embeddings: bool = True,
    model_name: str | None = None,
    embedding_provider: str = "",
) -> dict:
    global _index_cache, _index_cache_path
    source_paths = [Path(path) for path in (doc_paths or DEFAULT_DOC_PATHS)]
    provider = embedding_provider or EMBEDDING_PROVIDER
    if model_name:
        embedding_model = model_name
    elif provider == "siliconflow":
        embedding_model = SILICONFLOW_EMBEDDING_MODEL
    else:
        embedding_model = DEFAULT_EMBEDDING_MODEL
    chunks, warnings = build_chunks(
        source_paths,
        with_embeddings=with_embeddings,
        model_name=embedding_model,
        embedding_provider=provider,
    )
    index_payload = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "doc_paths": [str(path) for path in source_paths],
        "num_chunks": len(chunks),
        "chunks": chunks,
        "warnings": warnings,
        "embedding_model": embedding_model if with_embeddings else None,
        "embedding_provider": provider if with_embeddings else None,
        "has_embeddings": with_embeddings,
    }
    target = Path(index_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _index_cache = index_payload
    _index_cache_path = str(target.resolve())
    return index_payload


def load_index(index_path: str | Path = DEFAULT_INDEX_PATH) -> dict:
    global _index_cache, _index_cache_path
    path = Path(index_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"知识索引不存在: {path}")
    if _index_cache is not None and _index_cache_path == str(path):
        return _index_cache
    data = json.loads(path.read_text(encoding="utf-8"))
    _index_cache = data
    _index_cache_path = str(path)
    return data


def invalidate_cache() -> None:
    global _index_cache, _index_cache_path
    _index_cache = None
    _index_cache_path = None


def search_index(
    query: str,
    top_k: int = 5,
    source_type: str = "",
    index_path: str | Path = DEFAULT_INDEX_PATH,
    retrieval_mode: str = "hybrid",
) -> dict:
    index_data = load_index(index_path=index_path)

    if retrieval_mode in ("vector", "hybrid") and not index_data.get("has_embeddings", False):
        retrieval_mode = "keyword"

    results = retrieve(
        index_data,
        query=query,
        top_k=top_k,
        source_type=source_type,
        retrieval_mode=retrieval_mode,
    )

    return {
        "query": query,
        "top_k": top_k,
        "source_type": source_type or None,
        "index_path": str(index_path),
        "num_chunks": index_data.get("num_chunks", 0),
        "retrieval_mode": retrieval_mode,
        "has_embeddings": index_data.get("has_embeddings", False),
        "embedding_provider": index_data.get("embedding_provider"),
        "results": results,
        "warnings": index_data.get("warnings", []),
    }
