# AnsysAgent RAG 系统 LlamaIndex 化总改造文档

> 状态：已定稿（实现阶段按 llama_index 源码核查后如有出入会回填本目录文档）
> 参考源码：llama_index 已浅克隆到 `D:\FittenProject\llama_index`（`--depth 1`，跑 `main` 分支）
> 适用提交：2026-09-06

## 1. 背景与目标

### 1.1 现状（改造前）

本项目自带进程内 RAG（`rag/` 包），技术栈为纯自研 JSON 方案：

- 索引：一次全量扫描 `docs/api`、`knowledge/official`、`knowledge/internal`（含用户目录），文本解析后按"空行聚合段落 + 1200 字符固定窗口/120 重叠"切块，写入 `~/.AnsysAgent/.rag/keyword_index.json`（chunk 原文 + tokens + 可选 embedding 全量塞进一个 JSON）。
- 检索：自定义字符打分（关键词）+ numpy 逐条余弦（向量），双路 top_k×2 后按 0.6/0.4 权重直接相加再取 top_k。
- 向量：`all-MiniLM-L6-v2`（本地 sentence-transformers）或 SiliconFlow `BAAI/bge-m3`（OpenAI 兼容 `/embeddings`），无向量库，无重排。
- 触发：`chat_agent` 关键词命中 → `search_index()` → 拼成 system 消息。

痛点（用户确认）：检索召回不准、文档解析弱（表格/扫描 PDF）、新增文档要删缓存全量重建、索引规模大后单 JSON + 全量余弦性能差。

### 1.2 目标（改造后）

采用 llama_index 作为 RAG 内核，替换自研"分块/嵌入/向量检索"实现，但**保持对外薄壳 API 不变**：

1. 检索质量：真向量库（Chroma HNSW）+ LlamaIndex 检索链路 + 可选重排（SiliconFlow bge-reranker）。
2. 解析能力：分段（SentenceSplitter）保留段落/句子边界；PDF 可切换更强解析器（后续可按 `RAG_PDF_PARSER` 接入 LlamaParse/PyMuPDF），先保持本地解析稳定可控。
3. 增量：借鉴 IngestionPipeline 的 `UPSERTS_AND_DELETE` 语义——按文档内容 hash 判增/改/删，只对变更文档重嵌入，启动不再是全量重建。
4. 规模/性能：向量检索交给 Chroma（无需常驻服务，单进程本地持久化目录），检索不再全量扫内存 JSON；关键词仍走轻量快照内存搜索（数百文档规模足够）。

### 1.3 非目标（本期不做）

- 不引入 LlamaIndex 的 Agent / Workflow / QueryEngine 编排层（本项目已有 OmAgentWorkflow，避免两套编排打架）。
- 不引入 LlamaCloud / LlamaParse 云依赖（解析保持本地，表格/扫描场景以可选开关方式预留）。
- 不改 `chat_agent` / `knowledge_tools` / `/embed` 命令的对外行为。

## 2. 目标架构

```
main.py (CLI + /commands) / tests
   └─ chat_agent / knowledge_tools / tools.embedding_config_tool
        │  调用原有薄壳 API（签名不变）
        ▼
rag/ 薄壳层（对外兼容，绝不外泄 llama 对象）
   ├─ config.py          路径/环境变量/常量（新增 RAG_* 开关）
   ├─ config_manager.py  保留：/embed 提供商配置（local/siliconflow/自定义）
   ├─ service.py         build_index / load_index / search_index（兼容返回结构）
   ├─ ingest.py          保留：文档发现 discover_documents() 与文本抽取 extract_text()
   ├─ parser.py          【新】LlamaIndex SentenceSplitter 参数化封装
   ├─ embedder.py        【新】BaseEmbedding 子类，桥接现有双通道计算
   ├─ storage.py         【新】Chroma + SimpleDocumentStore + IngestionPipeline 装配
   ├─ retriever.py       改写：keyword / vector / hybrid 三路 + 结果映射
   └─ reranker.py        【新】可选 SiliconFlow 重排（BaseNodePostprocessor 子类）
```

