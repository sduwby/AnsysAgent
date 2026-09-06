"""LlamaIndex 文档组装与分块封装（RAG 2.0）。

职责：
- 把"源文件 → 抽取文本 → metadata"组装为 llama_index Document；
- 用 SentenceSplitter（比旧 1200 字符硬切更保语义边界）切块；
- 统一把 Node 转成 keyword_index.json 兼容快照 chunk dict。

本模块所有 llama_index 依赖都做了可导入保护：
未安装 llama_index-core 时 available() 返回 False，由上层走旧版纯关键词路径。
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from rag.config import RAG_CHUNK_OVERLAP, RAG_CHUNK_SIZE
from rag.ingest import tokenize_text

_log = logging.getLogger(__name__)

try:
    from llama_index.core import Document
    from llama_index.core.node_parser import SentenceSplitter

    _LLAMA_CORE_AVAILABLE = True
except Exception:  # pragma: no cover - 缺依赖保护
    Document = None  # type: ignore[assignment,misc]
    SentenceSplitter = None  # type: ignore[assignment,misc]
    _LLAMA_CORE_AVAILABLE = False


def available() -> bool:
    """llama_index-core 是否可用。"""
    return _LLAMA_CORE_AVAILABLE


def canonical_path_key(path: str | Path) -> str:
    """规范化为正斜杠绝对路径，作为 Document.id_（增量去重锚点）。"""
    return str(Path(path).resolve()).replace("\\", "/")


def build_document(path: Path, text: str, source_type: str, doc_hash: str) -> Any:
    """组装一个 Document。id_ 稳定 = 规范化路径。"""
    if not _LLAMA_CORE_AVAILABLE:
        raise ImportError("llama_index-core 未安装，无法组装 Document")
    return Document(
        id_=canonical_path_key(path),
        text=text,
        metadata={
            "path": str(path),
            "title": path.stem,
            "source_type": source_type,
            "doc_hash": doc_hash,
        },
    )


def compute_doc_hash(text: str) -> str:
    """内容指纹（sha1）。文本抽取结果稳定则 hash 稳定 → 增量构建可跳过未变文档。"""
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


_splitter: Any | None = None


def get_splitter() -> Any:
    """进程内缓存 SentenceSplitter（参数来自环境变量）。"""
    global _splitter
    if not _LLAMA_CORE_AVAILABLE:
        raise ImportError("llama_index-core 未安装，无法分块")
    if _splitter is None:
        _splitter = SentenceSplitter(
            chunk_size=RAG_CHUNK_SIZE,
            chunk_overlap=RAG_CHUNK_OVERLAP,
        )
    return _splitter


def reset_splitter() -> None:
    """清空 splitter 缓存（改配置后重建时调用）。"""
    global _splitter
    _splitter = None


def split_documents(documents: list[Any]) -> list[Any]:
    """把 Document 列表切成 TextNode 列表（按输入文档顺序）。"""
    if not documents:
        return []
    splitter = get_splitter()
    return list(splitter.get_nodes_from_documents(documents))


def chunk_from_node(node: Any, chunk_index: int) -> dict:
    """把 TextNode 转成 keyword_index.json 兼容 chunk dict（id=node_id 保证向量/关键词同源合并）。"""
    content = node.get_content().strip()
    return {
        "id": node.node_id,
        "path": str(node.metadata.get("path", "")),
        "title": node.metadata.get("title", ""),
        "source_type": node.metadata.get("source_type", ""),
        "chunk_index": chunk_index,
        "content": content,
        "tokens": tokenize_text(content),
    }
