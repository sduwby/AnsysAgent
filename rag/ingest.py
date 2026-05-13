"""Knowledge ingestion and chunking with vector embedding."""

from __future__ import annotations

import json
import logging
import re
import time
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path

import httpx

from rag.config import (
    EMBEDDING_PROVIDER,
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    SILICONFLOW_EMBEDDING_MODEL,
)
from rag.config_manager import get_provider_config, read_env_file

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    _LOCAL_EMBEDDING_AVAILABLE = True
except ImportError:
    _LOCAL_EMBEDDING_AVAILABLE = False

_log = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".md", ".txt", ".rst", ".json", ".pdf", ".ipynb", ".py", ".pptx"}
_IGNORED_NAMES = {".ds_store", "__pycache__"}

_embedding_model = None

_SILICONFLOW_BATCH_SIZE = 64
_SILICONFLOW_MAX_RETRIES = 3
_SILICONFLOW_RETRY_DELAY = 1.0


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    global _embedding_model
    if _embedding_model is None:
        if not _LOCAL_EMBEDDING_AVAILABLE:
            raise ImportError("请安装 sentence-transformers 和 numpy: pip install sentence-transformers numpy")
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def compute_embeddings_local(texts: list[str], model_name: str = "all-MiniLM-L6-v2") -> list[list[float]]:
    model = get_embedding_model(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def compute_embeddings_siliconflow(
    texts: list[str],
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> list[list[float]]:
    key = api_key or SILICONFLOW_API_KEY
    url = (base_url or SILICONFLOW_BASE_URL).rstrip("/") + "/embeddings"
    model_name = model or SILICONFLOW_EMBEDDING_MODEL

    if not key:
        raise ValueError("SiliconFlow API Key 未配置，请设置 SILICONFLOW_API_KEY 环境变量")

    all_embeddings: list[list[float]] = []
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    for batch_start in range(0, len(texts), _SILICONFLOW_BATCH_SIZE):
        batch = texts[batch_start:batch_start + _SILICONFLOW_BATCH_SIZE]
        payload = {
            "model": model_name,
            "input": batch,
        }

        for attempt in range(_SILICONFLOW_MAX_RETRIES):
            try:
                resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
                resp.raise_for_status()
                data = resp.json()

                if "data" not in data:
                    raise ValueError(f"SiliconFlow API 返回格式异常: {list(data.keys())}")

                sorted_data = sorted(data["data"], key=lambda x: x.get("index", 0))
                batch_embeddings = [item["embedding"] for item in sorted_data]
                all_embeddings.extend(batch_embeddings)
                break

            except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
                if attempt < _SILICONFLOW_MAX_RETRIES - 1:
                    wait = _SILICONFLOW_RETRY_DELAY * (2 ** attempt)
                    _log.warning("SiliconFlow 嵌入请求失败 (第%d次重试): %s", attempt + 1, exc)
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"SiliconFlow 嵌入请求失败 (已重试{_SILICONFLOW_MAX_RETRIES}次): {exc}") from exc

    return all_embeddings


def compute_embeddings_api(
    texts: list[str],
    api_key: str,
    base_url: str,
    model: str,
) -> list[list[float]]:
    """
    通用的嵌入 API 调用函数，支持任意符合 OpenAI 格式的嵌入服务
    
    参数:
        texts: 要嵌入的文本列表
        api_key: API Key
        base_url: API 基础 URL
        model: 模型名称
    
    返回:
        嵌入向量列表
    """
    if not api_key:
        raise ValueError("API Key 未配置")

    url = base_url.rstrip("/") + "/embeddings"
    all_embeddings: list[list[float]] = []
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for batch_start in range(0, len(texts), _SILICONFLOW_BATCH_SIZE):
        batch = texts[batch_start:batch_start + _SILICONFLOW_BATCH_SIZE]
        payload = {
            "model": model,
            "input": batch,
        }

        for attempt in range(_SILICONFLOW_MAX_RETRIES):
            try:
                resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
                resp.raise_for_status()
                data = resp.json()

                if "data" not in data:
                    raise ValueError(f"API 返回格式异常: {list(data.keys())}")

                sorted_data = sorted(data["data"], key=lambda x: x.get("index", 0))
                batch_embeddings = [item["embedding"] for item in sorted_data]
                all_embeddings.extend(batch_embeddings)
                break

            except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
                if attempt < _SILICONFLOW_MAX_RETRIES - 1:
                    wait = _SILICONFLOW_RETRY_DELAY * (2 ** attempt)
                    _log.warning("嵌入请求失败 (第%d次重试): %s", attempt + 1, exc)
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"嵌入请求失败 (已重试{_SILICONFLOW_MAX_RETRIES}次): {exc}") from exc

    return all_embeddings