### 数据流（一次增量构建）

```
发现文档(discover_documents, 保留)
   → 逐文件抽取文本(extract_text, 保留)
   → Document(id_=canonical_path, metadata={path,title,source_type,doc_hash})
   → IngestionPipeline.run(documents)          # UPSERTS_AND_DELETE + SimpleDocumentStore
        ├─ 未变文档：docstore hash 相同 → 跳过（不重新嵌入）
        ├─ 新增/变更：delete_ref_doc 旧节点 → SentenceSplitter 分块 → ConfigEmbedding 嵌入
        │            → ChromaVectorStore.add / docstore 更新
        └─ 已删除文档：docstore 中不在本轮清单者 → 同步删除向量与元数据
   → 从 docstore 汇总全量节点 → 重建 keyword_index.json（兼容快照 + 状态清单）
```

### 数据流（一次查询）

```
search_index(query, top_k, source_type, retrieval_mode)
   ├─ vector  :  embed_model 编码 query → VectorIndexRetriever(similarity_top_k=top_k×2)
   ├─ keyword :  快照内存打分（沿用现有 tokenize/score 逻辑，保持可离线）
   └─ hybrid  :  双路召回 → 0.6/0.4 融合（配置不变）
   → [可选 SiliconFlowRerank 重排] → 截断 top_k → 统一 result item 字段
```

## 3. 存储布局（~/.AnsysAgent/.rag/）

| 路径 | 用途 | 引擎 |
|---|---|---|
| `keyword_index.json` | 兼容快照 + 状态清单（含 chunks 原文与 tokens，供关键词搜索/计数/UI 展示） | 本项目 |
| `chroma/` | Chroma 本地持久化目录（向量 + 元数据 + 文本） | chromadb |
| `docstore.json` | llama_index SimpleDocumentStore 持久化（ref_doc 映射、节点 hash、节点内容） | llama_index |

说明：
- Chroma 存向量+元数据+文本（stores_text=True），docstore 仅登记 Document（ref_doc/hash）用于增量去重。
- **快照每次完整重建自 Chroma 全量记录**（本实现已核实：llama_index IngestionPipeline 的 docstore 只存
  Document 不存 chunk，故 keyword_index.json 从 Chroma 读回全部节点重建，保证与向量检索结果同源）。
  快照是我们为"关键词离线检索 + 既有调用方契约"保留的一层副本，不承担向量职责。
- 兼容性：`.gitignore` 已忽略 `.rag/`；`keyword_index.json` 仍在既有路径，`knowledge_tools` 与 `main.py` 帮助文案无需改路径。

## 4. llama_index 关键机制核验（依据本地源码）

以下结论均摘自克隆源码（实现阶段如遇出入以此为准继续查源码再回填本表）：

1. **ChromaVectorStore**（`llama-index-integrations/vector_stores/llama-index-vector-stores-chroma/llama_index/vector_stores/chroma/base.py`）
   - `from_params(persist_dir=..., collection_name=...)` → `chromadb.PersistentClient(path=persist_dir)`，本地无服务。
   - `stores_text = True`：节点文本与元数据都进 Chroma，查询直接还原 `TextNode`，无需回查 docstore。
   - 相似度：Chroma 返回距离，`math.exp(-distance)` 转成 [0,1] 相似度。
   - `delete(ref_doc_id)` 按元数据 `document_id == ref_doc_id` 删除整篇文档节点。
2. **IngestionPipeline 增量语义**（`llama-index-core/.../ingestion/pipeline.py`）
   - 官方构形：`transformations=[SentenceSplitter(...), Embedding()]`，`run(documents=...)`。
   - `_handle_upserts`：`ref_doc_id = node.ref_doc_id or node.id_`；对每个输入 Document 查 `docstore.get_document_hash(ref_doc_id)`；不存在 → 入库；存在但 hash 不同 → `docstore.delete_ref_doc` + `vector_store.delete(ref_doc_id)` 后重跑；hash 相同 → 直接跳过（**不会重复嵌入**）。
   - `DocstoreStrategy.UPSERTS_AND_DELETE`：额外把 docstore 中存在但本轮输入中缺失的文档从 docstore 与向量库删除。
   - hash 由节点内容决定 → 文本抽取结果稳定，则重复构建不产生嵌入开销。
