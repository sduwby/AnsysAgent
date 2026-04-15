"""Terminal renderers for assistant output."""

from __future__ import annotations

import json
import re
import sys
import unicodedata

import os
import shutil

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_TABLE_SEPARATOR_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$")
_MD_SIGNAL_RE = re.compile(r"(?m)(^\s{0,3}(?:#{1,6}|>|\|)\s*\S|^\s{0,3}(?:[-*+]|\d+\.)\s+\S|```)")
_INLINE_TOKEN_RE = re.compile(r"(\*\*[^*\n]+\*\*|`[^`\n]+`|\*[^*\n]+\*)")
_MD_OPENER_RE = re.compile(r"(?m)(^\s{0,3}(?:#{1,6}|>|\|)\s*|^\s{0,3}(?:[-*+]|\d+\.)\s|```|`|\*\*)")


def has_markdown_signal(text: str) -> bool:
    sample = text if len(text) <= 500 else text[:500]
    return bool(_MD_SIGNAL_RE.search(sample) or _INLINE_TOKEN_RE.search(sample))


def has_markdown_opener(text: str) -> bool:
    sample = text if len(text) <= 500 else text[:500]
    return bool(_MD_OPENER_RE.search(sample))


_FENCED_BLOCK_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def has_flowchart_block(text: str) -> bool:
    """Return True if text contains a fenced block with a flowchart diagram."""
    for m in _FENCED_BLOCK_RE.finditer(text):
        header_line = m.group(0).split("\n", 1)[0]  # e.g. ```flowchart LR
        body = m.group(1)
        if "flowchart" in header_line.lower() or body.lstrip().startswith("flowchart "):
            return True
    return False


def split_markdown_blocks(text: str) -> list[str]:
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    blocks: list[str] = []
    i = 0

    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue

        if lines[i].lstrip().startswith("```"):
            start = i
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith("```"):
                i += 1
            if i < len(lines):
                i += 1
            blocks.append("\n".join(lines[start:i]).strip())
            continue

        if i + 1 < len(lines) and _looks_like_table_start(lines[i], lines[i + 1]):
            start = i
            i += 2
            while i < len(lines) and lines[i].strip() and "|" in lines[i]:
                i += 1
            blocks.append("\n".join(lines[start:i]).strip())
            continue

        start = i
        i += 1
        while i < len(lines):
            if not lines[i].strip():
                break
            if lines[i].lstrip().startswith("```"):
                break
            if i + 1 < len(lines) and _looks_like_table_start(lines[i], lines[i + 1]):
                break
            i += 1
        blocks.append("\n".join(lines[start:i]).strip())

    return [block for block in blocks if block]


def render_markdown_block(block: str):
    if _is_fenced_block(block):
        return _render_fenced_block(block)
    if _is_markdown_table(block):
        return _render_table(block)
    return Markdown(block)


# ---------------------------------------------------------------------------
# Streaming renderer
# ---------------------------------------------------------------------------

