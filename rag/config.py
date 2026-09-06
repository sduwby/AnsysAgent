"""RAG path configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from agent.paths import ANSYS_DATA_DIR

# RAG 索引统一写到 ANSYS_DATA_DIR/.rag（跨模式一致）
DEFAULT_INDEX_DIR = ANSYS_DATA_DIR / ".rag"
DEFAULT_INDEX_PATH = DEFAULT_INDEX_DIR / "keyword_index.json"

# 向量索引路径
DEFAULT_VECTOR_INDEX_PATH = DEFAULT_INDEX_DIR / "vector_index.faiss"

# 嵌入模型配置：优先从环境变量读取，默认为 all-MiniLM-L6-v2
DEFAULT_EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# 嵌入提供商配置
# 支持 "local"（本地 sentence-transformers）和 "siliconflow"（硅基流动 API）
EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "local")

# 硅基流动 API 配置
SILICONFLOW_API_KEY = os.environ.get("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
SILICONFLOW_EMBEDDING_MODEL = os.environ.get("SILICONFLOW_EMBEDDING_MODEL", "BAAI/bge-m3")

HYBRID_VECTOR_WEIGHT = float(os.environ.get("RAG_HYBRID_VECTOR_WEIGHT", "0.6"))
HYBRID_KEYWORD_WEIGHT = float(os.environ.get("RAG_HYBRID_KEYWORD_WEIGHT", "0.4"))

# ------------------------------------------------------------
# LlamaIndex 内核配置（RAG 2.0，schema 版本用于旧缓存自动迁移）
# ------------------------------------------------------------

# 快照 schema/引擎版本；与 keyword_index.json 中的 schema_version 不匹配时触发一次自动重建
RAG_SCHEMA_VERSION = os.environ.get("RAG_SCHEMA_VERSION", "llamaindex-1")

# 强制走纯关键词模式（排障开关）
RAG_DISABLE_VECTOR = os.environ.get("RAG_DISABLE_VECTOR", "") == "1"

# Chroma 本地持久化目录与 collection
DEFAULT_CHROMA_DIR = DEFAULT_INDEX_DIR / "chroma"
DEFAULT_DOCSTORE_PATH = DEFAULT_INDEX_DIR / "docstore.json"
RAG_COLLECTION_NAME = os.environ.get("RAG_COLLECTION_NAME", "ansys_knowledge")

# 分块参数（单位：token，SentenceSplitter 的 chunk_size / chunk_overlap）
RAG_CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "512"))
RAG_CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "50"))

# 召回池倍率：每路先取 top_k × N 个候选再做融合/重排/截断
RAG_TOP_K_CANDIDATES = int(os.environ.get("RAG_TOP_K_CANDIDATES", "2"))

# 可选重排（SiliconFlow /rerank）。模型为空 = 关闭。
RAG_RERANK_MODEL = os.environ.get("RAG_RERANK_MODEL", "")
RAG_RERANK_BASE_URL = os.environ.get(
    "RAG_RERANK_BASE_URL", "https://api.siliconflow.cn/v1/rerank"
)

USER_KNOWLEDGE_DIR = ANSYS_DATA_DIR / "knowledge"
USER_OFFICIAL_DOC_DIR = USER_KNOWLEDGE_DIR / "official"
USER_INTERNAL_DOC_DIR = USER_KNOWLEDGE_DIR / "internal"

if getattr(sys, "frozen", False):
    # PyInstaller 打包环境
    # sys._MEIPASS: 内置资源解压目录（只读，随进程临时）
    _BUNDLE_DIR = Path(sys._MEIPASS)          # type: ignore[attr-defined]

    DEFAULT_DOC_PATHS: list[Path] = [
        # 内置知识：随 exe 打包，开箱即用（只读）
        _BUNDLE_DIR / "docs" / "api",
        _BUNDLE_DIR / "knowledge" / "official",
        # 用户自定义知识：统一放在 ANSYS_DATA_DIR/knowledge/ 下
        USER_OFFICIAL_DOC_DIR,
        USER_INTERNAL_DOC_DIR,
    ]
else:
    # 开发环境
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DEFAULT_DOC_PATHS = [
        _PROJECT_ROOT / "docs" / "api",
        _PROJECT_ROOT / "knowledge" / "official",
        _PROJECT_ROOT / "knowledge" / "internal",
        USER_OFFICIAL_DOC_DIR,
        USER_INTERNAL_DOC_DIR,
    ]
