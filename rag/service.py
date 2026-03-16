"""RAG index build/load/search service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import DEFAULT_DOC_PATHS, DEFAULT_INDEX_PATH
from .ingest import build_chunks
from .retriever import retrieve

# 模块级内存缓存：避免每次检索都从磁盘读取 JSON
_index_cache: dict | None = None
_index_cache_path: str | None = None


def build_index(
    doc_paths: list[str | Path] | None = None,
    index_path: str | Path = DEFAULT_INDEX_PATH,
) -> dict:
    global _index_cache, _index_cache_path
    source_paths = [Path(path) for path in (doc_paths or DEFAULT_DOC_PATHS)]
    chunks, warnings = build_chunks(source_paths)
    index_payload = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "doc_paths": [str(path) for path in source_paths],
        "num_chunks": len(chunks),
        "chunks": chunks,
        "warnings": warnings,
    }
    target = Path(index_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # 同步更新内存缓存
    _index_cache = index_payload
    _index_cache_path = str(target.resolve())
    return index_payload


def load_index(index_path: str | Path = DEFAULT_INDEX_PATH) -> dict:
    global _index_cache, _index_cache_path
    path = Path(index_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"知识索引不存在: {path}")
    # 命中缓存时直接返回，避免重复磁盘 I/O
    if _index_cache is not None and _index_cache_path == str(path):
        return _index_cache
    data = json.loads(path.read_text(encoding="utf-8"))
    _index_cache = data
    _index_cache_path = str(path)
    return data


def invalidate_cache() -> None:
    """主动使内存缓存失效（重建 index 后调用）。"""
    global _index_cache, _index_cache_path
    _index_cache = None
    _index_cache_path = None


def search_index(
    query: str,
    top_k: int = 5,
    source_type: str = "",
    index_path: str | Path = DEFAULT_INDEX_PATH,
) -> dict:
    index_data = load_index(index_path=index_path)
    results = retrieve(index_data, query=query, top_k=top_k, source_type=source_type)
    return {
        "query": query,
        "top_k": top_k,
        "source_type": source_type or None,
        "index_path": str(index_path),
        "num_chunks": index_data.get("num_chunks", 0),
        "results": results,
        "warnings": index_data.get("warnings", []),
    }
