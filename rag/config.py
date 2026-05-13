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