3. **SentenceSplitter**（`.../node_parser/text/sentence.py`）
   - 默认 `chunk_size=DEFAULT_CHUNK_SIZE=1024`（token）、`chunk_overlap=DEFAULT_CHUNK_OVERLAP=20`、段落分隔 `\n\n\n`、句子边界正则二次切分；按文档切分时把 Document 的 metadata 带入子节点。
   - 本项目将用环境变量覆盖为更适合检索文档的粒度（见 01 配置文档）。
4. **重排基类** `BaseNodePostprocessor`（`.../postprocessor/types.py`）：实现 `_postprocess_nodes(nodes, query_bundle)` 即可；官方 SiliconFlow 集成 `SiliconFlowRerank`（`llama-index-postprocessor-siliconflow-rerank`）调用 `POST /v1/rerank`，本项目将内嵌等价实现（httpx，避免引入 requests 与额外集成包依赖）。

## 5. 兼容性契约（必须保持）

| 契约 | 出处 | 要求 |
|---|---|---|
| `rag.service.build_index()` 返回 dict | tools/knowledge_tools.py、tests | 键：built_at/doc_paths/num_chunks/chunks/warnings/embedding_model/embedding_provider/has_embeddings |
| `rag.service.search_index()` 返回 dict | chat_agent / knowledge_tools / tests | 键：query/top_k/source_type/index_path/num_chunks/retrieval_mode/has_embeddings/embedding_provider/results/warnings；results 元素含 source_type/title/path/score/snippet/id/chunk_index |
| `rag.ingest.discover_documents()` | tests/test_regressions | 跳隐藏文件/隐藏目录行为不变 |
| `rag.config_manager.*` | main.py `/embed`、tools/embedding_config_tool.py | provider/model/key/url 配置接口不变 |
| `chat_agent._build_knowledge_context/_should_use_knowledge` | tests | 触发词、system 注入、跳过执行型消息逻辑不变（不改 chat_agent.py） |
| `DEFAULT_INDEX_PATH` 文件存在性语义 | tests / main.py 帮助 | 构建后 `keyword_index.json` 必须真实存在；删除即触发下次重建 |
| 降级路径 | 既有行为 | 无 sentence-transformers / 无 chromadb / 嵌入调用失败时，自动退化为"纯关键词快照"模式，search 不抛错 |

## 6. 实施顺序

1. 依赖与配置（pyproject/requirements/env 新增 RAG_* 开关）→ `01_config_and_env.md`
2. 摄取与索引（parser/storage/service.build_index 增量）→ `02_ingest_and_index.md`
3. Embedding 桥接 → `03_embedding.md`
4. 检索与重排 → `04_retrieval_and_rerank.md`
5. 薄壳 service/search 兼容层整合 → `05_service_api.md`
6. 打包与测试 → `06_packaging_and_tests.md`

每步实现前对照对应分模块文档；**实现中若发现 llama_index 行为与文档描述不符，先到本地克隆源码确认，再回填文档后继续**。

## 7. 风险与回滚

- **Python 3.13 兼容**：chromadb / llama-index-core 需在 3.13 可安装（实施时先做 `pip install` 冒烟）。
- **打包体积与 hook**：llama_index/chromadb 依赖较重，PyInstaller 需补充 hidden-import 与数据收集，见 06 文档（本期先保源码运行与测试，spec 修改随后验证）。
- **模型切换**：索引嵌入模型与查询嵌入模型必须一致；快照会记录 `embedding_model`，运行期检测到变更仅告警不自动重建（避免无感消耗）。
- **回滚**：所有对外 API 不变；回滚 = 还原 `rag/` 目录即可。删除 `.rag/chroma` 与 `docstore.json`（或整体删除 `.rag`）即回到"下次启动全量重建"路径，不会残留脏数据。
