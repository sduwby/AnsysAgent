"""把本项目既有嵌入能力桥接成 llama_index BaseEmbedding（RAG 2.0）。

BaseEmbedding 同时承担两个角色（源码依据 llama_index.core.base.embeddings.base）：
- 索引期：IngestionPipeline.transformations 之一，对 TextNode 批量回填 node.embedding；
- 查询期：VectorIndexRetriever 用 get_agg_embedding_from_queries 对 query 编码。

桥接保证 /embed 配置（provider + model）仍是唯一真源，写入与查询编码同模型。
"""

from __future__ import annotations

import logging
from typing import Any

from rag.config import EMBEDDING_PROVIDER

_log = logging.getLogger(__name__)

try:
    from llama_index.core.base.embeddings.base import BaseEmbedding

    _LLAMA_CORE_AVAILABLE = True
except Exception:  # pragma: no cover - 缺依赖保护
    BaseEmbedding = None  # type: ignore[assignment,misc]
    _LLAMA_CORE_AVAILABLE = False


if _LLAMA_CORE_AVAILABLE:

    class ConfigEmbedding(BaseEmbedding):
        """读取当前配置的嵌入桥接（provider/model 显式传入，不依赖全局 Settings）。"""

        provider: str = ""
        model: str = ""

        @classmethod
        def class_name(cls) -> str:
            return "ConfigEmbedding"

        def _resolved_model(self) -> str:
            if self.model:
                return self.model
            from rag.config import (
                DEFAULT_EMBEDDING_MODEL,
                SILICONFLOW_EMBEDDING_MODEL,
            )
            if (self.provider or EMBEDDING_PROVIDER) == "siliconflow":
                return SILICONFLOW_EMBEDDING_MODEL
            return DEFAULT_EMBEDDING_MODEL

        def _embed_batch(self, texts: list[str]) -> list[list[float]]:
            # 惰性 import，避免 import 环与缺依赖时的模块级失败
            from rag.ingest import compute_embeddings

            embeddings = compute_embeddings(
                texts,
                model_name=self._resolved_model(),
                provider=self.provider or EMBEDDING_PROVIDER,
            )
            return [list(item) for item in embeddings]

        def _get_text_embedding(self, text: str) -> list[float]:
            return self._embed_batch([text])[0]

        def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
            return self._embed_batch(list(texts))

        def _get_query_embedding(self, query: str) -> list[float]:
            return self._embed_batch([query])[0]

        async def _aget_query_embedding(self, query: str) -> list[float]:
            # 同步实现即满足使用；异步版本委托同步
            return self._get_query_embedding(query)

else:  # pragma: no cover
    ConfigEmbedding = None  # type: ignore[assignment,misc]


def available() -> bool:
    """llama_index-core 嵌入基类是否可用。"""
    return _LLAMA_CORE_AVAILABLE and ConfigEmbedding is not None


def embedding_source_ready(provider: str, model: str) -> bool:
    """当前 provider+model 是否具备计算条件（不真正调用嵌入）。"""
    if provider == "local":
        from rag.ingest import _LOCAL_EMBEDDING_AVAILABLE

        return _LOCAL_EMBEDDING_AVAILABLE
    if provider == "siliconflow":
        from rag.config import SILICONFLOW_API_KEY

        return bool(SILICONFLOW_API_KEY)
    # 自定义 provider：配置存在即视为可尝试（真正失败由 build 捕获并降级）
    from rag.config_manager import get_provider_config

    return get_provider_config(provider) is not None
