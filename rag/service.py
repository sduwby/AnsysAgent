"""RAG index build/load/search service（RAG 2.0：LlamaIndex + Chroma）。

对外薄壳，兼容旧返回结构：
- build_index() / search_index() / load_index() / invalidate_cache() 签名与返回字段不变；
- 向量/解析能力缺失时自动降级为关键词模式（与旧版行为一致）；
- 旧版 keyword_index.json（无 schema_version）会被检测并在首次检索时自动重建迁移。

新增内部模块：
  parser.py     Document 组装 + SentenceSplitter 分块
  embedder.py   现有嵌入通道 → llama_index BaseEmbedding
  storage.py    Chroma + SimpleDocumentStore + IngestionPipeline（增量）
  retriever.py  关键词 / 向量 / 融合
  reranker.py   可选 SiliconFlow 重排
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rag.config import (
    DEFAULT_CHROMA_DIR,
    DEFAULT_DOC_PATHS,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_INDEX_PATH,
    EMBEDDING_PROVIDER,
    RAG_DISABLE_VECTOR,
    RAG_SCHEMA_VERSION,
    RAG_TOP_K_CANDIDATES,
    SILICONFLOW_EMBEDDING_MODEL,
)
from rag import embedder, parser, reranker, storage
from rag.retriever import (
    HYBRID_KEYWORD_WEIGHT,
    HYBRID_VECTOR_WEIGHT,
    invalidate_vector_cache,
    keyword_retrieve,
    merge_hybrid,
    vector_available,
    vector_retrieve,
)
from rag.ingest import build_chunks, discover_documents, extract_text, guess_source_type

_log = logging.getLogger(__name__)

_snapshot_cache: dict | None = None
_snapshot_cache_path: str | None = None
_rebuild_attempted = False  # 进程内只做一次自动迁移，避免每次检索都触发


# --------------------------------------------------------------------------
# 公共：build_index
# --------------------------------------------------------------------------

def _collect_text_entries(doc_paths: list[str | Path]) -> tuple[list[dict], list[str]]:
    """发现文档并抽取文本，返回 entries（含 path/text/source_type/doc_hash）与 warnings。"""
    warnings: list[str] = []
    entries: list[dict] = []
    for document in discover_documents(doc_paths):
        text, doc_warnings = extract_text(document)
        warnings.extend(f"{document}: {warning}" for warning in doc_warnings)
        if not text.strip():
            continue  # 与旧 chunk_text 行为一致：空文本不产出 chunk
        entries.append(
            {
                "path": document,
                "text": text,
                "source_type": guess_source_type(document),
                "doc_hash": parser.compute_doc_hash(text),
            }
        )
    return entries, warnings


def _chunks_from_nodes(nodes: list[Any]) -> list[dict]:
    """把 TextNode 列表转成快照 chunk 列表（按 doc 顺序编号 chunk_index）。"""
    counters: dict[str, int] = {}
    chunks: list[dict] = []
    for node in nodes:
        path = str(node.metadata.get("path", ""))
        index = counters.get(path, 0)
        counters[path] = index + 1
        chunks.append(parser.chunk_from_node(node, index))
    return chunks


def _write_payload(payload: dict, index_path: str | Path) -> dict:
    global _snapshot_cache, _snapshot_cache_path
    target = Path(index_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _snapshot_cache = payload
    _snapshot_cache_path = str(target.resolve())
    invalidate_vector_cache()
    return payload


def build_index(
    doc_paths: list[str | Path] | None = None,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    with_embeddings: bool = True,
    model_name: str | None = None,
    embedding_provider: str = "",
) -> dict:
    """构建/增量更新知识索引并写快照。

    引擎选择（优先级）：
      1) 向量引擎：with_embeddings 且未禁用 RAG_DISABLE_VECTOR，且 llama_index + chroma + 嵌入
         通道齐备 → IngestionPipeline(UPSERTS_AND_DELETE) 增量摄取到 Chroma + docstore；
      2) LlamaIndex 分块（parser）关键词快照：llama_index-core 可用，但不满足向量条件；
      3) 旧版关键词路径（ingest.build_chunks）：llama_index-core 不可用。
    """
    source_paths = [Path(path) for path in (doc_paths or DEFAULT_DOC_PATHS)]
    warnings: list[str] = []
    embed_model: str | None = None
    embed_provider: str | None = None
    has_embeddings = False
    engine = "legacy"

    want_vector = (
        with_embeddings
        and not RAG_DISABLE_VECTOR
        and parser.available()
        and storage.available()
        and embedder.available()
    )
    if with_embeddings and want_vector:
        # 确定实际生效的 model/provider，先做"通道可用性"探测，避免中途失败污染旧库
        provider = embedding_provider or EMBEDDING_PROVIDER
        if model_name:
            resolved_model = model_name
        elif provider == "siliconflow":
            resolved_model = SILICONFLOW_EMBEDDING_MODEL
        else:
            resolved_model = DEFAULT_EMBEDDING_MODEL
        if not embedder.embedding_source_ready(provider, resolved_model):
            want_vector = False
            if provider == "local":
                warnings.append("本地嵌入不可用：未安装 sentence-transformers；本次仅生成关键词索引")
            elif provider == "siliconflow":
                warnings.append("SiliconFlow API Key 未配置；本次仅生成关键词索引")

    entries, collected_warnings = _collect_text_entries(source_paths)
    warnings.extend(collected_warnings)

    chunks: list[dict] = []
    if want_vector and entries:
        # 模型切换检测：换模型必须全量重建向量库，否则新节点用新模型、旧节点向量失真
        try:
            _maybe_reset_for_model_change(index_path, resolved_model, provider)
            documents = [
                parser.build_document(
                    entry["path"], entry["text"], entry["source_type"], entry["doc_hash"]
                )
                for entry in entries
            ]
            _log.info("向量摄取开始（增量）：%d 个文档 → %s/%s", len(documents), provider, resolved_model)
            storage.ingest_incremental(
                documents,
                splitter=parser.get_splitter(),
                embed_model=embedder.ConfigEmbedding(provider=provider, model=resolved_model),
            )
            # 快照直接从 Chroma 全量重建（docstore 只登记 Document，不存 chunk）
            chunks = storage.collect_all_chunks()
            embed_model, embed_provider, has_embeddings = resolved_model, provider, True
            engine = "llamaindex"
            _log.info("向量摄取完成，共 %d 个 chunk", len(chunks))
        except Exception as exc:
            # 摄取中途失败：清理半成品向量态，避免下次读到脏数据；回退关键词快照
            _log.warning("向量摄取失败，已回退关键词索引: %s", exc)
            warnings.append(f"向量摄取失败（{exc}），本次仅生成关键词索引；可重试重建")
            try:
                storage.ensure_clean_state()
            except Exception:  # pragma: no cover
                pass
            want_vector = False
            if parser.available():
                documents = [
                    parser.build_document(
                        entry["path"], entry["text"], entry["source_type"], entry["doc_hash"]
                    )
                    for entry in entries
                ]
                chunks = _chunks_from_nodes(parser.split_documents(documents))
                engine = "llamaindex"
            else:  # pragma: no cover
                chunks, legacy_warnings = build_chunks(source_paths, with_embeddings=False)
                warnings.extend(legacy_warnings)
    elif not want_vector and entries:
        if parser.available():
            documents = [
                parser.build_document(
                    entry["path"], entry["text"], entry["source_type"], entry["doc_hash"]
                )
                for entry in entries
            ]
            chunks = _chunks_from_nodes(parser.split_documents(documents))
            engine = "llamaindex"
            if with_embeddings and not RAG_DISABLE_VECTOR:
                warnings.append("llama_index/chroma 未就绪，本次仅生成关键词索引")
        else:
            chunks, legacy_warnings = build_chunks(source_paths, with_embeddings=False)
            warnings.extend(legacy_warnings)
            if with_embeddings:
                warnings.append("llama_index-core 未安装；本次仅生成关键词索引")
    else:
        if with_embeddings and not RAG_DISABLE_VECTOR and not parser.available():
            warnings.append("llama_index-core 未安装；本次仅生成关键词索引")

    payload = {
        "schema_version": RAG_SCHEMA_VERSION,
        "engine": engine,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "doc_paths": [str(path) for path in source_paths],
        "num_chunks": len(chunks),
        "chunks": chunks,
        "warnings": warnings,
        "embedding_model": embed_model,
        "embedding_provider": embed_provider,
        "has_embeddings": has_embeddings,
    }
    return _write_payload(payload, index_path)


def _maybe_reset_for_model_change(index_path: str | Path, model: str, provider: str) -> None:
    """若已有向量索引且嵌入模型与本次不同，则全量清空重建（保证写入/查询同模型）。"""
    path = Path(index_path)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    old_model = data.get("embedding_model")
    old_provider = data.get("embedding_provider")
    if data.get("has_embeddings") and (old_model != model or old_provider != provider):
        _log.info("检测到嵌入模型变更（%s/%s → %s/%s），清空向量库后全量重建",
                  old_provider, old_model, provider, model)
        storage.ensure_clean_state()


# --------------------------------------------------------------------------
# 公共：load_index / 缓存
# --------------------------------------------------------------------------

def load_index(index_path: str | Path = DEFAULT_INDEX_PATH) -> dict:
    """读取快照 JSON（不存在时抛 FileNotFoundError，语义与旧版一致）。"""
    global _snapshot_cache, _snapshot_cache_path
    path = Path(index_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"知识索引不存在: {path}")
    if _snapshot_cache is not None and _snapshot_cache_path == str(path):
        return _snapshot_cache
    data = json.loads(path.read_text(encoding="utf-8"))
    _snapshot_cache = data
    _snapshot_cache_path = str(path)
    return data


def invalidate_cache() -> None:
    """清空快照与向量索引缓存。"""
    global _snapshot_cache, _snapshot_cache_path, _rebuild_attempted
    _snapshot_cache = None
    _snapshot_cache_path = None
    _rebuild_attempted = False
    invalidate_vector_cache()


def _needs_rebuild(data: dict, index_path: str | Path) -> bool:
    """旧版缓存 / schema 不匹配 / 声称有向量但库丢失 → 需要自动重建。"""
    if data.get("schema_version") != RAG_SCHEMA_VERSION:
        return True
    if data.get("has_embeddings"):
        if RAG_DISABLE_VECTOR:
            return False
        if not storage.available():
            return False  # 向量库依赖缺失：检索时按 keyword 降级，不自动重建
        if not Path(DEFAULT_CHROMA_DIR).exists():
            return True
    return False


def _ensure_current(data: dict, index_path: str | Path = DEFAULT_INDEX_PATH) -> dict:
    """旧缓存自动迁移：进程内只尝试一次全量重建。"""
    global _rebuild_attempted
    if not _needs_rebuild(data, index_path):
        return data
    if _rebuild_attempted:
        _log.warning("知识索引需迁移但已尝试过重建，本次按当前数据继续")
        return data
    _rebuild_attempted = True
    _log.info("检测到旧版/过期知识索引，自动重建中（一次性）...")
    try:
        existing = [Path(p) for p in (data.get("doc_paths") or DEFAULT_DOC_PATHS) if Path(p).exists()]
        if existing:
            return build_index(doc_paths=existing, index_path=index_path)
        existing = [Path(p) for p in DEFAULT_DOC_PATHS if Path(p).exists()]
        if existing:
            return build_index(doc_paths=existing, index_path=index_path)
    except Exception as exc:
        _log.warning("索引自动迁移失败: %s", exc)
    return data


# --------------------------------------------------------------------------
# 公共：search_index
# --------------------------------------------------------------------------

def _format_result_item(item: dict) -> dict:
    content = item.get("content", "")
    return {
        "id": item.get("id", ""),
        "path": item.get("path", ""),
        "title": item.get("title", ""),
        "source_type": item.get("source_type", ""),
        "chunk_index": item.get("chunk_index", 0),
        "score": item.get("score", 0.0),
        "snippet": content[:800].replace("\n", " ").strip(),
    }


def search_index(
    query: str,
    top_k: int = 5,
    source_type: str = "",
    index_path: str | Path = DEFAULT_INDEX_PATH,
    retrieval_mode: str = "hybrid",
) -> dict:
    """按模式检索：vector / keyword / hybrid（默认）。返回结构与旧版一致。"""
    index_data = load_index(index_path=index_path)
    index_data = _ensure_current(index_data, index_path=index_path)

    has_embeddings = bool(index_data.get("has_embeddings", False))
    provider = index_data.get("embedding_provider", "") or ""
    model = index_data.get("embedding_model", "") or ""

    # 向量可用性判定（嵌入缺失 / 库缺失 / 强制关闭 都降级）
    vector_capable = (
        has_embeddings
        and not RAG_DISABLE_VECTOR
        and vector_available()
        and Path(DEFAULT_CHROMA_DIR).exists()
    )
    if retrieval_mode in ("vector", "hybrid") and not vector_capable:
        retrieval_mode = "keyword"

    candidate_n = max(1, top_k * RAG_TOP_K_CANDIDATES)
    chunks = index_data.get("chunks", [])
    results: list[dict] = []

    if retrieval_mode == "vector":
        items = vector_retrieve(
            query, top_k=candidate_n, source_type=source_type,
            provider=provider, model=model, index_path=str(Path(index_path)),
        )
        results = items[:top_k]
    elif retrieval_mode == "keyword":
        results = keyword_retrieve(chunks, query, top_k=top_k, source_type=source_type)
    else:  # hybrid
        vector_items = vector_retrieve(
            query, top_k=candidate_n, source_type=source_type,
            provider=provider, model=model, index_path=str(Path(index_path)),
        )
        keyword_items = keyword_retrieve(
            chunks, query, top_k=candidate_n, source_type=source_type
        )
        fused = merge_hybrid(
            vector_items,
            keyword_items,
            top_k=top_k,
            vector_weight=HYBRID_VECTOR_WEIGHT,
            keyword_weight=HYBRID_KEYWORD_WEIGHT,
        )
        # 可选重排（需配置 RAG_RERANK_MODEL + SiliconFlow key）；失败回退融合结果
        if reranker.rerank_enabled() and fused:
            try:
                fused = reranker.rerank_items(query, fused, top_n=top_k)
            except Exception as exc:
                _log.warning("重排失败，使用融合结果: %s", exc)
        results = fused[:top_k]

    return {
        "query": query,
        "top_k": top_k,
        "source_type": source_type or None,
        "index_path": str(index_path),
        "num_chunks": index_data.get("num_chunks", len(chunks)),
        "retrieval_mode": retrieval_mode,
        "has_embeddings": has_embeddings,
        "embedding_provider": provider,
        "results": [_format_result_item(item) for item in results],
        "warnings": index_data.get("warnings", []),
    }