class AssistantStreamRenderer:
    """
    流式 Markdown 渲染器。

    策略：
    - 以"段落边界"为单位渲染——每当一个完整块（普通段落、代码块、表格）就绪时
      立即调用 Rich 渲染并输出，无需等待全文结束。
    - 对"需要完整内容才能渲染"的特殊块（代码块、表格），在等待期间先将原文本以
      纯文本形式输出到屏幕；一旦块完整，擦除这部分纯文本输出，再做结构化渲染。
    - 普通段落（Markdown 文本）：积累整个段落（空行分隔），段落完成后一次性用
      Rich Markdown 渲染，避免残缺片段。
    - 换行符之前保留在缓冲区，直到真正出现新行，确保每次渲染都是完整的行单位。
    """

    def __init__(self, console: Console):
        self.console = console
        self._text = ""           # 全部已接收文本
        self._rendered_pos = 0    # _text 中已完成渲染的字节位置（"已消费"边界）

        # 对于正在等待完整结束的 fenced block / table，记录其开始在 _text 中的位置
        # 以及已输出到终端的纯文本字符数（用于 erase）。
        self._pending_raw_start: int | None = None   # 该特殊块在 _text 中的起始 index
        self._pending_raw_lines: int = 0             # 已向终端输出的该块的行数

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_text(self, chunk: str) -> None:
        if not chunk:
            return
        self._text += chunk
        self._try_flush()

    def finalize(self) -> str:
        """流结束，渲染剩余所有内容。"""
        remainder = self._text[self._rendered_pos:]
        if not remainder.strip():
            # 仅有空白：输出换行占位
            if remainder:
                self.console.print("", end="", highlight=False, markup=False)
            return self._text

        # 如果有悬空的 pending raw 输出，先擦除
        if self._pending_raw_start is not None:
            self._erase_pending_raw()
            self._pending_raw_start = None
            self._pending_raw_lines = 0

        # 渲染剩余全部块
        blocks = split_markdown_blocks(remainder)
        for block in blocks:
            renderable = render_markdown_block(block)
            self.console.print(renderable)

        self._rendered_pos = len(self._text)
        return self._text

    @property
    def text(self) -> str:
        return self._text

    # ------------------------------------------------------------------
    # Internal flush logic
    # ------------------------------------------------------------------

    def _try_flush(self) -> None:
        """
        检查从 _rendered_pos 开始的未渲染内容，将能确认完整的块渲染输出。
        """
        while True:
            pending = self._text[self._rendered_pos:]
            if not pending:
                break

            # 找到下一个完整块
            result = self._next_complete_block(pending)
            if result is None:
                # 没有完整块可渲染——但如果正处于特殊块等待中，把新到的行作为纯文本输出
                self._stream_pending_raw_tail()
                break

            block, consumed = result

            # 如果此前有 pending raw 输出（等待完整时的纯文本），先擦除
            if self._pending_raw_start is not None:
                self._erase_pending_raw()
                self._pending_raw_start = None
                self._pending_raw_lines = 0

            renderable = render_markdown_block(block)
            self.console.print(renderable)
            self._rendered_pos += consumed

    def _next_complete_block(self, text: str) -> tuple[str, int] | None:
        """
        从 text 开头找到第一个「完整块」，返回 (block_str, consumed_chars)。
        若不存在完整块则返回 None。

        完整块定义：
        - 普通段落：以空行结束（即段落后有 \n\n 或文本结束后有换行且后面有空行）
        - fenced 代码块：有开闭 ``` 对
        - Markdown 表格：表格所有行已完整（后面有空行或遇到非表格行）
        """
        text = text.replace("\r\n", "\n")

        # 跳过开头的空行（空行本身不构成块，直接消费掉）
        stripped_start = len(text) - len(text.lstrip("\n"))
        if stripped_start > 0:
            self._rendered_pos += stripped_start
            text = text[stripped_start:]
            if not text:
                return None

        lines = text.split("\n")

        # ── fenced 代码块 ────────────────────────────────────────────
        if lines[0].lstrip().startswith("```"):
            # 查找结束的 ```
            end_idx = None
            for i in range(1, len(lines)):
                if lines[i].lstrip().startswith("```"):
                    end_idx = i
                    break
            if end_idx is None:
                # 块未闭合 → 标记为 pending raw
                if self._pending_raw_start is None:
                    self._pending_raw_start = self._rendered_pos
                return None
            # 找到完整的 fenced block
            block_lines = lines[: end_idx + 1]
            block = "\n".join(block_lines)
            # consumed = block 本身的字符数 + 后面的空行
            consumed = len(block)
            # 消费掉紧随其后的换行
            rest = text[consumed:]
            extra = len(rest) - len(rest.lstrip("\n"))
            consumed += extra
            return block.strip(), consumed

        # ── Markdown 表格 ─────────────────────────────────────────────
        if len(lines) >= 2 and _looks_like_table_start(lines[0], lines[1]):
            # 收集所有连续的表格行
            end_idx = 2
            while end_idx < len(lines) and lines[end_idx].strip() and "|" in lines[end_idx]:
                end_idx += 1
            # 判断表格是否"完整"：后面出现了空行或文本已结束但有至少一行数据行
            table_complete = (
                end_idx < len(lines) and not lines[end_idx].strip()
            ) or (
                # 只有 header + separator，没有数据行，仍当作完整
                end_idx == len(lines) and not text.endswith("\n|")
            )
            if not table_complete and end_idx == len(lines):
                # 还没有终止行 → 可能表格还未输完
                if self._pending_raw_start is None:
                    self._pending_raw_start = self._rendered_pos
                return None
            block_lines = lines[:end_idx]
            block = "\n".join(block_lines)
            consumed = len(block)
            rest = text[consumed:]
            extra = len(rest) - len(rest.lstrip("\n"))
            consumed += extra
            return block.strip(), consumed

        # ── 普通段落（空行分隔）────────────────────────────────────────
        # 找到第一个空行（连续两个 \n\n）
        double_newline = text.find("\n\n")
        if double_newline == -1:
            # 还没有段落结束符：不渲染
            return None
        # 段落内容
        para = text[:double_newline].strip()
        if not para:
            # 全是空白 → 消费掉
            consumed = double_newline + 2
            self._rendered_pos += consumed
            return self._next_complete_block(self._text[self._rendered_pos:])
        consumed = double_newline + 2
        return para, consumed

    def _stream_pending_raw_tail(self) -> None:
        """
        当处于「等待特殊块完整」的过程中，把新到的、尚未输出的行以纯文本输出到终端。
        这样用户能实时看到正在流式生成的代码/表格内容。
        """
        if self._pending_raw_start is None:
            return

        pending_text = self._text[self._pending_raw_start:]
        pending_lines = pending_text.split("\n")

        # 只输出已「稳定」的行（即不包括最后一行——它可能还在增长）
        stable_lines = pending_lines[:-1]  # 最后一行可能未完整
        already_output = self._pending_raw_lines

        new_lines = stable_lines[already_output:]
        if not new_lines:
            return

        for line in new_lines:
            self.console.print(line, end="\n", highlight=False, markup=False)
        self._pending_raw_lines += len(new_lines)

    def _count_lines_on_terminal(self, text: str) -> int:
        """计算文本在终端上实际占用的行数（考虑折行）。"""
        cols = shutil.get_terminal_size(fallback=(80, 24)).columns or 80
        total = 0
        for line in text.split("\n"):
            total += max(1, (len(line) + cols - 1) // cols)
        return total

    def _erase_pending_raw(self) -> None:
        """擦除已输出的 pending raw 行，为结构化渲染腾出空间。"""
        if self._pending_raw_lines == 0:
            return
        # 取已输出的原始文本
        pending_text = self._text[self._pending_raw_start:]
        pending_lines = pending_text.split("\n")
        output_text = "\n".join(pending_lines[: self._pending_raw_lines])

        n = self._count_lines_on_terminal(output_text)
        # 移动到已输出块的起始行并清除
        sys.stdout.write("\r\033[K")
        for _ in range(n - 1):
            sys.stdout.write("\033[A\033[K")
        sys.stdout.flush()


# Backward-compatible alias for older imports/tests.
StreamingAssistantRenderer = AssistantStreamRenderer


def _is_fenced_block(block: str) -> bool:
    lines = block.splitlines()
    return bool(lines) and lines[0].lstrip().startswith("```")


def _parse_fenced_block(block: str) -> tuple[str, str]:
    lines = block.splitlines()
    if not lines:
        return "", ""
    fence_header = lines[0].strip()[3:].strip()
    body_lines = lines[1:]
    if body_lines and body_lines[-1].lstrip().startswith("```"):
        body_lines = body_lines[:-1]
    return fence_header.lower(), "\n".join(body_lines)


def _render_fenced_block(block: str):
    language, body = _parse_fenced_block(block)
    if language == "json":
        return _render_json_block(body)
    if language in {"bash", "sh", "zsh", "shell", "console"}:
        return _render_shell_block(body, title=language or "shell")
    if language in {"txt", "text", "plain"}:
        return _render_text_block(body, title=language or "text")
    if language in {"yaml", "yml"}:
        return _render_kv_block(body, title=language, border_style="yellow")
    if language in {"ini", "env", "toml"}:
        return _render_kv_block(body, title=language, border_style="cyan")
    if language == "sql":
        return _render_sql_block(body)
    if language == "csv":
        return _render_csv_block(body)
    if language.startswith("flowchart") or body.lstrip().startswith("flowchart "):
        # Extract orientation from the fence header (e.g. "flowchart td" -> "TD")
        parts = language.split()
        orientation = parts[1].upper() if len(parts) >= 2 else None
        return _render_flowchart_block(body, orientation=orientation)
    # 其他代码块使用Panel包裹
    return Panel(Text(body), title=language or "code", border_style="dim")


def _looks_like_table_start(header: str, separator: str) -> bool:
    return "|" in header and bool(_TABLE_SEPARATOR_RE.match(separator.strip()))


def _is_markdown_table(block: str) -> bool:
    lines = [line for line in block.splitlines() if line.strip()]
    return len(lines) >= 2 and _looks_like_table_start(lines[0], lines[1])


def _split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip().replace("<br>", "\n") for cell in line.split("|")]


