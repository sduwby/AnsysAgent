# 03 Embedding 桥接改造（embedder.py）

## 1. 问题

LlamaIndex 内部期望一个 `BaseEmbedding`（`llama_index.core.base.embeddings.base.BaseEmbedding`），它同时承担：
1. **索引期**：作为 `IngestionPipeline.transformations` 之一，对分块后的 TextNode 批量计算并回填 `node.embedding`（`__call__` 走 `get_text_embedding_batch`）。
2. **查询期**：`VectorIndexRetriever` 用 `embed_model.get_agg_embedding_from_queries(...)` 对 query 编码。

本项目已有双通道嵌入能力（本地 sentence-transformers / SiliconFlow OpenAI 兼容 `/embeddings` / 自定义 provider），且 `_encode_query` 已经存在。不能另起一套，否则 `/embed` 配置的真源地位会被绕过。

## 2. 设计：`ConfigEmbedding(BaseEmbedding)`

在 `rag/embedder.py` 实现：

```python
from llama_index.core.base.embeddings.base import BaseEmbedding

class ConfigEmbedding(BaseEmbedding):
    """把 rag.config/当前 .env 的嵌入配置桥接成 llama_index BaseEmbedding。"""

    def __init__(self, provider: str = "", model_name: str = "", **kwargs):
        super().__init__(**kwargs)
        self._provider = provider or EMBEDDING_PROVIDER
        self._model_name = model_name  # 为空则按 provider 决定默认模型

    def _get_text_embedding(self, text: str):
        return self._embed_batch([text])[0]

    def _get_text_embeddings(self, texts: list[str]):
        return self._embed_batch(texts)

    def _get_query_embedding(self, query: str):
        return self._embed_batch([query])[0]

    def _embed_batch(self, texts: list[str]):
        return compute_embeddings(
            texts,
            model_name=self._model_name,
            provider=self._provider,        # 复用 rag/ingest(或迁移后 rag/embedder) 的既有实现
        )
```

依据本地源码核验：
- `BaseEmbedding` 的抽象方法即为 `_get_query_embedding` 与 `_get_text_embedding`（`_get_text_embeddings` 有默认实现按条调用，但既然我们有批量通道，直接覆写批量版以复用一次 API 请求/一次本地 encode）。
- `BaseEmbedding.__call__(nodes)` 会为缺 embedding 的节点批量生成并 set，天然可作 transformation 使用（`IngestionPipeline` docstring 示例即把 `OpenAIEmbedding()` 放进 `transformations`）。

## 3. 模型一致性（写入/查询）

- `build_index` 时由当前配置（provider + model）实例化 `ConfigEmbedding`；同一配置在**整个进程内缓存复用**（懒加载单例），保证同一次会话内索引/查询编码一致。
- 每次 build 把实际生效的 `embedding_model` / `embedding_provider` 写进快照 `keyword_index.json` 元数据。
- 查询期若 `search_index` 检测到 `has_embeddings=True` 但当前 env 配置与快照模型不一致：**只告警并继续按当前配置查询**（加日志 + warnings），不自动重建（避免用户无感触发大批量 API 调用）。文档建议用户在 `/embed` 换模型后手动"重建知识索引"。

## 4. 与旧模块的衔接

- `rag/ingest.py` 中的 `compute_embeddings*`（local/siliconflow/api、批量 64 + 指数退避重试）逻辑保留，改为由 embedder 引用；迁移后放 `rag/embedder.py` 更内聚，`ingest.py` 对外保留 `get_embedding_model`（部分旧引用）或同步更新引用点。
- `rag/retriever.py` 旧 `_encode_query` 将被删除，查询编码统一走 `ConfigEmbedding`（避免两套代码路径漂移）。

## 5. 降级与错误语义

- 复用现有语义：provider=local 但未装 sentence-transformers → 抛 ImportError 被 build 捕获 → 进入"纯关键词"降级（02 文档第 6 节）。
- provider=siliconflow 但未配 key → 同样降级并在 warnings 说明。
- 网络/限流错误 → 沿用 `compute_embeddings_api` 的重试；最终失败由 build 捕获转关键词模式，query 端则在该轮跳过向量召回（vector 返回空、hybrid 退化为关键词）。

## 6. 可选增强（本期先不做，文档留口）

- 多模态嵌入（图片/表格块）——需接入 SiliconFlow 多模态模型与解析器，本期范围外。
- 向量维度与模型名自动记录，作为后续 index 健康检查的基础字段（本期仅记录 embedding_model 字段）。
