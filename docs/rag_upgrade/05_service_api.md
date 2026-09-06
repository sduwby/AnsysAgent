# 05 薄壳 API 与调用方整合（service.py）

## 1. 目标

`rag/service.py` 是对外唯一入口，所有调用方（`chat_agent`、`knowledge_tools`、测试）只依赖它。改造后其函数签名与返回结构**逐字段保持不变**，内部按 02/03/04 文档装配新引擎。

## 2. `build_index()` 新版流程

```python
def build_index(doc_paths=None, index_path=DEFAULT_INDEX_PATH,
                with_embeddings=True, model_name=None, embedding_provider="") -> dict:
    # 1) 发现文档（保留 ingest.discover_documents，过滤隐藏文件/目录）
    # 2) 逐文件抽取文本（保留 ingest.extract_text）→ (text, doc_warnings)
    #    空文本文件：计入 warnings，跳过（与旧行为一致）
    # 3) parser.build_document(...) 生成 Document 列表；doc_hash=sha1(text)
    # 4) 向量可用性探测：
    #      with_embeddings=True
    #      and not RAG_DISABLE_VECTOR
    #      and embedder 可用（本地库存在 或 provider 指向 API 且 key 已配）
    #      and importlib.util.find_spec("chromadb") 且 "llama_index" 可导入
    #    全部满足 → storage.ingest_incremental(documents)（UPSERTS_AND_DELETE）
    #    否则 warnings.append(...)，仅走分块(parser.split_text 级别)
    # 5) 从 docstore（向量路径）或本地节点列表（关键词路径）重建快照
    #    → 序列化 keyword_index.json（含 chunks + 元数据）
    # 6) 失效进程内 index 缓存 → 返回兼容 dict
```

返回 dict 字段（**与旧完全一致**）：

```python
{
  "built_at": iso, "doc_paths": [...], "num_chunks": int,
  "chunks": [...], "warnings": [...],
  "embedding_model": model 或 None, "embedding_provider": provider 或 None,
  "has_embeddings": bool,
}
```

`model_name`/`embedding_provider` 传参语义保持：非空覆盖配置；为空则回落 `EMBEDDING_PROVIDER` / 默认模型（siliconflow 默认 `BAAI/bge-m3`，local 默认 `all-MiniLM-L6-v2`）。

## 3. 进程内状态与缓存（服务层）

```
_engine_cache: None | {"index_path","has_embeddings","chunks","docstore_ref","index_obj",
                        "embedding_model","embedding_provider","warnings", ...}
```

- `load_index(index_path)`：懒加载。读取 `keyword_index.json`；若文件不存在抛 `FileNotFoundError`（既有语义，`knowledge_tools.search_official_docs` 依赖）。
- **schema/引擎一致性校验**：
  - 快照 `schema_version != RAG_SCHEMA_VERSION` → 视为旧版/不兼容，`load_index` 抛异常并提示"删除缓存后重建"；
  - `has_embeddings=True` 但 chromadb/llama_index 缺失，或 Chroma 目录缺失 → 重建判定：置 `_knowledge_index_ready=False` 语义由调用方触发下次 `build_index`（实现上 search 前自动尝试一次轻量 rebuild？见第 5 节约定）。
- `invalidate_cache()`：清空引擎缓存与 `VectorStoreIndex` 缓存（`build_index` 后自动调用）。
- 关键词快照在内存缓存，供 `keyword`/`hybrid` 检索；Chroma 组件对象复用，避免每次查询重建连接。

## 4. `search_index()` 新版流程

```python
def search_index(query, top_k=5, source_type="", index_path=DEFAULT_INDEX_PATH,
                 retrieval_mode="hybrid") -> dict:
    data = load_index(index_path)
    if retrieval_mode in ("vector", "hybrid") and 不具备向量条件:
        retrieval_mode = "keyword"        # 与旧降级逻辑一致
    # vector/hybrid → embedder 编码 → 向量召回（04 文档）
    # keyword/hybrid → 快照关键词召回
    # hybrid 融合 → [可选 rerank] → 截断 top_k
    return {
      "query","top_k","source_type","index_path","num_chunks",
      "retrieval_mode"(实际生效),"has_embeddings","embedding_provider",
      "results":[...], "warnings":[...],
    }
```

## 5. 与 `chat_agent` 的衔接约定（不改 chat_agent 代码）

`chat_agent._prepare_knowledge_index` 只在 `DEFAULT_INDEX_PATH` 不存在时调用一次 `build_index`。升级后为兼容旧缓存：
- 新版本首次运行发现旧版 `keyword_index.json`（schema_version 不匹配）时：`search_index`/`build_knowledge_index` 检测到不匹配 → 记录 warning 并**自动触发一次全量重建**（重建写回新 schema）。这样老用户升级后首次问答会自动完成迁移，无需手动删文件。
- 该自动迁移只发生一次；重建成功后在快照写入新 schema_version。
- `build_knowledge_index(force_rebuild=False)` 的"存在即跳过"语义仅在 schema 匹配时生效。

## 6. 调用方变更清单

| 文件 | 变更 |
|---|---|
| `agent/chat_agent.py` | 无（只调 `build_index`/`search_index`） |
| `tools/knowledge_tools.py` | 无（只调 `build_index`/`search_index`；`index_path`/`doc_paths` 参数照旧） |
| `main.py` | 帮助文案中 `.rag/keyword_index.json` 仍成立；"重建知识索引"口语化指令走 knowledge tool，无需改 |
| `rag/config_manager.py` | 无 |
| `rag/ingest.py` | 内部计算函数迁移至 embedder 后，其余保持不变 |
| `rag/retriever.py` | 保持 keyword 打分算法；`retrieve()` 入口可保留仅供内部，行为对齐第 4 节 |

## 7. 兼容性回归清单（由既有测试背书）

- `tests/test_regressions.py::test_build_knowledge_index_creates_local_index`：index_path 文件存在、num_chunks≥1。
- `test_search_official_docs_returns_relevant_chunk`：snippet 包含原文 "Back EMF"。
- `test_build_knowledge_index_reads_notebook_cells`：ipynb cell 可检索。
- `test_discover_documents_skips_hidden_files`：隐藏文件跳过。
- `test_chat_agent_*`：chat_agent 侧逻辑（测试用 patch 掉 search_index，不依赖真实引擎）。

> 注：旧测试文件写在 `/tmp` 下（Windows 上为当前盘 `/tmp` 映射），沿用即可。
