"""Terminal renderers for assistant output."""

from __future__ import annotations

import json
import re

from rich import box
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_TABLE_SEPARATOR_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$")
_MD_SIGNAL_RE = re.compile(r"(?m)(^\s{0,3}(?:#{1,6}|>|\|)\s*\S|^\s{0,3}(?:[-*+]|\d+\.)\s+\S|```)")
_INLINE_TOKEN_RE = re.compile(r"(\*\*[^*\n]+\*\*|`[^`\n]+`|\*[^*\n]+\*)")
_MD_OPENER_RE = re.compile(r"(?m)(^\s{0,3}(?:#{1,6}|>|\|)\s*|^\s{0,3}(?:[-*+]|\d+\.)\s|```|`|\*\*)")
_PLAIN_BUFFER_LIMIT = 96


def has_markdown_signal(text: str) -> bool:
    sample = text if len(text) <= 500 else text[:500]
    return bool(_MD_SIGNAL_RE.search(sample) or _INLINE_TOKEN_RE.search(sample))


def has_markdown_opener(text: str) -> bool:
    sample = text if len(text) <= 500 else text[:500]
    return bool(_MD_OPENER_RE.search(sample))


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


def _render_streaming_block(block: str):
    # 检查是否是fenced block（代码块）
    if _is_fenced_block(block):
        lines = block.splitlines()
        # 检查是否有结束的fence标记（第二个```）
        fence_count = sum(1 for line in lines if line.lstrip().startswith("```"))
        is_complete = fence_count >= 2
        
        if not is_complete:
            # 检查是否是flowchart块
            language, body = _parse_fenced_block(block)
            if language.startswith("flowchart") or body.lstrip().startswith("flowchart "):
                # flowchart块即使不完整也要流式输出,返回纯文本
                return Text(body if body else "")
            # 其他不完整的代码块返回None,避免显示残缺内容
            return None
    
    return render_markdown_block(block)


class AssistantStreamRenderer:
    """Streaming assistant renderer with a low-flicker plain-text fast path."""

    def __init__(self, console: Console):
        self.console = console
        self._text = ""
        self._plain_streamed = ""
        self._committed_blocks: list[str] = []
        self._cache: dict[str, object] = {}
        self._live: Live | None = None

    def append_text(self, text: str) -> None:
        if not text:
            return
        self._text += text

        if self._live is None:
            # Stay in the plain-text fast path unless markdown openers appear.
            if has_markdown_opener(self._text):
                self._commit_stable_blocks()
                self._refresh_live_tail()
                return

            pending_plain = self._text[len(self._plain_streamed) :]
            flush_upto = max(0, len(pending_plain) - _PLAIN_BUFFER_LIMIT)
            if flush_upto > 0:
                to_flush = pending_plain[:flush_upto]
                self.console.print(to_flush, end="", highlight=False, markup=False)
                self._plain_streamed += to_flush
            return

        self._commit_stable_blocks()
        self._refresh_live_tail()

    def finalize(self) -> str:
        if self._live is not None:
            self._commit_stable_blocks(final=True)
            self._refresh_live_tail()
            self._stop_live()
        else:
            pending_plain = self._text[len(self._plain_streamed) :]
            if pending_plain:
                self.console.print(pending_plain, end="", highlight=False, markup=False)
                self._plain_streamed += pending_plain
        return self._text

    @property
    def text(self) -> str:
        return self._text

    def _ensure_live(self) -> None:
        if self._live is not None:
            return
        self._live = Live(
            Text(""),
            console=self.console,
            auto_refresh=False,
            transient=False,
            vertical_overflow="visible",
        )
        self._live.start()

    def _commit_stable_blocks(self, final: bool = False) -> None:
        blocks = split_markdown_blocks(self._markdown_text)
        if not blocks:
            return
        stable_count = len(blocks) if final else max(0, len(blocks) - 1)
        while len(self._committed_blocks) < stable_count:
            candidate = blocks[len(self._committed_blocks)]
            self._committed_blocks.append(candidate)

    def _refresh_live_tail(self) -> None:
        unstable_blocks = self._unstable_blocks()
        committed_renderables = [self._render_cached_block(block) for block in self._committed_blocks]
        if not unstable_blocks and not committed_renderables:
            self._stop_live()
            return
        self._ensure_live()
        assert self._live is not None
        renderables: list[object] = []
        for index, renderable in enumerate(committed_renderables):
            if index:
                renderables.append(Text(""))
            renderables.append(renderable)
        if unstable_blocks:
            # 对每个unstable_block单独渲染，而不是合并后再渲染
            # 这样可以正确处理不完整的flowchart块
            for unstable_block in unstable_blocks:
                rendered = _render_streaming_block(unstable_block)
                # 过滤掉None值（不完整的flowchart块）
                if rendered is not None:
                    if renderables:
                        renderables.append(Text(""))
                    renderables.append(rendered)
        self._live.update(Group(*renderables) if renderables else Text(""), refresh=True)

    def _unstable_blocks(self) -> list[str]:
        blocks = split_markdown_blocks(self._markdown_text)
        if len(self._committed_blocks) >= len(blocks):
            return []
        return blocks[len(self._committed_blocks) :]

    def _stop_live(self) -> None:
        if self._live is None:
            return
        self._live.stop()
        self._live = None

    def _render_cached_block(self, block: str):
        cached = self._cache.get(block)
        if cached is not None:
            return cached
        renderable = render_markdown_block(block)
        self._cache[block] = renderable
        return renderable

    @property
    def _markdown_text(self) -> str:
        return self._text[len(self._plain_streamed) :]


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
    # 对于flowchart块，直接返回纯文本，不使用Panel包裹
    if language.startswith("flowchart") or body.lstrip().startswith("flowchart "):
        return Text(body)
    # 其他代码块使用Panel包裹
    return Panel(Text(body), title=language or "code", border_style="dim")


