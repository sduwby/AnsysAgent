# 02 摄取与索引改造（ingest / parser / storage）

## 1. 改造后职责划分

| 文件 | 职责 |
|---|---|
| `rag/ingest.py` | **保留且几乎不动**：`discover_documents()`、`extract_text()`、`tokenize_text()`（关键词仍需要）。删除/降级：旧的 `chunk_text()`、`build_chunks()` 中"自研切块"部分将不再被 service 调用，仅作兼容残留可删。嵌入计算函数迁至 `rag/embedder.py`。 |
| `rag/parser.py`【新】 | 将文本/元数据组装的 Document 交给 LlamaIndex `SentenceSplitter` 切块。 |
| `rag/storage.py`【新】 | Chroma + SimpleDocumentStore + IngestionPipeline 装配与持久化。 |

## 2. Document 组装（parser.py）

每个源文件产出一个 `Document`，`id_` 必须是**稳定、规范化路径键**，这是增量去重的锚点（依据 llama_index：`_handle_upserts` 用 `node.id_` 当 ref_doc_id 查 hash）：

```python
from llama_index.core import Document

def build_document(path: Path, text: str, source_type: str, doc_hash: str) -> Document:
    return Document(
        id_=canonical_path_key(path),          # 正斜杠 + 绝对路径
        text=text,
        metadata={
            "path": str(path),
            "title": path.stem,
            "source_type": source_type,
            "doc_hash": doc_hash,
        },
    )
```

- `doc_hash` = 抽取后 `text` 的 sha1（内容指纹，而非 mtime）。文本抽取规则不变时 hash 稳定 → 重复构建直接跳过、不重新嵌入。
- 用途：路径、标题、来源类型、指纹会随节点元数据自动落入 Chroma 与 docstore（SentenceSplitter 会把 Document.metadata 带入子节点）。

## 3. 分块（parser.py）

```python
from llama_index.core.node_parser import SentenceSplitter

splitter = SentenceSplitter(
    chunk_size=RAG_CHUNK_SIZE,
    chunk_overlap=RAG_CHUNK_OVERLAP,
)
```

- 行为（本地源码核验）：先按段落 `paragraph_separator` 切，再做句子边界 `secondary_chunking_regex` 与词切分合并到 `chunk_size`(token)。文档元数据自动复制到每个子节点。
- 相比旧 `chunk_text`：不再"一切从空行开始硬凑 1200 字符"，句子边界完整、语义粘连更少。

## 4. 索引存储装配（storage.py）

```python
from llama_index.core.ingestion import IngestionPipeline, DocstoreStrategy
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.vector_stores.chroma import ChromaVectorStore

def get_vector_store() -> ChromaVectorStore:
    return ChromaVectorStore.from_params(
        persist_dir=str(DEFAULT_CHROMA_DIR),
        collection_name=RAG_COLLECTION_NAME,
    )  # chromadb.PersistentClient(path=...)

def get_docstore() -> SimpleDocumentStore:
    if DEFAULT_DOCSTORE_PATH.exists():
        return SimpleDocumentStore.from_persist_path(str(DEFAULT_DOCSTORE_PATH))
    return SimpleDocumentStore()  # 内存态，run 后 persist 落盘
```

### 4.1 增量构建（核心）

```python
pipeline = IngestionPipeline(
    transformations=[splitter, config_embedding],          # 见 03 文档
    vector_store=get_vector_store(),
    docstore=get_docstore(),
    docstore_strategy=DocstoreStrategy.UPSERTS_AND_DELETE,
    disable_cache=True,    # 去重靠 docstore hash，不需要 transform cache
)
changed_nodes = pipeline.run(documents=all_current_documents)
docstore.persist(str(DEFAULT_DOCSTORE_PATH))
```

依据本地源码（pipeline.py `_handle_upserts`/`run`）的语义保证：

- 新文档：直接进 `nodes_to_run`，分块→嵌入→`vector_store.add`→`docstore.add_documents`。
- 已变更文档：先 `docstore.delete_ref_doc(ref_doc_id)` + `vector_store.delete(ref_doc_id)`（Chroma 按元数据 `document_id` 删整篇），再走完整入库。
- 未变文档：hash 相同 → 从 `nodes_to_run` 剔除，**不重新嵌入、不重复写向量**。
- `UPSERTS_AND_DELETE`：docstore 里存在但不在本次传入文档集合中的旧文档 → 从 docstore/向量库删除（即"源文件被移除"的场景）。

调用约定：**每次增量构建都传入当前全量文档列表**（发现逻辑只扫存在的文件），删除语义才成立。

## 5. 快照（keyword_index.json）重建

`service.build_index` 在 pipeline.run 之后，**从 Chroma 全量读取记录**重建快照：

```python
chunks = storage.collect_all_chunks()   # Chroma collection.get() 读回 id/metadata/document
```

实现备注（依据本地 llama_index 行为核实后修正）：
- IngestionPipeline 的 `_update_docstore` 只把 **Document** 写入 docstore（作为增量去重的 hash 登记簿），
  并不存 chunk；chunk 文本与元数据实际存于 Chroma（`stores_text=True`，查询直接还原 TextNode）。
- 因此快照以 Chroma 全量为唯一来源，chunk 的 `id` 取 Chroma 节点 id，与向量检索返回的 node_id 同源，
  混合检索按 id 融合不会出现两套编号。
- 生成的 chunk dict 与旧结构兼容（含 tokens 预分词）：
  ```python
  {
      "id": node_id,
      "path": meta["path"], "title": meta["title"], "source_type": meta["source_type"],
      "chunk_index": i, "content": text, "tokens": tokenize_text(text),
  }
  ```

纯关键词（无向量库）路径不走 Chroma：直接用 SentenceSplitter 切出的节点列表重建同一格式快照。

## 6. 纯关键词降级路径

- 嵌入不可用（本地库缺失 / API 失败 / `RAG_DISABLE_VECTOR=1`）：**跳过 pipeline**，仅用 `parser.py` 分块生成节点 → 直接构建快照。此时 `has_embeddings=False`，Chroma/docstore 不落盘。
- 这样即使环境没有 chromadb / sentence-transformers，索引构建与检索仍可用（等价旧纯关键词模式），测试可在无重依赖环境跑。

## 7. 依赖方向（防循环）

```
parser → (llama_index.core)      仅类型
storage → parser / embedder / config
service → storage / parser / embedder / ingest(发现/抽取) / config
retriever → storage / config / ingest.tokenize
```
`rag/ingest.py` 与 `rag/config_manager.py` 不 import 上层模块。
