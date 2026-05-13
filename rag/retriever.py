"""Local retrieval with vector search support."""

from __future__ import annotations

import math
import re

from rag.config import EMBEDDING_PROVIDER, SILICONFLOW_EMBEDDING_MODEL
from rag.config_manager import get_provider_config, read_env_file

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    _NUMPY_AVAILABLE = False

try:
    from rag.ingest import get_embedding_model, compute_embeddings_siliconflow, compute_embeddings_api
    _VECTOR_AVAILABLE = True
except ImportError:
    _VECTOR_AVAILABLE = False


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


def compute_cosine_similarity(vec1, vec2) -> float:
    if _NUMPY_AVAILABLE:
        a = np.asarray(vec1, dtype=np.float64).flatten()
        b = np.asarray(vec2, dtype=np.float64).flatten()
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))
    else:
        dot = sum(x * y for x, y in zip(vec1, vec2))
        norm_a = math.sqrt(sum(x * x for x in vec1))
        norm_b = math.sqrt(sum(x * x for x in vec2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def _encode_query(query: str, embedding_provider: str = "") -> list[float]:
    provider = embedding_provider or EMBEDDING_PROVIDER

    if provider == "siliconflow":
        results = compute_embeddings_siliconflow([query], model=SILICONFLOW_EMBEDDING_MODEL)
        return results[0]
    elif provider == "local":
        if not _VECTOR_AVAILABLE:
            raise ImportError("本地嵌入模型不可用")
        model = get_embedding_model()
        embedding = model.encode(query, convert_to_numpy=True)
        return embedding.tolist()
    else:
        # 自定义提供商
        provider_config = get_provider_config(provider)
        if not provider_config:
            raise ValueError(f"未知提供商: {provider}")
        
        env = read_env_file()
        prefix = f"CUSTOM_PROVIDER_{provider.upper()}"
        api_key = env.get(f"{prefix}_API_KEY", "")
        base_url = env.get(f"{prefix}_BASE_URL", "")
        model = env.get(f"{prefix}_MODEL", "default-model")
        
        if not api_key:
            raise ValueError(f"提供商 {provider} 的 API Key 未配置")
        if not base_url:
            raise ValueError(f"提供商 {provider} 的基础 URL 未配置")
        
        results = compute_embeddings_api([query], api_key, base_url, model)
        return results[0]


def retrieve_vector(index_data: dict, query: str, top_k: int = 5, source_type: str = "") -> list[dict]:
    if not _NUMPY_AVAILABLE and not _VECTOR_AVAILABLE:
        return []

    try:
        query_embedding = _encode_query(query, index_data.get("embedding_provider", ""))
    except Exception:
        return []

    candidates: list[dict] = []
    for chunk in index_data.get("chunks", []):
        if source_type and chunk.get("source_type") != source_type:
            continue

        embedding = chunk.get("embedding")
        if embedding is None:
            continue

        similarity = compute_cosine_similarity(query_embedding, embedding)

        if similarity > 0.1:
            snippet = chunk["content"][:800].replace("\n", " ").strip()
            candidates.append({
                "id": chunk["id"],
                "path": chunk["path"],
                "title": chunk["title"],
                "source_type": chunk["source_type"],
                "chunk_index": chunk["chunk_index"],
                "score": round(float(similarity), 4),
                "snippet": snippet,
            })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:top_k]


def retrieve_keyword(index_data: dict, query: str, top_k: int = 5, source_type: str = "") -> list[dict]:
    query_tokens = tokenize_query(query)
    candidates: list[dict] = []
    for chunk in index_data.get("chunks", []):
        if source_type and chunk.get("source_type") != source_type:
            continue
        score = score_chunk_keyword(query, query_tokens, chunk)
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


def retrieve(
    index_data: dict,
    query: str,
    top_k: int = 5,
    source_type: str = "",
    retrieval_mode: str = "hybrid",
) -> list[dict]:
    if retrieval_mode == "vector":
        return retrieve_vector(index_data, query, top_k, source_type)
    elif retrieval_mode == "keyword":
        return retrieve_keyword(index_data, query, top_k, source_type)
    else:
        vector_results = retrieve_vector(index_data, query, top_k * 2, source_type)
        keyword_results = retrieve_keyword(index_data, query, top_k * 2, source_type)

        merged = {}
        for result in vector_results:
            merged[result["id"]] = {"score": result["score"] * 0.6, "data": result}

        for result in keyword_results:
            if result["id"] in merged:
                merged[result["id"]]["score"] += result["score"] * 0.4
            else:
                merged[result["id"]] = {"score": result["score"] * 0.4, "data": result}

        final_results = [
            {**item["data"], "score": round(item["score"], 4)}
            for item in sorted(merged.values(), key=lambda x: x["score"], reverse=True)
        ]

        return final_results[:top_k]
