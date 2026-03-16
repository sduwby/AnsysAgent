"""Knowledge retrieval tools backed by the local RAG index."""

from __future__ import annotations

from rag.config import DEFAULT_DOC_PATHS, DEFAULT_INDEX_PATH
from rag.service import build_index, search_index
from tools.utils import _ok, _err, append_warnings, ok_message


def build_knowledge_index(
    doc_paths: list[str] | None = None,
    force_rebuild: bool = True,
) -> dict:
    """Build a local keyword index for official/internal documents."""
    try:
        if not force_rebuild and DEFAULT_INDEX_PATH.exists():
            return _ok(ok_message(
                "知识索引已存在，跳过重建",
                index_path=str(DEFAULT_INDEX_PATH),
                reused_existing_index=True,
            ))
        index_data = build_index(doc_paths=doc_paths or DEFAULT_DOC_PATHS)
        result = ok_message(
            f"知识索引已构建，共 {index_data['num_chunks']} 个 chunk",
            index_path=str(DEFAULT_INDEX_PATH),
            num_chunks=index_data["num_chunks"],
            doc_paths=index_data["doc_paths"],
        )
        return _ok(append_warnings(result, index_data.get("warnings", [])))
    except Exception as exc:
        return _err(str(exc))


def search_official_docs(
    query: str,
    top_k: int = 5,
    source_type: str = "",
) -> dict:
    """Search the local RAG index for relevant official or internal docs."""
    try:
        if top_k <= 0:
            return _err("top_k 必须为正整数")
        result = search_index(query=query, top_k=top_k, source_type=source_type, index_path=DEFAULT_INDEX_PATH)
        return _ok(ok_message(
            f"已检索到 {len(result['results'])} 条相关知识片段",
            query=query,
            top_k=top_k,
            source_type=source_type or None,
            index_path=result["index_path"],
            num_chunks=result["num_chunks"],
            results=result["results"],
            warnings=result.get("warnings", []),
        ))
    except FileNotFoundError:
        return _err(f"知识索引不存在，请先调用 build_knowledge_index。默认路径: {DEFAULT_INDEX_PATH}")
    except Exception as exc:
        return _err(str(exc))