def _render_inline_markdown(text: str) -> Text:
    renderable = Text()
    last = 0
    for match in _INLINE_TOKEN_RE.finditer(text):
        start, end = match.span()
        if start > last:
            renderable.append(text[last:start])

        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            renderable.append(token[2:-2], style="bold")
        elif token.startswith("`") and token.endswith("`"):
            renderable.append(token[1:-1], style="bold bright_black on grey15")
        elif token.startswith("*") and token.endswith("*"):
            renderable.append(token[1:-1], style="italic")
        else:
            renderable.append(token)
        last = end

    if last < len(text):
        renderable.append(text[last:])
    return renderable


def _strip_inline_markdown_markers(text: str) -> str:
    return _INLINE_TOKEN_RE.sub(lambda m: m.group(0).strip("*`"), text)


def _render_table(block: str) -> Table:
    lines = [line for line in block.splitlines() if line.strip()]
    headers = _split_table_row(lines[0])
    rows = [_split_table_row(line) for line in lines[2:]]

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan", expand=True)
    for header in headers:
        table.add_column(_render_inline_markdown(header or " "), overflow="fold")
    for row in rows:
        normalized = row + [""] * max(0, len(headers) - len(row))
        table.add_row(*[_render_inline_markdown(cell) for cell in normalized[: len(headers)]])
    return table


