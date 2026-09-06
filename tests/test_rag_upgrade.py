"""RAG 2.0（LlamaIndex + Chroma）回归测试。

覆盖：
- 关键词降级路径：无嵌入/无向量库条件下 build/search 兼容旧契约；
- 增量摄取语义（需 llama_index-core + chromadb）：
    新增 → 摄取；未变 → 跳过；变更 → 删除重建该文档；删除文件 → 从 docstore/向量库清理。

运行方式：
    .venv\\Scripts\\python.exe -m pytest tests/test_rag_upgrade.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

# rag.config 依赖 agent.paths，会按环境变量解析数据目录；这里不依赖默认目录，全部显式传参
from rag import embedder, parser, storage
from rag.config import RAG_SCHEMA_VERSION
from rag.service import build_index, search_index

# --- 外部重依赖缺失时跳过向量级用例 -------------------------------------
_LLAMA_READY = parser.available() and embedder.available() and storage.available()


def _write_md(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class TestKeywordFallback:
    """无可用嵌入通道时必须能兼容旧契约（关键词检索）。"""

    def test_build_and_search_keyword_fallback(self, tmp_path: Path):
        doc = _write_md(tmp_path / "doc.md", "Back EMF extraction requires transient solution in Maxwell.")
        index_file = tmp_path / "keyword_index.json"

        payload = build_index(
            doc_paths=[str(doc)],
            index_path=index_file,
            with_embeddings=True,
            embedding_provider="missing_provider",  # 强制无向量通道
        )
        assert payload["schema_version"] == RAG_SCHEMA_VERSION
        assert payload["num_chunks"] >= 1
        assert payload["has_embeddings"] is False
        assert index_file.exists()

        result = search_index("back emf transient maxwell", top_k=3, index_path=index_file)
        assert result["results"], "关键词检索应至少返回一条片段"
        assert result["num_chunks"] == payload["num_chunks"]
        first = result["results"][0]
        # 兼容契约字段
        for key in ("id", "path", "title", "source_type", "chunk_index", "score", "snippet"):
            assert key in first
        assert "Back EMF" in first["snippet"] or "Back EMF" in str(payload["chunks"][0]["content"])

    def test_source_type_filter_keyword(self, tmp_path: Path):
        api_doc = _write_md(tmp_path / "sub" / "api.md", "pyaedt Maxwell transient setup.")
        _ = _write_md(tmp_path / "sub" / "tutorial.md", "Welcome to mechanical tutorial.")
        index_file = tmp_path / "keyword_index.json"
        payload = build_index(
            doc_paths=[str(tmp_path / "sub")],
            index_path=index_file,
            with_embeddings=False,
        )
        # 两个文件都应是 document 类型（无 api/official 路径标记）
        filtered = search_index("maxwell", top_k=5, source_type="document", index_path=index_file)
        assert filtered["results"]
        missing = search_index("maxwell", top_k=5, source_type="api", index_path=index_file)
        assert not missing["results"] or all(r["source_type"] != "document" for r in missing["results"])
        assert payload["schema_version"] == RAG_SCHEMA_VERSION


@pytest.mark.skipif(not _LLAMA_READY, reason="需要 llama_index-core + chromadb")
class TestVectorIncremental:
    """向量摄取增量语义（Document hash 判增/改/删）。"""

    FAKE_DIM = 8

    @pytest.fixture(autouse=True)
    def _fake_embeddings(self, monkeypatch):
        """把 compute_embeddings 换成确定性假向量，避免真实模型/网络。"""

        def _fake(texts, model_name="", provider=""):
            import hashlib

            vectors = []
            for text in texts:
                vec = [0.0] * self.FAKE_DIM
                for ch in text.lower():
                    if ch.isalnum():
                        vec[ord(ch) % self.FAKE_DIM] += 1.0
                vectors.append(vec)
            return vectors

        monkeypatch.setattr("rag.ingest.compute_embeddings", _fake)
        yield

    def _make_doc(self, tmp_path: Path, name: str, content: str):
        path = tmp_path / name
        _write_md(path, content)
        return parser.build_document(
            path,
            content,
            "internal",
            parser.compute_doc_hash(content),
        )

    def _vector_count(self, chroma_dir: Path) -> int:
        store = storage.get_vector_store(chroma_dir)
        return store.client.count()

    def test_incremental_upsert_and_delete(self, tmp_path: Path):
        chroma_dir = tmp_path / "chroma"
        docstore_path = tmp_path / "docstore.json"

        doc_a = self._make_doc(tmp_path, "a.md", "First Maxwell transient document body.")
        doc_b = self._make_doc(tmp_path, "b.md", "Second thermal icepak content body.")

        # 1) 首次全量摄取
        nodes1 = storage.ingest_incremental(
            [doc_a, doc_b],
            splitter=parser.get_splitter(),
            embed_model=embedder.ConfigEmbedding(provider="local", model="fake-model"),
            chroma_dir=chroma_dir,
            docstore_path=docstore_path,
        )
        assert nodes1, "首次摄取应产出节点"
        store1 = storage.get_docstore(docstore_path)
        assert len(store1.get_all_document_hashes()) == 2
        total1 = len(storage.collect_all_chunks(chroma_dir))
        assert total1 > 0
        assert self._vector_count(chroma_dir) == total1

        # 2) 相同输入再次摄取 → 全部跳过（不重复嵌入/写向量）
        nodes2 = storage.ingest_incremental(
            [doc_a, doc_b],
            splitter=parser.get_splitter(),
            embed_model=embedder.ConfigEmbedding(provider="local", model="fake-model"),
            chroma_dir=chroma_dir,
            docstore_path=docstore_path,
        )
        assert nodes2 == []
        assert self._vector_count(chroma_dir) == total1

        # 3) 修改一个文件 → 仅该文档重建，总数保持一致
        doc_b_new = self._make_doc(tmp_path, "b.md", "Second document with brand new thermal content.")
        nodes3 = storage.ingest_incremental(
            [doc_a, doc_b_new],
            splitter=parser.get_splitter(),
            embed_model=embedder.ConfigEmbedding(provider="local", model="fake-model"),
            chroma_dir=chroma_dir,
            docstore_path=docstore_path,
        )
        assert nodes3, "变更文档应被重建"
        assert all(n.ref_doc_id == doc_b_new.id_ for n in nodes3)
        store3 = storage.get_docstore(docstore_path)
        assert len(store3.get_all_document_hashes()) == 2
        total3 = len(storage.collect_all_chunks(chroma_dir))
        assert self._vector_count(chroma_dir) == total3

        # 4) 删除文件（只传剩余文档）→ 从 docstore 与向量库清理
        nodes4 = storage.ingest_incremental(
            [doc_a],
            splitter=parser.get_splitter(),
            embed_model=embedder.ConfigEmbedding(provider="local", model="fake-model"),
            chroma_dir=chroma_dir,
            docstore_path=docstore_path,
        )
        assert nodes4 == []
        store4 = storage.get_docstore(docstore_path)
        hashes = store4.get_all_document_hashes()
        assert set(hashes.values()) == {doc_a.id_}
        total4 = len(storage.collect_all_chunks(chroma_dir))
        assert self._vector_count(chroma_dir) == total4
        assert total4 < total3

    def test_vector_retriever_roundtrip(self, tmp_path: Path):
        """真实 llama 检索链路：写入 → VectorIndexRetriever 召回并还原文本/元数据。"""
        from llama_index.core import VectorStoreIndex
        from llama_index.core.retrievers import VectorIndexRetriever

        chroma_dir = tmp_path / "chroma"
        docstore_path = tmp_path / "docstore.json"
        doc = self._make_doc(
            tmp_path, "a.md",
            "Back EMF extraction requires a transient solution in Maxwell Magnetics.",
        )
        storage.ingest_incremental(
            [doc],
            splitter=parser.get_splitter(),
            embed_model=embedder.ConfigEmbedding(provider="local", model="fake-model"),
            chroma_dir=chroma_dir,
            docstore_path=docstore_path,
        )

        index = VectorStoreIndex.from_vector_store(
            vector_store=storage.get_vector_store(chroma_dir),
            embed_model=embedder.ConfigEmbedding(provider="local", model="fake-model"),
        )
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=2,
            embed_model=embedder.ConfigEmbedding(provider="local", model="fake-model"),
        )
        hits = retriever.retrieve("Back EMF transient")
        assert hits
        node = hits[0].node
        assert "Back EMF" in node.get_content()
        assert node.metadata.get("source_type") == "internal"