def compute_embeddings(
    texts: list[str],
    model_name: str = "all-MiniLM-L6-v2",
    provider: str = "",
) -> list[list[float]]:
    embed_provider = provider or EMBEDDING_PROVIDER

    if embed_provider == "siliconflow":
        sf_model = model_name if model_name != "all-MiniLM-L6-v2" else SILICONFLOW_EMBEDDING_MODEL
        return compute_embeddings_siliconflow(texts, model=sf_model)
    elif embed_provider == "local":
        if not _LOCAL_EMBEDDING_AVAILABLE:
            raise ImportError(
                "本地嵌入不可用，请安装 sentence-transformers: pip install sentence-transformers numpy\n"
                "或切换到远程提供商"
            )
        return compute_embeddings_local(texts, model_name)
    else:
        # 自定义提供商
        provider_config = get_provider_config(embed_provider)
        if not provider_config:
            raise ValueError(f"未知提供商: {embed_provider}")
        
        env = read_env_file()
        prefix = f"CUSTOM_PROVIDER_{embed_provider.upper()}"
        api_key = env.get(f"{prefix}_API_KEY", "")
        base_url = env.get(f"{prefix}_BASE_URL", "")
        model = env.get(f"{prefix}_MODEL", model_name)
        
        if not api_key:
            raise ValueError(f"提供商 {embed_provider} 的 API Key 未配置")
        if not base_url:
            raise ValueError(f"提供商 {embed_provider} 的基础 URL 未配置")
        
        return compute_embeddings_api(texts, api_key, base_url, model)


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


def build_chunks(
    doc_paths: list[str | Path],
    with_embeddings: bool = False,
    model_name: str = "all-MiniLM-L6-v2",
    embedding_provider: str = "",
) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    chunks: list[dict] = []
    for document in discover_documents(doc_paths):
        text, doc_warnings = extract_text(document)
        warnings.extend(f"{document}: {warning}" for warning in doc_warnings)
        for chunk_index, content in enumerate(chunk_text(text), start=1):
            chunk = {
                "id": f"{document.as_posix()}#{chunk_index}",
                "path": str(document),
                "title": document.stem,
                "source_type": guess_source_type(document),
                "chunk_index": chunk_index,
                "content": content,
                "tokens": tokenize_text(content),
            }
            chunks.append(chunk)

    if with_embeddings and chunks:
        provider = embedding_provider or EMBEDDING_PROVIDER
        can_embed = (provider == "siliconflow") or _LOCAL_EMBEDDING_AVAILABLE
        if can_embed:
            try:
                contents = [chunk["content"] for chunk in chunks]
                embeddings = compute_embeddings(contents, model_name=model_name, provider=provider)
                for i, chunk in enumerate(chunks):
                    chunk["embedding"] = embeddings[i]
            except Exception as exc:
                warnings.append(f"向量嵌入计算失败 ({provider}): {exc}")
        else:
            warnings.append("向量嵌入不可用：未安装 sentence-transformers 且未配置 SiliconFlow")

    return chunks, warnings
