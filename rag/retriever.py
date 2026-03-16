"""Local keyword retrieval."""

from __future__ import annotations

import math
import re


def tokenize_query(text: str) -> list[str]:
    ascii_words = re.findall(r"[A-Za-z0-9_./:-]+", text.lower())
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    return ascii_words + cjk_chars


def score_chunk(query: str, query_tokens: list[str], chunk: dict) -> float:
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


def retrieve(index_data: dict, query: str, top_k: int = 5, source_type: str = "") -> list[dict]:
    query_tokens = tokenize_query(query)
    candidates: list[dict] = []
    for chunk in index_data.get("chunks", []):
        if source_type and chunk.get("source_type") != source_type:
            continue
        score = score_chunk(query, query_tokens, chunk)
        if score <= 0:
            continue
        snippet = chunk["content"][:800].replace("\n", " ").strip()
        candidates.append({
            "id": chunk["id"],
            "path": chunk["path"],
            "title": chunk["title"],
            "source_type": chunk["source_type"],
            "chunk_index": chunk["chunk_index"],
            "score": round(score, 4),
            "snippet": snippet,
        })
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_k]
