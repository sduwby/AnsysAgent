"""RAG path configuration."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX_DIR = PROJECT_ROOT / ".rag"
DEFAULT_INDEX_PATH = DEFAULT_INDEX_DIR / "keyword_index.json"
DEFAULT_DOC_PATHS = [
    PROJECT_ROOT / "docs" / "api",
    PROJECT_ROOT / "knowledge" / "official",
    PROJECT_ROOT / "knowledge" / "internal",
]
