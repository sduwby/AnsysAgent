"""
Memory 管理器：提供持久化文件记忆、入口索引和相关记忆检索。

参考 memdir 设计，采用：
1. `memory/MEMORY.md` 作为入口索引
2. 每条记忆一个 Markdown 文件，带简单 frontmatter
3. 对当前 query 进行轻量相关性检索，向模型注入最相关的记忆
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agent.logger import get_logger
from agent.paths import ANSYS_DATA_DIR

_log = get_logger("memory_manager")

MEMORY_DIR: Path = ANSYS_DATA_DIR / "memory"
MEMORY_ENTRYPOINT: Path = MEMORY_DIR / "MEMORY.md"
MEMORY_TYPES: tuple[str, ...] = ("user", "feedback", "project", "reference")
MAX_ENTRYPOINT_LINES = 200
MAX_ENTRYPOINT_BYTES = 25_000
MAX_RELEVANT_MEMORIES = 5

_MEMORY_GUIDANCE = """## 持久记忆系统

你有一个持久化、基于文件的记忆系统，目录位于 `ANSYS_DATA_DIR/memory/`。

- `MEMORY.md` 是记忆入口索引，不保存完整内容，只保存主题入口和一行摘要
- 每条具体记忆保存在单独的 `.md` 文件中，包含 frontmatter：`name` / `type` / `description`
- 仅保存不能从当前代码、当前项目文件、git 历史直接推导出的信息
- 优先保存四类记忆：
  - `user`：用户规则、偏好、知识背景、沟通习惯
  - `feedback`：用户确认有效或明确纠正过的工作方式
  - `project`：项目中的隐含背景、截止日期、协作约束、决策原因
  - `reference`：外部系统入口、看板、文档、仪表盘等查找线索
