"""Knowledge ingestion and chunking."""

from __future__ import annotations

import json
import re
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path


SUPPORTED_SUFFIXES = {".md", ".txt", ".rst", ".json", ".pdf", ".ipynb", ".py", ".pptx"}
_IGNORED_NAMES = {".ds_store", "__pycache__"}


def discover_documents(doc_paths: list[str | Path]) -> list[Path]:
    documents: list[Path] = []
    for raw_path in doc_paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        if any(part.lower() in _IGNORED_NAMES for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and not path.name.startswith("."):
            documents.append(path)
            continue
        if path.is_dir():
            for file_path in sorted(path.rglob("*")):
                if any(part.lower() in _IGNORED_NAMES for part in file_path.parts):
                    continue
                if file_path.name.startswith("."):
                    continue
                if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_SUFFIXES:
                    documents.append(file_path)
    return documents


def _extract_notebook_text(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        notebook = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception as exc:
        return "", [f"notebook 解析失败: {exc}"]
    parts: list[str] = []
    for cell in notebook.get("cells", []):
        source = cell.get("source", [])
        if isinstance(source, list):
            text = "".join(source).strip()
        else:
            text = str(source).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts), warnings


def _extract_pptx_text(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    slides_text: list[str] = []
    namespace = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    try:
        with zipfile.ZipFile(path) as archive:
            slide_names = sorted(
                name for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            )
            for slide_name in slide_names:
                xml_data = archive.read(slide_name)
                root = ET.fromstring(xml_data)
                texts = [node.text.strip() for node in root.findall(".//a:t", namespace) if node.text and node.text.strip()]
                if texts:
                    slides_text.append("\n".join(texts))
    except Exception as exc:
        warnings.append(f"PPTX 提取失败: {exc}")
        return "", warnings
    return "\n\n".join(slides_text), warnings


def extract_text(path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".rst", ".py"}:
        return path.read_text(encoding="utf-8", errors="ignore"), warnings
    if suffix == ".ipynb":
        return _extract_notebook_text(path)
    if suffix == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            return json.dumps(data, ensure_ascii=False, indent=2), warnings
        except Exception as exc:
            warnings.append(f"JSON 解析失败: {exc}")
            return path.read_text(encoding="utf-8", errors="ignore"), warnings
    if suffix == ".pptx":
        return _extract_pptx_text(path)
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception:
            warnings.append("未安装 pypdf，PDF 文本暂未提取")
            return "", warnings
        try:
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text, warnings
        except Exception as exc:
            warnings.append(f"PDF 提取失败: {exc}")
            return "", warnings
    return "", warnings


def guess_source_type(path: Path) -> str:
    normalized = "/".join(path.parts).lower()
    if "/docs/api/" in normalized:
        return "api"
    if "/knowledge/official/" in normalized:
        return "official"
    if "/knowledge/internal/" in normalized:
        return "internal"
    if "faq" in normalized:
        return "faq"
    if "workflow" in normalized or "best_practice" in normalized:
        return "workflow"
    if "manual" in normalized or "help" in normalized:
        return "manual"
    return "document"


def tokenize_text(text: str) -> list[str]:
    ascii_words = re.findall(r"[A-Za-z0-9_./:-]+", text.lower())
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", text)
    return ascii_words + cjk_chars


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 120) -> list[str]:
    clean_text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not clean_text:
        return []
    paragraphs = [part.strip() for part in clean_text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            current = paragraph
            continue
        start = 0
        step = max(1, chunk_size - overlap)
        while start < len(paragraph):
            chunks.append(paragraph[start:start + chunk_size].strip())
            start += step
        current = ""
    if current:
        chunks.append(current)
    return chunks


def build_chunks(doc_paths: list[str | Path]) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    chunks: list[dict] = []
    for document in discover_documents(doc_paths):
        text, doc_warnings = extract_text(document)
        warnings.extend(f"{document}: {warning}" for warning in doc_warnings)
        for chunk_index, content in enumerate(chunk_text(text), start=1):
            chunks.append({
                "id": f"{document.as_posix()}#{chunk_index}",
                "path": str(document),
                "title": document.stem,
                "source_type": guess_source_type(document),
                "chunk_index": chunk_index,
                "content": content,
                "tokens": tokenize_text(content),
            })
    return chunks, warnings