def _render_json_block(body: str):
    try:
        parsed = json.loads(body)
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        pretty = body
    return Panel(Text(pretty), title="json", border_style="blue")


def _render_text_block(body: str, title: str = "text"):
    return Panel(Text(body), title=title, border_style="dim")


def _render_shell_block(body: str, title: str = "shell"):
    text = Text()
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("$ "):
            text.append("$ ", style="bold green")
            text.append(line[2:])
        elif line.startswith("# "):
            text.append(line, style="dim")
        else:
            text.append(line)
        if index != len(lines) - 1:
            text.append("\n")
    return Panel(text, title=title, border_style="green")


def _render_kv_block(body: str, title: str, border_style: str):
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style=f"bold {border_style}", expand=True)
    table.add_column("Key", overflow="fold")
    table.add_column("Value", overflow="fold")
    added = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        separator = None
        if "=" in line:
            separator = "="
        elif ":" in line:
            separator = ":"
        if separator is None:
            table.add_row(line, "")
            added = True
            continue
        key, value = line.split(separator, 1)
        table.add_row(key.strip(), value.strip())
        added = True
    if not added:
        return Panel(Text(body), title=title, border_style=border_style)
    return Panel(table, title=title, border_style=border_style)


def _render_sql_block(body: str):
    keywords = {
        "select", "from", "where", "group", "by", "order", "limit", "insert",
        "into", "values", "update", "set", "delete", "join", "left", "right",
        "inner", "outer", "and", "or", "as", "on", "having",
    }
    text = Text()
    token_re = re.compile(r"(\s+|,|\(|\)|;)")
    for token in token_re.split(body):
        if not token:
            continue
        if token.isspace() or token in {",", "(", ")", ";"}:
            text.append(token)
        elif token.lower() in keywords:
            text.append(token.upper(), style="bold cyan")
        else:
            text.append(token)
    return Panel(text, title="sql", border_style="cyan")


def _render_csv_block(body: str):
    lines = [line for line in body.splitlines() if line.strip()]
    if not lines:
        return Panel(Text(body), title="csv", border_style="blue")
    rows = [line.split(",") for line in lines]
    headers = rows[0]
    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold blue", expand=True)
    for header in headers:
        table.add_column(header.strip() or " ", overflow="fold")
    for row in rows[1:]:
        normalized = [cell.strip() for cell in row] + [""] * max(0, len(headers) - len(row))
        table.add_row(*normalized[: len(headers)])
    return Panel(table, title="csv", border_style="blue")


def _render_flowchart_block(body: str, orientation: str | None = None):
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    has_header = bool(lines and lines[0].lower().startswith("flowchart "))
    title = lines[0] if has_header else "flowchart"
    if has_header:
        parts = lines[0].split()
        if len(parts) >= 2:
            orientation = parts[1].upper()
    if orientation is None:
        orientation = "TD"

    parse_lines = lines[1:] if has_header else lines
    nodes, edges = _parse_flowchart(parse_lines)
    if not edges:
        return Panel(Text(body), title=title, border_style="magenta")

    ascii_flow = _render_ascii_flowchart(nodes, edges, orientation=orientation)
    return Panel(Text(ascii_flow), title=title, border_style="magenta")


def _extract_node_label(s: str, start: int) -> tuple[str, int] | None:
    """
    从 s[start] 开始，提取一个节点标签部分（如 `[...]` / `(...)` / `{...}`）。
    支持标签内嵌套同类括号（如 `connect_motorcad()`）。
    返回 (label_content, end_index)，其中 end_index 是闭括号之后的位置。
    若 s[start] 不是开括号则返回 None。
    """
    if start >= len(s):
        return None
    open_ch = s[start]
    close_map = {"[": "]", "(": ")", "{": "}"}
    if open_ch not in close_map:
        return None
    close_ch = close_map[open_ch]
    depth = 0
    i = start
    while i < len(s):
        ch = s[i]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return s[start + 1: i], i + 1
        i += 1
    # 未找到匹配闭括号
    return None


