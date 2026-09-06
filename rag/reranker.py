"""SiliconFlow 重排（RAG 2.0，可选）。

调用 POST /rerank，把"候选 items（含 content）"按 query 重排，
返回按 relevance_score 降序的新列表（会改写 score 字段）。
参考 llama_index 官方集成 llama-index-postprocessor-siliconflow-rerank 的请求格式；
网络层使用本项目既有 httpx。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from rag.config import RAG_RERANK_BASE_URL, RAG_RERANK_MODEL, SILICONFLOW_API_KEY

_log = logging.getLogger(__name__)


def rerank_enabled() -> bool:
    """开启重排的条件：配置了模型 + SiliconFlow key 已配置。"""
    return bool(RAG_RERANK_MODEL and SILICONFLOW_API_KEY)


def rerank_items(query: str, items: list[dict], top_n: int) -> list[dict]:
    """对候选 items 重排；失败时抛异常（调用方捕获后回退融合结果）。"""
    if not items:
        return []
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": RAG_RERANK_MODEL,
        "query": query,
        "documents": [item.get("content", "") for item in items],
        "top_n": top_n,
        "return_documents": False,
    }
    resp = httpx.post(
        RAG_RERANK_BASE_URL,
        json=payload,
        headers=headers,
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return items[:top_n]

    reranked: list[dict] = []
    for entry in sorted(results, key=lambda r: r["relevance_score"], reverse=True):
        idx = entry.get("index")
        if not isinstance(idx, int) or idx < 0 or idx >= len(items):
            continue
        item = dict(items[idx])
        item["score"] = round(float(entry["relevance_score"]), 4)
        reranked.append(item)
    return reranked[:top_n]