- 不要保存当前会话里的临时任务状态、代码结构、文件路径罗列、可以重新读出来的实现细节
- 当用户明确要求“记住”“保存经验”“记录偏好”时，应优先考虑调用 memory 工具
- 当当前问题明显与已保存记忆有关时，应参考相关记忆，但若与当前真实状态冲突，以当前状态为准，并更新旧记忆
"""


def _sanitize_name(name: str) -> str:
    safe = name.strip().lower()
    safe = re.sub(r"[^a-z0-9\u4e00-\u9fff\-_]", "-", safe)
    safe = re.sub(r"-+", "-", safe).strip("-")
    return safe or "memory"


def _memory_path(name: str) -> Path:
    return MEMORY_DIR / f"{_sanitize_name(name)}.md"


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text.strip()
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text.strip()
    header, body = parts
    lines = header.splitlines()[1:]
    data: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data, body.strip()


def _build_frontmatter(name: str, memory_type: str, description: str) -> str:
    return (
        "---\n"
        f"name: {name.strip()}\n"
        f"type: {memory_type.strip()}\n"
        f"description: {description.strip()}\n"
        "---\n\n"
    )


def _strip_frontmatter(text: str) -> str:
    _, body = _parse_frontmatter(text)
    return body


def _tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in re.findall(r"[a-z0-9\u4e00-\u9fff_+-]{2,}", text.lower()):
        if len(token) < 2:
            continue
        tokens.add(token)
        if re.search(r"[\u4e00-\u9fff]", token):
            for i in range(len(token) - 1):
                tokens.add(token[i:i + 2])
    return tokens


@dataclass
class MemoryRecord:
    name: str
    path: Path
    memory_type: str
    description: str
    content: str
    mtime: float


class MemoryManager:
    def __init__(self) -> None:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        if not MEMORY_ENTRYPOINT.exists():
            MEMORY_ENTRYPOINT.write_text(
                "# Memory Index\n\n"
                "在这里记录记忆索引，每行一个主题入口，格式：\n"
                "- [标题](file.md) - 一行摘要\n",
                encoding="utf-8",
            )

    def list_memories(self) -> list[MemoryRecord]:
        records: list[MemoryRecord] = []
        for path in sorted(MEMORY_DIR.glob("*.md")):
            if path.name == MEMORY_ENTRYPOINT.name:
                continue
            try:
                raw = path.read_text(encoding="utf-8")
            except OSError:
                continue
            meta, body = _parse_frontmatter(raw)
            stat = path.stat()
            records.append(
                MemoryRecord(
                    name=meta.get("name", path.stem),
                    path=path,
                    memory_type=meta.get("type", ""),
                    description=meta.get("description", ""),
                    content=body,
                    mtime=stat.st_mtime,
                )
            )
        records.sort(key=lambda item: item.mtime, reverse=True)
        return records

    def get_memory(self, name: str) -> Optional[MemoryRecord]:
        path = _memory_path(name)
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        stat = path.stat()
        return MemoryRecord(
            name=meta.get("name", path.stem),
            path=path,
            memory_type=meta.get("type", ""),
            description=meta.get("description", ""),
            content=body,
            mtime=stat.st_mtime,
        )

    def save_memory(
        self,
        name: str,
        content: str,
        memory_type: str,
        description: str,
        update_index: bool = True,
    ) -> tuple[bool, str]:
        safe_name = _sanitize_name(name)
        memory_type = memory_type.strip().lower()
        if memory_type not in MEMORY_TYPES:
            return False, f"无效 memory type: {memory_type}，可选值: {', '.join(MEMORY_TYPES)}"
        if not content.strip():
            return False, "memory 内容不能为空"
        if not description.strip():
            return False, "memory 描述不能为空"

        path = _memory_path(safe_name)
        raw = _build_frontmatter(safe_name, memory_type, description) + content.strip() + "\n"
        path.write_text(raw, encoding="utf-8")
        if update_index:
            self._upsert_index_entry(safe_name, description)
        _log.info("已保存 memory: %s (%s)", safe_name, memory_type)
        return True, f"memory '{safe_name}' 已保存"

    def delete_memory(self, name: str, remove_from_index: bool = True) -> tuple[bool, str]:
        path = _memory_path(name)
        if not path.exists():
            return False, f"memory '{_sanitize_name(name)}' 不存在"
        path.unlink()
        if remove_from_index:
            self._remove_index_entry(path.name)
        _log.info("已删除 memory: %s", path.stem)
        return True, f"memory '{path.stem}' 已删除"

    def get_entrypoint_content(self) -> str:
        raw = MEMORY_ENTRYPOINT.read_text(encoding="utf-8").strip()
        lines = raw.splitlines()
        truncated = "\n".join(lines[:MAX_ENTRYPOINT_LINES]).strip()
        if len(truncated.encode("utf-8")) > MAX_ENTRYPOINT_BYTES:
            encoded = truncated.encode("utf-8")[:MAX_ENTRYPOINT_BYTES]
            truncated = encoded.decode("utf-8", errors="ignore").rstrip()
        return truncated

    def build_memory_context(self, query: str) -> str:
        parts = [_MEMORY_GUIDANCE.strip(), "", "## MEMORY.md 入口索引", self.get_entrypoint_content()]
        relevant = self.find_relevant_memories(query)
        if relevant:
            parts.extend(["", "## 与当前问题最相关的记忆"])
            for idx, item in enumerate(relevant, start=1):
                parts.append(
                    f"{idx}. {item.name} ({item.memory_type or 'unknown'}) | "
                    f"{item.path.name} | {item.description}"
                )
                parts.append(item.content[:1200].strip())
        return "\n".join(parts).strip()

    def find_relevant_memories(self, query: str, top_k: int = MAX_RELEVANT_MEMORIES) -> list[MemoryRecord]:
        tokens = _tokenize(query)
        if not tokens:
            return []
        scored: list[tuple[int, float, MemoryRecord]] = []
        for item in self.list_memories():
            haystack = " ".join([item.name, item.description, item.content[:800]])
            item_tokens = _tokenize(haystack)
            score = len(tokens & item_tokens)
            if score <= 0:
                continue
            scored.append((score, item.mtime, item))
        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [item for _, _, item in scored[:top_k]]

    def _upsert_index_entry(self, safe_name: str, description: str) -> None:
        entry = f"- [{safe_name}]({safe_name}.md) - {description.strip()}"
        lines = MEMORY_ENTRYPOINT.read_text(encoding="utf-8").splitlines()
        kept: list[str] = []
        replaced = False
        for line in lines:
            if f"({safe_name}.md)" in line:
                kept.append(entry)
                replaced = True
            else:
                kept.append(line)
        if not replaced:
            if kept and kept[-1].strip():
                kept.append("")
            kept.append(entry)
        MEMORY_ENTRYPOINT.write_text("\n".join(kept).strip() + "\n", encoding="utf-8")

    def _remove_index_entry(self, filename: str) -> None:
        lines = MEMORY_ENTRYPOINT.read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if f"({filename})" not in line]
        MEMORY_ENTRYPOINT.write_text("\n".join(kept).strip() + "\n", encoding="utf-8")