def _parse_node_token(s: str, pos: int) -> tuple[str, str, int] | None:
    """
    从 s[pos] 尝试解析一个节点 token（ID + 可选标签）。
    返回 (node_id, label, end_pos) 或 None。
    """
    # 节点 ID：字母/数字/下划线
    id_match = re.match(r"[A-Za-z0-9_]+", s[pos:])
    if not id_match:
        return None
    node_id = id_match.group(0)
    end = pos + len(node_id)
    if end < len(s) and s[end] in ("[", "(", "{"):
        result = _extract_node_label(s, end)
        if result is not None:
            raw_label, end = result
            label = _strip_inline_markdown_markers(raw_label.strip().strip('"').strip("'"))
            return node_id, label or node_id, end
    return node_id, node_id, end


_EDGE_ARROW_RE = re.compile(r"\s*(-->|==>|-.->|---)\s*")


def _parse_flowchart(lines: list[str]) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    nodes: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 尝试按 "node --> node" 格式逐字符解析整行
        pos = 0
        parsed: list[tuple[str, str]] = []  # [(node_id, label), ...]
        arrow_types: list[str] = []

        tok = _parse_node_token(line, pos)
        if tok is None:
            continue
        node_id, label, pos = tok
        parsed.append((node_id, label))

        while pos < len(line):
            # 跳过空白
            sp = re.match(r"\s+", line[pos:])
            if sp:
                pos += len(sp.group(0))

            # 尝试匹配箭头
            arr = _EDGE_ARROW_RE.match(line[pos:])
            if arr is None:
                break
            arrow = arr.group(1)
            pos += len(arr.group(0))

            # 匹配右侧节点
            tok = _parse_node_token(line, pos)
            if tok is None:
                break
            node_id, label, pos = tok
            arrow_types.append(arrow)
            parsed.append((node_id, label))

        # 注册节点
        for nid, nlabel in parsed:
            if nlabel != nid:
                nodes[nid] = nlabel
            else:
                nodes.setdefault(nid, nlabel)

        # 注册边
        for i, arrow in enumerate(arrow_types):
            edges.append((parsed[i][0], arrow, parsed[i + 1][0]))

    return nodes, edges


def _parse_flow_node(raw: str) -> tuple[str, str]:
    """兼容旧调用点的简化版节点解析（不再使用于主路径）。"""
    raw = raw.strip()
    result = _parse_node_token(raw, 0)
    if result is None:
        return raw, raw
    node_id, label, _ = result
    return node_id, label


def _render_ascii_flowchart(nodes: dict[str, str], edges: list[tuple[str, str, str]], orientation: str = "TD") -> str:
    if orientation == "LR":
        chain: list[str] = []
        for index, (left, _edge, right) in enumerate(edges):
            if index == 0:
                chain.append(_format_flow_node(nodes.get(left, left)))
            chain.append(_format_flow_node(nodes.get(right, right)))
        return " --> ".join(chain)

    lines: list[str] = []
    seen_nodes: set[str] = set()
    for index, (left, edge, right) in enumerate(edges):
        left_label = nodes.get(left, left)
        right_label = nodes.get(right, right)
        if left not in seen_nodes:
            lines.extend(_render_ascii_node(left_label))
            seen_nodes.add(left)
        lines.append("  |" if edge in {"-->", "---"} else "  ‖")
        lines.append("  v")
        lines.extend(_render_ascii_node(right_label))
        seen_nodes.add(right)
        if index != len(edges) - 1:
            lines.append("")
    return "\n".join(lines)


def _display_width(s: str) -> int:
    """计算字符串在终端中的显示宽度（中文/全角字符占 2 列）。"""
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def _format_flow_node(label: str) -> str:
    return f"[{ ' '.join(_strip_inline_markdown_markers(label).split()) }]"


def _render_ascii_node(label: str) -> list[str]:
    clean = " ".join(_strip_inline_markdown_markers(label).split())
    dw = _display_width(clean)
    # 边框宽度基于显示宽度，保证盒子两侧各有一个空格
    width = max(dw + 2, 6)
    top = "+" + "-" * width + "+"
    # 内容区域显示宽度 = width - 2（左右各一个空格）
    inner = width - 2
    pad = inner - dw
    left_pad = pad // 2
    right_pad = pad - left_pad
    mid = "| " + " " * left_pad + clean + " " * right_pad + " |"
    bottom = "+" + "-" * width + "+"
    return [top, mid, bottom]
