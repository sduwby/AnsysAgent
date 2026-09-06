# 04 检索与重排改造（retriever.py / reranker.py）

## 1. 目标

在保持 `search_index(query, top_k, source_type, retrieval_mode)` 返回结构不变的前提下，把向量召回替换为 LlamaIndex 链路并新增可选重排。关键词打分继续用本项目成熟的轻量算法（可离线、可解释、被既有测试依赖）。

## 2. 召回池设计

为兼容旧的 `hybrid` 语义（双路各取 top_k×2 融合），引入环境变量 `RAG_TOP_K_CANDIDATES`（默认 2，含义 = 每路召回 top_k 的倍数）。流程：

```
candidate_n = top_k * RAG_TOP_K_CANDIDATES
vector   → VectorIndexRetriever(similarity_top_k=candidate_n)
keyword  → 快照打分取前 candidate_n
hybrid   → 归一化前融合（保持旧权重变量 HYBRID_VECTOR_WEIGHT / HYBRID_KEYWORD_WEIGHT）
可选 rerank → 对候选集执行重排（取回 relevance score）
最终截断 top_k → 统一输出结构
```

> 说明：旧实现在 vector/keyword 各自得分量纲相差很大时直接加权相加，量纲问题依旧存在。本期**不改融合公式**（保持行为可预期、避免新回归面），把精度提升主要放在 ①真向量召回 + ②可选重排两处。文档记录后续可选做 min-max/softmax 归一化融合作为独立优化项。

## 3. Vector 召回（retriever.py）

```python
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.core.retrievers import VectorIndexRetriever

# 进程内缓存一个 index 对象（底层绑定 Chroma collection + embedder）
index = VectorStoreIndex.from_vector_store(vector_store=get_vector_store())
index._embed_model = config_embedding      # 查询编码用当前配置

retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=candidate_n,
    filters=MetadataFilters(
        filters=[ExactMatchFilter(key="source_type", value=source_type)]
    ) if source_type else None,
)
nodes_with_score = retriever.retrieve(query_str)   # -> List[NodeWithScore]
```

要点（本地源码核验）：
- `ChromaVectorStore.stores_text=True`：查询直接把文本与元数据还原成 `TextNode`，`VectorIndexRetriever` 不需要回查 docstore（`_determine_nodes_to_fetch` 只在无文本时才取 docstore）。
- Chroma 距离 `math.exp(-distance)` 转相似度；NodeWithScore.score 即该相似度。
- `MetadataFilters + ExactMatchFilter(key="source_type")` 映射为 Chroma `where={source_type: {"$eq": ...}}`（ChromaVectorStore 内 `_to_chroma_filter`）。
- 需要设置全局 `Settings.embed_model = config_embedding` 或直接给 index 注入 embed_model；优先显式注入避免全局副作用。

### 进程内缓存与失效
- `VectorStoreIndex` 对象在进程内做懒加载缓存；`build_index` 执行后主动失效该缓存，保证下一次查询拿到新向量。
- `source_type` 不同只影响 filter 参数，无需重建对象。

## 4. Keyword 召回（保留旧算法）

沿用 `rag/retriever.py` 现有 `tokenize_query` / `score_chunk_keyword`，输入改为快照 chunks（内容来自 docstore 节点）。仅性能细节：快照建索引时已预置 `tokens`，检索时零重复分词。排序、`source_type` 过滤、命中判空逻辑与旧版一致，保证"纯关键词模式"与既有测试完全等价。

## 5. Rerank（reranker.py，可选）

### 5.1 触发条件
`RAG_RERANK_MODEL` 非空 **且** `SILICONFLOW_API_KEY` 已配置（复用现有 key）时，`hybrid` 融合后、截断前对候选集执行重排。

### 5.2 实现

参考 llama_index 官方集成 `SiliconFlowRerank`（monorepo `llama-index-postprocessor-siliconflow-rerank`）的请求
格式，本项目以 `rag/reranker.py::rerank_items(query, items, top_n)` 实现（直接面向融合后的候选 dict，
避免无谓构造 llama 节点对象；网络层用项目既有 httpx，而非官方集成的 requests）：

- 端点 `POST {RAG_RERANK_BASE_URL}`，请求体 `{"model","query","documents":[...],"top_n":...,"return_documents":false}`；
- 响应 `results[].index` 重映射回原候选，`relevance_score` 覆盖 score 后按降序取 `top_n`。
- 若未来需要挂在 llama_index QueryEngine 链路，`rag/reranker.py` 中可扩展为
  `BaseNodePostprocessor._postprocess_nodes` 实现（基类见 llama_index `postprocessor/types.py`），接口等价。

### 5.3 容错
- 网络/格式异常 → `service` 捕获并记 warning，回退使用融合结果（不阻断主流程）。
- `top_n` 取 `top_k`；`RAG_RERANK_MODEL` 未配置或 `SILICONFLOW_API_KEY` 缺失时不开启，零开销。

## 6. 统一结果映射（兼容层）

把内部 NodeWithScore/快照 dict 映射为旧 result item 字段：

```python
{
    "id": node_id 或 path#chunk_index,
    "path": node.metadata["path"] 或 snapshot.path,
    "title": node.metadata["title"],
    "source_type": node.metadata["source_type"],
    "chunk_index": n,
    "score": round(float(score), 4),
    "snippet": content[:800].replace("\n", " ").strip(),
}
```

向量与关键词两路的 item 用**同一 canonical id 融合去重**（快照 chunk 与 Chroma 节点同源），融合/重排完成后输出前 top_k。

## 7. 检索模式矩阵

| retrieval_mode | 行为 |
|---|---|
| `vector` | 仅向量召回；embedding 不可用 → 返回空并告警 |
| `keyword` | 仅快照关键词（永不依赖 chromadb/网络） |
| `hybrid`（默认） | 双路融合；向量不可用时自动退化为 keyword；开启 rerank 时重排 |

## 8. 验收要点

- `search_official_docs("back emf transient maxwell", top_k=3)` 在不联网（keyword 降级）环境下仍返回含原文片段的 snippet（既有测试）。
- `source_type="api"` 只返回该来源。
- 开启 rerank 且 key 有效时，返回顺序按 relevance_score；key 无效或网络失败不报错。
