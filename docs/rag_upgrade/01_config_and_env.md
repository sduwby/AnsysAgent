# 01 配置与运行环境改造

## 1. 目标

1. 让"引入 llama_index 内核"是可选的（`[rag]` extras），不污染纯执行模式。
2. 保留 `/embed` 现有配置语义：`EMBEDDING_PROVIDER`（local/siliconflow/自定义）+ 模型名是唯一"真源"。
3. 新增的 LlamaIndex/增量/分块/重排参数都有合理默认值并可被环境变量覆盖。

## 2. pyproject.toml `[rag]` extras

```toml
rag = [
    "pypdf>=4.2.0",
    "sentence-transformers>=2.7.0",
    "numpy>=1.26.0",
    "llama-index-core>=0.12,<1.0",
    "llama-index-vector-stores-chroma>=0.4,<1.0",
    "chromadb>=0.5,<2.0",
]
```

同时把上面三项同步写入 `requirements.txt` 的 `# --- RAG ---` 段（requirements 由 pyproject 生成，此处人工同步一次）。

## 3. 新增环境变量（写入 `.env.exampl`，代码在 `rag/config.py`）

| 变量 | 默认值 | 含义 |
|---|---|---|
| `RAG_SCHEMA_VERSION` | `"llamaindex-1"` | 索引快照 schema/引擎版本；不匹配视为需重建 |
| `RAG_COLLECTION_NAME` | `"ansys_knowledge"` | Chroma collection 名 |
| `RAG_CHUNK_SIZE` | `512` | SentenceSplitter `chunk_size`（单位 token） |
| `RAG_CHUNK_OVERLAP` | `50` | SentenceSplitter `chunk_overlap`（token） |
| `RAG_RETRIEVAL_MODE` | `"hybrid"` | search_index 默认检索模式 |
| `RAG_TOP_K_CANDIDATES` | `2` | 召回池倍率（每路先取 top_k×N 再融合/重排） |
| `RAG_RERANK_MODEL` | `""`（空=关闭） | 如 `BAAI/bge-reranker-v2-m3`；开启后 hybrid 路径执行重排 |
| `RAG_RERANK_BASE_URL` | `https://api.siliconflow.cn/v1/rerank` | 重排服务端点 |
| `RAG_HYBRID_VECTOR_WEIGHT` / `RAG_HYBRID_KEYWORD_WEIGHT` | 沿用 0.6/0.4 | 融合权重（向后兼容既有名） |

旧变量（`EMBEDDING_PROVIDER`/`EMBEDDING_MODEL`/`SILICONFLOW_*`/`HYBRID_*_WEIGHT`）全部保留不动。

设计要点（依据 llama_index 源码）：SentenceSplitter 默认即 `DEFAULT_CHUNK_SIZE=1024`，但本项目旧实现是 ~1200 字符/120 重叠；按英文约 4 字符/token 折算，512 token 略粗于旧粒度、检索粒度和嵌入成本平衡（llama_index 官方对 QA/检索场景也推荐 ~512）。纯离线或中文为主的内部文档可调小，纯英文长文可调大。

## 4. 降级开关（环境变量）

| 变量 | 默认 | 说明 |
|---|---|---|
| `RAG_DISABLE_VECTOR` | `""` | 设 `"1"` 时 build/search 完全走关键词快照（等价旧"纯关键词"路径，用于排障） |

## 5. 保留/调整的现有代码

- `rag/config_manager.py`：不改逻辑。它是 `/embed` 与 embedding_config_tool 的配置后端（provider 列表、自定义 provider、写 `~/.AnsysAgent/.env`）。改造中嵌入实现只依赖它的读取结果。
- `tools/embedding_config_tool.py` / `main.py /embed`：不改。
- `agent/chat_agent.py`：不改（触发词、注入逻辑、`_knowledge_index_ready` 语义保持）。
- `rag/config.py` 顶部 `getattr(sys, "frozen", False)` 分叉逻辑保留：内置只读文档目录与用户可写目录仍然分开。
- 新增常量（放在 `rag/config.py`）：
  ```python
  RAG_SCHEMA_VERSION = os.environ.get("RAG_SCHEMA_VERSION", "llamaindex-1")
  DEFAULT_CHROMA_DIR = DEFAULT_INDEX_DIR / "chroma"
  DEFAULT_DOCSTORE_PATH = DEFAULT_INDEX_DIR / "docstore.json"
  ```

## 6. 验收

- 不带 `[rag]` 装最小依赖时，`import rag` 不报错、`/embed providers` 正常。
- 带 `[rag]` 时 `python -c "import llama_index.core, chromadb; print('ok')"` 通过。
- 项目根跑 `python -m pytest tests/test_regressions.py -k knowledge` 全绿（见 06 文档）。
