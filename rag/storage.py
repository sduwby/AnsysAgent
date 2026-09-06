"""Chroma + SimpleDocumentStore + IngestionPipeline 装配（RAG 2.0）。

提供本地无服务持久化的增量摄取：
- vector store：chromadb.PersistentClient（目录持久化）；
- docstore：llama_index SimpleDocumentStore（单 JSON 落盘），用于增量去重与快照重建；
- pipeline：IngestionPipeline(docstore_strategy=UPSERTS_AND_DELETE)，
  行为见 llama_index/core/ingestion/pipeline.py：按 Document.id_ hash 判定增/改/删，
  未变文档直接跳过（不重复嵌入）。

所有 llama_index / chromadb 依赖均可导入保护；未安装时 available() 返回 False。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from rag.config import DEFAULT_CHROMA_DIR, DEFAULT_DOCSTORE_PATH, RAG_COLLECTION_NAME

_log = logging.getLogger(__name__)

try:
    from llama_index.core.ingestion import DocstoreStrategy, IngestionPipeline
    from llama_index.core.storage.docstore import SimpleDocumentStore
    from llama_index.vector_stores.chroma import ChromaVectorStore

    _STORAGE_AVAILABLE = True
except Exception:  # pragma: no cover - 缺依赖保护
    _STORAGE_AVAILABLE = False


def available() -> bool:
    """llama_index core + chroma 向量存储集成是否全部可用。"""
    return _STORAGE_AVAILABLE


def get_vector_store(chroma_dir: str | Path = DEFAULT_CHROMA_DIR) -> Any:
    """构造（或复用磁盘上）Chroma collection。

    依据 llama_index-vector-stores-chroma：from_params 内部用
    chromadb.PersistentClient(path=persist_dir) 本地持久化。
    """
    if not _STORAGE_AVAILABLE:
        raise ImportError("未安装 chromadb / llama_index-vector-stores-chroma")
    return ChromaVectorStore.from_params(
        persist_dir=str(chroma_dir),
        collection_name=RAG_COLLECTION_NAME,
    )


def get_docstore(docstore_path: str | Path = DEFAULT_DOCSTORE_PATH) -> Any:
    """加载（或新建内存态）SimpleDocumentStore；docstore 需在摄取后显式 persist。"""
    if not _STORAGE_AVAILABLE:
        raise ImportError("未安装 llama_index.core")
    path = Path(docstore_path)
    if path.exists():
        return SimpleDocumentStore.from_persist_path(str(path))
    return SimpleDocumentStore()


def persist_docstore(docstore: Any, docstore_path: str | Path = DEFAULT_DOCSTORE_PATH) -> None:
    path = Path(docstore_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    docstore.persist(str(path))


def ingest_incremental(
    documents: list[Any],
    splitter: Any,
    embed_model: Any,
    chroma_dir: str | Path = DEFAULT_CHROMA_DIR,
    docstore_path: str | Path = DEFAULT_DOCSTORE_PATH,
) -> list[Any]:
    """执行一次增量摄取，返回本轮实际变更/新增的节点。

    语义（UPSERTS_AND_DELETE）：
      - 每次必须传入当前全量文档列表，pipeline 据此判定删除；
      - 未变文档（doc_id + hash 相同）被跳过，不重新嵌入。
    """
    if not _STORAGE_AVAILABLE:
        raise ImportError("未安装 chromadb / llama_index-vector-stores-chroma")
    if not documents:
        return []
    vector_store = get_vector_store(chroma_dir)
    docstore = get_docstore(docstore_path)
    pipeline = IngestionPipeline(
        transformations=[splitter, embed_model],
        vector_store=vector_store,
        docstore=docstore,
        docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
        disable_cache=True,  # 去重依赖 docstore hash，不需要 transformation cache
    )
    nodes = pipeline.run(documents=list(documents))
    persist_docstore(pipeline.docstore or docstore, docstore_path)
    return list(nodes)


def collect_all_chunks(
    chroma_dir: str | Path = DEFAULT_CHROMA_DIR,
) -> list[dict]:
    """从 Chroma 读取全部向量记录，重建快照 chunk 列表。

    说明：llama_index IngestionPipeline 的 docstore 仅登记 Document（ref_doc/hash），
    chunk 文本与元数据实际存于 Chroma（stores_text=True）。因此快照重建直接从
    Chroma 全量读取，保证与向量检索结果（node id）同源。
    """
    if not _STORAGE_AVAILABLE:
        return []
    try:
        store = get_vector_store(chroma_dir)
        data = store.client.get(include=["metadatas", "documents"])
    except Exception as exc:  # pragma: no cover - 空/损坏库防御
        _log.debug("读取 Chroma 全量失败: %s", exc)
        return []

    ids = data.get("ids") or []
    metadatas = data.get("metadatas") or []
    documents = data.get("documents") or []

    from rag.ingest import tokenize_text

    chunks: list[dict] = []
    for idx, (node_id, meta, content) in enumerate(zip(ids, metadatas, documents)):
        text = (content or "").strip()
        if not text:
            continue
        meta = meta or {}
        chunks.append(
            {
                "id": str(node_id),
                "path": str(meta.get("path", "") or ""),
                "title": str(meta.get("title", "") or ""),
                "source_type": str(meta.get("source_type", "") or ""),
                "chunk_index": idx,
                "content": text,
                "tokens": tokenize_text(text),
            }
        )
    return chunks


def ensure_clean_state() -> None:
    """仅测试/排障用：删除 Chroma 与 docstore，强制下次全量重建。"""
    for target in (DEFAULT_CHROMA_DIR, DEFAULT_DOCSTORE_PATH):
        path = Path(target)
        try:
            if path.is_dir():
                import shutil

                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                os.remove(path)
        except OSError:  # pragma: no cover
            _log.debug("清理失败: %s", target)
