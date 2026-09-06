# 06 打包与测试

## 1. 测试矩阵与目标

| 级别 | 内容 | 命令 |
|---|---|---|
| 冒烟 | llama_index/chromadb 可导入、版本打印 | `python -c "import llama_index.core, chromadb; print('ok')"` |
| 关键词回归 | 无 chromadb/嵌入时构建与检索可用 | `python -m pytest tests/test_regressions.py -k "knowledge or rag or index"` |
| 向量构建+增量 | 构建→复用不重嵌→改文件只重嵌变更→删文件被清理 | 新增 `tests/test_rag_upgrade.py` |
| 检索 | vector/keyword/hybrid、source_type 过滤、rerank 开关 | 同上 |
| 全量 | 全仓回归 | `python -m pytest tests/` |

新增测试文件**沿用既有 mock 风格**（`tests/test_regressions.py` 顶部 stub 重依赖），但 RAG 向量用例允许真实 import chromadb（若未安装则 `pytest.skip`），关键词用例必须零外部依赖。

## 2. 关键行为断言（新增 test_rag_upgrade.py）

1. `build_index` 两次相同输入 → docstore 中无新增/重嵌（可比较 `get_all_document_hashes()` 不变；向量目录计数不变）。
2. 修改一个文件文本 → 第二次 build 后该 ref_doc 的 hash 更新、Chroma 删除并重建该 doc 节点，其它文档 count 不变。
3. 删除一个源文件（再次只传剩余 doc_paths）→ 该 ref_doc 从 docstore 与 Chroma 消失。
4. `source_type` 过滤只命中对应来源。
5. `retrieval_mode="hybrid"` 且向量可用时结果字段结构 = 兼容结构；embedding 不可用时等效 keyword。

## 3. PyInstaller 打包（`ansys-agent.spec` / `build.bat`）

### 3.1 原则
本项目运行期项目目录只读，知识库写入 `ANSYS_DATA_DIR/.rag`，因此**chroma/docstore 数据不能打进 exe**（它们应落在用户数据目录并持久化）。需打包的只是 llama_index/chromadb 的 Python 模块与少量原生库。

### 3.2 spec 需要补充的点（本期代码完成并冒烟后落地验证）

- `hiddenimports` 收集 llama_index 各子模块：核心用到的有 `llama_index.core.*`（node_parser、ingestion、storage.docstore、vector_stores、retrievers、indices.vector_store、base.embeddings）与 `llama_index.vector_stores.chroma`。
- chromadb 原生依赖：`chromadb` 的 telemetry/后端动态 import 较多，建议在 spec 中 `collect_submodules("chromadb")`、`collect_data_files("chromadb")` 并确认 sqlite 后端为系统可用的 pysqlite。
- 删除/排查默认 embedding function 引入的 onnxruntime：本项目始终显式传 embedding，不创建使用默认 EF 的路径；若收集过大再考虑在 collection 创建时规避。
- sentence-transformers 的模型文件不打包（下载到用户缓存）；`EMBEDDING_MODEL` 默认仍 `all-MiniLM-L6-v2`，首用联网下载——与现状一致。
- 建议用 PyInstaller `--collect-all llama_index` 起步再裁剪；因体积影响 exe 大小，正式裁剪留到打包验证阶段并同步本文档。

### 3.3 风险
- llama_index-core 依赖较多（fsspec、numpy、tenacity、tiktoken、SQLAlchemy 仅部分路径），spec 收集面变大。
- chromadb 在 Python 3.13 + PyInstaller 的组合需实测；若受阻，备选方案是向量层预留 `ChromaVectorStore` 抽象、可用 lance/sqlite-vec 替换（本期不切换，仅在文档记录后备路径）。

## 4. 依赖安装（当前开发机 Python 3.13.1）

```bash
python -m pip install "llama-index-core" "llama-index-vector-stores-chroma" "chromadb"
python -m pip install -e ".[rag,dev]"
```

版本对齐以 PyPI 最新稳定为准；本仓库克隆仅供源码对照，不作为安装源。

## 5. 文档同步纪律

实现过程中若发现 llama_index 行为与本目录文档不一致：
1. 到 `D:\FittenProject\llama_index` 克隆源码定位对应实现；
2. 回填修改本文档（含源码文件:行号）；
3. 再继续实现，避免文档与代码漂移。