def _is_cacheable_block(block: str) -> bool:
    return not _is_markdown_table(block) and not _is_fenced_block(block)


def _should_defer_render(block: str) -> bool:
    # 移除flowchart的延迟渲染逻辑,让所有块都正常流式输出
    return False


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


def _render_flowchart_block(body: str):
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    title = lines[0] if lines else "flowchart"
    orientation = "TD"
    if lines and lines[0].lower().startswith("flowchart "):
        parts = lines[0].split()
        if len(parts) >= 2:
            orientation = parts[1].upper()

    nodes, edges = _parse_flowchart(lines[1:] if len(lines) > 1 else [])
    if not edges:
        return Panel(Text(body), title=title, border_style="magenta")

    ascii_flow = _render_ascii_flowchart(nodes, edges, orientation=orientation)
    return Panel(Text(ascii_flow), title=title, border_style="magenta")


def _parse_flowchart(lines: list[str]) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    nodes: dict[str, str] = {}
    edges: list[tuple[str, str, str]] = []
    node_re = re.compile(r"^\s*([A-Za-z0-9_]+)([\[\(\{].*[\]\)\}])\s*$")
    edge_re = re.compile(
        r"([A-Za-z0-9_]+(?:[\[\(\{][^\]\)\}]+[\]\)\}])?)\s*(-->|==>|-.->|---)\s*([A-Za-z0-9_]+(?:[\[\(\{][^\]\)\}]+[\]\)\}])?)"
    )

    for line in lines:
        node_match = node_re.match(line)
        if node_match:
            node_id, label_part = node_match.groups()
            label = label_part[1:-1].strip().strip('"').strip("'")
            nodes[node_id] = label or node_id

        match = edge_re.search(line)
        if not match:
            continue
        left_raw, edge, right_raw = match.groups()
        left_id, left_label = _parse_flow_node(left_raw)
        right_id, right_label = _parse_flow_node(right_raw)
        nodes.setdefault(left_id, left_label)
        nodes.setdefault(right_id, right_label)
        if left_label != left_id:
            nodes[left_id] = left_label
        if right_label != right_id:
            nodes[right_id] = right_label
        edges.append((left_id, edge, right_id))

    return nodes, edges


def _parse_flow_node(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    match = re.match(r"([A-Za-z0-9_]+)([\[\(\{].*[\]\)\}])?", raw)
    if not match:
        return raw, raw
    node_id = match.group(1)
    label_part = match.group(2) or ""
    if not label_part:
        return node_id, node_id
    label = _strip_inline_markdown_markers(label_part[1:-1].strip())
    return node_id, label or node_id


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


def _format_flow_node(label: str) -> str:
    return f"[{ ' '.join(_strip_inline_markdown_markers(label).split()) }]"


def _render_ascii_node(label: str) -> list[str]:
    clean = " ".join(_strip_inline_markdown_markers(label).split())
    width = max(len(clean) + 2, 6)
    top = "+" + "-" * width + "+"
    mid = f"| {clean.center(width - 2)} |"
    bottom = "+" + "-" * width + "+"
    return [top, mid, bottom]
