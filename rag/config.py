"""RAG path configuration."""

from __future__ import annotations

import sys
from pathlib import Path

from agent.paths import ANSYS_DATA_DIR

# RAG 索引统一写到 ANSYS_DATA_DIR/.rag（跨模式一致）
DEFAULT_INDEX_DIR = ANSYS_DATA_DIR / ".rag"
DEFAULT_INDEX_PATH = DEFAULT_INDEX_DIR / "keyword_index.json"

if getattr(sys, "frozen", False):
    # PyInstaller 打包环境
    # sys._MEIPASS: 内置资源解压目录（只读，随进程临时）
    # sys.executable parent: exe 所在目录（可写，用户可扩展）
    _BUNDLE_DIR = Path(sys._MEIPASS)          # type: ignore[attr-defined]
    _EXE_DIR = Path(sys.executable).parent

    DEFAULT_DOC_PATHS: list[Path] = [
        # 内置知识：随 exe 打包，开箱即用（只读）
        _BUNDLE_DIR / "docs" / "api",
        _BUNDLE_DIR / "knowledge" / "official",
        # 用户自定义知识：放在 exe 同级 knowledge/ 目录，随时增删（可写）
        _EXE_DIR / "knowledge" / "official",
        _EXE_DIR / "knowledge" / "internal",
    ]
else:
    # 开发环境
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DEFAULT_DOC_PATHS = [
        _PROJECT_ROOT / "docs" / "api",
        _PROJECT_ROOT / "knowledge" / "official",
        _PROJECT_ROOT / "knowledge" / "internal",
    ]
