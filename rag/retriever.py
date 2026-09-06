"""检索层（RAG 2.0）。

- keyword：沿用本项目成熟的轻量字符打分（可离线、结果可预期），输入 keyword_index.json 快照 chunks；
- vector：LlamaIndex VectorIndexRetriever + Chroma（stores_text=True，查询直接还原 TextNode）；
- hybrid 融合 / 可选重排 由 service.search_index 编排。

vector 相关依赖全部可导入保护：不具备条件时调用方降级为 keyword。
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

from rag.config import (
    DEFAULT_INDEX_PATH,
    HYBRID_KEYWORD_WEIGHT,
    HYBRID_VECTOR_WEIGHT,
)
from rag.embedder import ConfigEmbedding, available as embedder_available
from rag.storage import available as storage_available, get_vector_store

_log = logging.getLogger(__name__)

try:
    from llama_index.core import Settings, VectorStoreIndex
    from llama_index.core.retrievers import VectorIndexRetriever
    from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters

    _VECTOR_AVAILABLE = True
except Exception:  # pragma: no cover - 缺依赖保护
    _VECTOR_AVAILABLE = False


# --------------------------------------------------------------------------
# 关键词打分（保留旧算法，行为与旧版完全一致）
# --------------------------------------------------------------------------

def tokenize_query(text: str) -> list[str]:
    ascii_words = re.findall(r"[A-Za-z0-9_./:-]+", text.lower())
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    return ascii_words + cjk_chars


def score_chunk_keyword(query: str, query_tokens: list[str], chunk: dict) -> float:
    content = chunk.get("content", "")
    chunk_tokens = chunk.get("tokens", [])
    if not content or not query_tokens:
        return 0.0

    score = 0.0
    token_hits = 0
    token_set = set(chunk_tokens)
    for token in query_tokens:
        if token in token_set:
            token_hits += 1
            score += 2.0
        if len(token) > 2 and token in content.lower():
            score += 1.0
    if query.lower() in content.lower():
        score += 5.0
    score += min(1.5, math.log(len(content) + 1, 10) / 4)
    score += token_hits / max(1, len(query_tokens))
    return score


def keyword_retrieve(
    chunks: list[dict],
    query: str,
    top_k: int = 5,
    source_type: str = "",
) -> list[dict]:
    """在快照 chunk 列表上做关键词检索，返回兼容结构 item（含 content 供融合/重排）。"""
    query_tokens = tokenize_query(query)
    candidates: list[dict] = []
    for chunk in chunks:
        if source_type and chunk.get("source_type") != source_type:
            continue
        score = score_chunk_keyword(query, query_tokens, chunk)
        if score <= 0:
            continue
        candidates.append(
            {
                "id": chunk.get("id", ""),
                "path": chunk.get("path", ""),
                "title": chunk.get("title", ""),
                "source_type": chunk.get("source_type", ""),
                "chunk_index": chunk.get("chunk_index", 0),
                "score": round(score, 4),
                "content": chunk.get("content", ""),
            }
        )
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_k]


# --------------------------------------------------------------------------
# 向量检索（LlamaIndex + Chroma）
# --------------------------------------------------------------------------

_vector_index_cache: dict[str, Any] = {}  # key=index_path → VectorStoreIndex


def vector_available() -> bool:
    """llama_index 检索类 + chroma 存储集成是否都可用。"""
    return _VECTOR_AVAILABLE and storage_available() and embedder_available()


def _get_index(index_path: str = str(DEFAULT_INDEX_PATH), embed_model: Any = None) -> Any:
    global _vector_index_cache
    key = str(index_path)
    if key not in _vector_index_cache:
        vector_store = get_vector_store()
        _vector_index_cache[key] = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            # 显式传 embed_model：避免 from_vector_store 回落到 Settings 默认 OpenAI 嵌入
            embed_model=embed_model,
        )
    return _vector_index_cache[key]


def invalidate_vector_cache() -> None:
    """清空向量索引缓存（build_index 或 schema 迁移后调用）。"""
    global _vector_index_cache
    _vector_index_cache = {}


def vector_retrieve(
    query: str,
    top_k: int = 5,
    source_type: str = "",
    provider: str = "",
    model: str = "",
    index_path: str = str(DEFAULT_INDEX_PATH),
) -> list[dict]:
    """向量召回 top_k，返回 item（含 content）。失败返回 [] 不抛（由调用方降级）。"""
    if not vector_available():
        return []
    try:
        embed_model = ConfigEmbedding(provider=provider, model=model)
        # 显式绑定全局 Settings.embed_model：llama_index 内部（VectorStoreIndex.__init__ /
        # QueryBundle 编码）仍会读取 Settings 默认嵌入；与本路所用编码保持一致可避免回落
        # 到 OpenAI 默认导致 ImportError。
        Settings.embed_model = embed_model
        filters = (
            MetadataFilters(
                filters=[ExactMatchFilter(key="source_type", value=source_type)]
            )
            if source_type
            else None
        )
        retriever = VectorIndexRetriever(
            index=_get_index(index_path, embed_model=embed_model),
            similarity_top_k=top_k,
            filters=filters,
            embed_model=embed_model,
        )
        nodes_with_score = retriever.retrieve(query)
    except Exception as exc:
        _log.warning("向量检索失败，本路跳过: %s", exc)
        return []

    items: list[dict] = []
    for node_with_score in nodes_with_score:
        node = node_with_score.node
        meta = getattr(node, "metadata", {}) or {}
        content = node.get_content()
        if not content:
            continue
        items.append(
            {
                "id": str(node.node_id),
                "path": meta.get("path", ""),
                "title": meta.get("title", ""),
                "source_type": meta.get("source_type", ""),
                "chunk_index": int(meta.get("chunk_index", 0) or 0),
                "score": round(float(node_with_score.score or 0.0), 4),
                "content": content,
            }
        )
    return items


# --------------------------------------------------------------------------
# 融合与输出（service 使用）
# --------------------------------------------------------------------------

def merge_hybrid(
    vector_items: list[dict],
    keyword_items: list[dict],
    top_k: int = 5,
    vector_weight: float = HYBRID_VECTOR_WEIGHT,
    keyword_weight: float = HYBRID_KEYWORD_WEIGHT,
) -> list[dict]:
    """按旧语义双路融合：同 id 加权相加后取 top_k。"""
    merged: dict[str, dict] = {}
    for item in vector_items:
        merged[item["id"]] = {
            "item": item,
            "score": float(item["score"]) * vector_weight,
        }
    for item in keyword_items:
        if item["id"] in merged:
            merged[item["id"]]["score"] += float(item["score"]) * keyword_weight
        else:
            merged[item["id"]] = {
                "item": item,
                "score": float(item["score"]) * keyword_weight,
            }
    final = sorted(
        (entry for entry in merged.values() if entry["score"] > 0),
        key=lambda entry: entry["score"],
        reverse=True,
    )
    return [dict(entry["item"], score=round(entry["score"], 4)) for entry in final[:top_k]]
