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
from rich.style import Style
from rich.padding import Padding

# ---------------------------------------------------------------------------
# Color and Style Constants (参考 claude-code-sourcemap 设计)
# ---------------------------------------------------------------------------

# 代码块背景样式（使用 Style 对象正确设置背景色）
CODE_BLOCK_STYLE = Style(bgcolor="#1e1e2e")

# 主题色配置
COLORS = {
    # Claude 品牌色
    'claude_orange': '#d7775f',
    'claude_orange_rgb': (215, 119, 87),
    # 基础颜色
    'black': '#1a1a1a',
    'white': '#ffffff',
    'gray': '#888888',
    'gray_light': '#cccccc',
    'gray_dark': '#333333',
    # 语义颜色
    'success': '#4ade80',
    'error': '#f87171',
    'warning': '#fbbf24',
    'info': '#60a5fa',
    'primary': '#89b4fa',
    'secondary': '#cba6f7',
    'accent': '#fab387',
    # 代码块主题
    'code_bg': '#1e1e2e',
    'code_fg': '#cdd6f4',
    'code_comment': '#6c7086',
    'code_keyword': '#cba6f7',
    'code_string': '#a6e3a1',
    'code_number': '#fab387',
    'code_function': '#89b4fa',
    'code_class': '#f9e2af',
    # Panel 边框颜色
    'border_default': '#45475a',
    'border_success': '#4ade80',
    'border_error': '#f87171',
    'border_warning': '#fbbf24',
    'border_info': '#60a5fa',
    'border_magenta': '#cba6f7',
    'border_cyan': '#89dceb',
    'border_green': '#4ade80',
}

# 样式配置
STYLES = {
    'prompt': Style(color=COLORS['claude_orange'], bold=True),
    'success': Style(color=COLORS['success']),
    'error': Style(color=COLORS['error']),
    'warning': Style(color=COLORS['warning']),
    'info': Style(color=COLORS['info']),
    'code': Style(color=COLORS['code_fg']),
    'comment': Style(color=COLORS['code_comment'], dim=True),
    'keyword': Style(color=COLORS['code_keyword'], bold=True),
    'string': Style(color=COLORS['code_string']),
    'number': Style(color=COLORS['code_number']),
}

# ---------------------------------------------------------------------------
# Markdown Detection Utilities
# ---------------------------------------------------------------------------

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
        header_line = m.group(0).split("\n", 1)[0]
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

# 行内 Markdown 特征：含这些标记的行在行完成后需要擦除重渲
_INLINE_MD_RE = re.compile(r"\*\*[^*\n]+\*\*|\*[^*\n]+\*|`[^`\n]+`|^#{1,6}\s|^[-*+]\s|^\d+\.\s|^>\s", re.MULTILINE)

# 表格分隔行
_TABLE_SEP_LINE_RE = re.compile(r"^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$")


def _display_width(s: str) -> int:
    """计算字符串终端显示宽度（宽字符占 2 列）。"""
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def _terminal_line_count(text: str) -> int:
    """计算文本在终端实际占用的行数（含折行）。"""
    cols = shutil.get_terminal_size(fallback=(80, 24)).columns or 80
    total = 0
    for line in text.split("\n"):
        w = _display_width(line)
        total += max(1, (w + cols - 1) // cols)
    return total


def _erase_lines(n: int) -> None:
    """擦除光标所在行及上方共 n 行。"""
    if n <= 0:
        return
    sys.stdout.write("\r\033[K")
    for _ in range(n - 1):
        sys.stdout.write("\033[A\033[K")
    sys.stdout.flush()


class AssistantStreamRenderer:
    """
    流式 Markdown 渲染器——行级实时渲染策略：

    普通文本行
      - token 到达时立即 write stdout（打字机效果）
      - 行结束（\n）时：若该行含 Markdown 标记（加粗/斜体/标题/列表等），
        擦除该行原始文字，用 Rich Markdown 重新渲染；否则保持原样

    代码块（``` ... ```）
      - 进入代码块后 token 继续逐字写 stdout（用户实时看到代码）
      - 遇到闭合 ``` 时：擦除整个代码块的原始文字，用 Rich Panel 重新渲染

    表格（| header | ... \n |---|--- 行）
      - 进入表格模式后，字符仍然实时写入 stdout
      - 每收到新行时，擦除之前的表格输出，重新渲染完整的 Rich Table
      - 表格结束（空行或非表格行）时，完成渲染并退出表格模式

    这样做到：流式阶段每个字符立即可见，完整块就绪时原位替换为格式化渲染，
    表格实现实时流式刷新，用户可以看到表格逐行构建的过程。
    """

    # 渲染器状态
    _STATE_NORMAL   = "normal"    # 普通文本
    _STATE_CODE     = "code"      # 代码块内部
    _STATE_TABLE    = "table"     # 表格模式（流式刷新）

    def __init__(self, console: Console):
        self.console = console
        self._full_text = ""          # 完整接收文本（仅用于 text 属性）

        self._state = self._STATE_NORMAL

        # 当前行缓冲（行内字符，不含 \n）
        self._cur_line = ""
        # 当前行已向 stdout 写入的字符数（用于行级擦除）
        self._cur_line_written = 0

        # 代码块状态
        self._code_lang = ""          # 语言标识
        self._code_body_lines: list[str] = []  # 已完成的代码行
        self._code_raw_lines = 0      # 已写入 stdout 的代码块行数（含 ``` 行）

        # 表格状态
        self._table_lines: list[str] = []  # 已收集的表格行（含 header）
        self._table_raw_lines = 0      # 已写入 stdout 的表格行数

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append_text(self, chunk: str) -> None:
        if not chunk:
            return
        self._full_text += chunk
        for ch in chunk:
            self._feed_char(ch)

    def finalize(self) -> str:
        """流结束，处理所有未完成的缓冲内容。"""
        if self._state == self._STATE_CODE:
            # 代码块未闭合：擦除原始输出，按普通代码块渲染
            self._flush_code_block(closed=False)
        elif self._state == self._STATE_TABLE:
            # 表格未结束：直接渲染已收集的行
            self._flush_table()
        else:
            # 普通行：处理最后一行（无 \n 结尾的尾部）
            self._flush_cur_line(eol=False)

        return self._full_text

    @property
    def text(self) -> str:
        return self._full_text

    # ------------------------------------------------------------------
    # 核心字符状态机
    # ------------------------------------------------------------------

    def _feed_char(self, ch: str) -> None:
        if ch == "\n":
            self._on_newline()
        else:
            self._on_char(ch)

    def _on_char(self, ch: str) -> None:
        """处理非换行字符。"""
        self._cur_line += ch

        # 所有模式下都实时写入 stdout（打字机效果）
        sys.stdout.write(ch)
        sys.stdout.flush()
        self._cur_line_written += 1

    def _on_newline(self) -> None:
        """处理换行符——行完成，触发行级渲染决策。"""
        line = self._cur_line
        self._cur_line = ""
        self._cur_line_written = 0

        if self._state == self._STATE_NORMAL:
            # 先检查上一行是否是表格候选（当前行可能是分隔行）
            if hasattr(self, "_table_candidate"):
                if self._maybe_enter_table(line):
                    return   # 已进入表格模式，当前行已被收入表格缓冲
                # 不是表格分隔行，继续按普通行处理当前行
            self._handle_normal_line(line)
        elif self._state == self._STATE_CODE:
            self._handle_code_line(line)
        elif self._state == self._STATE_TABLE:
            self._handle_table_line(line)

    # ------------------------------------------------------------------
    # 普通模式行处理
    # ------------------------------------------------------------------

    def _handle_normal_line(self, line: str) -> None:
        """普通行完成，决定是保持原样还是擦除重渲。"""
        # 检测是否进入代码块
        stripped = line.lstrip()
        if stripped.startswith("```"):
            lang = stripped[3:].strip().lower()
            self._state = self._STATE_CODE
            self._code_lang = lang
            self._code_body_lines = []
            # 代码块起始行已经写入了 stdout，记录行数
            self._code_raw_lines = 1
            sys.stdout.write("\n")
            sys.stdout.flush()
            return

        # 检测是否进入表格（当前行是表头，等待下一行判断）
        # 表格由 "header行\n分隔行" 组合触发，先将表头暂存
        if "|" in line:
            # 可能是表格表头，先写 stdout，等下一行判断
            sys.stdout.write("\n")
            sys.stdout.flush()
            # 暂存为"待确认的表格候选行"
            self._table_candidate = line
            self._table_candidate_written = True
            return

        # 清除上一次的表格候选（下一行不是分隔行）
        if hasattr(self, "_table_candidate"):
            del self._table_candidate

        # 普通行：重渲决策
        self._render_normal_line(line)

    def _render_normal_line(self, line: str) -> None:
        """对已完成的普通行进行渲染（含行内 Markdown 检测）。"""
        has_inline_md = bool(_INLINE_MD_RE.search(line))

        if has_inline_md and line.strip():
            # 擦除已写入的原始行，用 Rich 渲染
            written_chars = _display_width(line)
            cols = shutil.get_terminal_size(fallback=(80, 24)).columns or 80
            raw_lines = max(1, (written_chars + cols - 1) // cols)
            _erase_lines(raw_lines)
            self.console.print(Markdown(line))
        else:
            # 无 Markdown：保持原样，只补换行
            sys.stdout.write("\n")
            sys.stdout.flush()

    # ------------------------------------------------------------------
    # 表格候选行 → 表格模式切换
    # ------------------------------------------------------------------

    def _maybe_enter_table(self, line: str) -> bool:
        """
        检查当前行是否是表格分隔行。
        若是，进入表格模式并把候选表头和分隔行一起收入缓冲。
        返回 True 表示已进入表格模式。
        """
        if not hasattr(self, "_table_candidate"):
            return False
        candidate = self._table_candidate
        del self._table_candidate

        if _TABLE_SEP_LINE_RE.match(line.strip()):
            # 确认是表格，擦除已写入的表头行和分隔行
            cols = shutil.get_terminal_size(fallback=(80, 24)).columns or 80
            # 计算表头占用的行数
            header_lines = max(1, (_display_width(candidate) + cols - 1) // cols)
            # 分隔行通常只有一行
            separator_lines = max(1, (_display_width(line) + cols - 1) // cols)
            # 擦除表头和分隔行
            _erase_lines(header_lines + separator_lines + 1)  # +1 是因为当前行的换行
            
            self._state = self._STATE_TABLE
            self._table_lines = [candidate, line]
            self._table_raw_lines = 0  # 重置表格原始行数计数
            # 立即渲染当前已有的表格（表头+分隔行）
            # Rich Table: 1表头 + 1分隔线 + 1底部边框 + 1换行 = 4行
            self._table_raw_lines = len(self._table_lines) + 2
            block = "\n".join(self._table_lines)
            self.console.print(_render_table(block))
            if hasattr(self, "_table_candidate_written"):
                del self._table_candidate_written
            return True
        else:
            # 不是表格，表头已经写入 stdout，只需渲染它
            if hasattr(self, "_table_candidate_written"):
                del self._table_candidate_written
            # 普通行渲染（已有 \n，不再补写）
            # 不需要额外操作，表头已经原样显示
            return False

    # ------------------------------------------------------------------
    # 代码块行处理
    # ------------------------------------------------------------------

    def _handle_code_line(self, line: str) -> None:
        """代码块内的行完成。"""
        if line.lstrip().startswith("```"):
            # 代码块闭合
            self._code_raw_lines += 1  # 闭合行也写了
            sys.stdout.write("\n")
            sys.stdout.flush()
            self._flush_code_block(closed=True)
        else:
            self._code_body_lines.append(line)
            self._code_raw_lines += 1
            sys.stdout.write("\n")
            sys.stdout.flush()

    def _flush_code_block(self, closed: bool) -> None:
        """擦除代码块的原始输出，用 Rich Panel 重渲。"""
        body = "\n".join(self._code_body_lines)
        lang = self._code_lang

        # 构建完整代码块字符串用于 _render_fenced_block
        fence = f"```{lang}\n{body}\n```" if body else f"```{lang}\n```"

        # 擦除：_code_raw_lines 行（代码块内所有已写入的行）
        _erase_lines(self._code_raw_lines)

        renderable = _render_fenced_block(fence)
        self.console.print(renderable)

        # 重置代码块状态
        self._state = self._STATE_NORMAL
        self._code_lang = ""
        self._code_body_lines = []
        self._code_raw_lines = 0

    # ------------------------------------------------------------------
    # 表格行处理
    # ------------------------------------------------------------------

    def _handle_table_line(self, line: str) -> None:
        """表格模式内的行完成。"""
        stripped = line.strip()
        # 空行或非表格行 → 表格结束
        if not stripped or "|" not in stripped:
            # 表格结束：擦除当前渲染的表格（如果有的话），然后重新渲染最终表格
            if self._table_raw_lines > 0:
                _erase_lines(self._table_raw_lines)
            
            # 渲染最终完整表格
            if len(self._table_lines) >= 2:
                block = "\n".join(self._table_lines)
                self.console.print(_render_table(block))
            
            # 重置状态
            self._table_lines = []
            self._table_raw_lines = 0
            self._state = self._STATE_NORMAL
            
            # 当前行按普通行处理
            self._handle_normal_line(line)
        else:
            # 新的表格数据行：擦除之前渲染的表格，然后重新渲染包含新行的完整表格
            if self._table_raw_lines > 0:
                _erase_lines(self._table_raw_lines)
            
            # 添加新行到表格
            self._table_lines.append(line)
            
            # 渲染更新后的完整表格
            if len(self._table_lines) >= 2:
                block = "\n".join(self._table_lines)
                renderable = _render_table(block)
                self.console.print(renderable)
                # 记录渲染后的表格占用行数（用于下一次擦除）
                # Rich Table: 1表头 + 1分隔线 + 数据行 + 1底部边框 + 1换行
                self._table_raw_lines = len(self._table_lines) + 2

    def _flush_table(self) -> None:
        """渲染已缓冲的表格（finalize 时调用）。"""
        if len(self._table_lines) < 2:
            # 不完整，降级为纯文本输出
            for l in self._table_lines:
                sys.stdout.write(l + "\n")
            sys.stdout.flush()
        else:
            block = "\n".join(self._table_lines)
            self.console.print(_render_table(block))
        
        # 重置状态
        self._table_lines = []
        self._table_raw_lines = 0
        self._state = self._STATE_NORMAL

    # ------------------------------------------------------------------
    # 尾部处理（finalize 时当前行无 \n）
    # ------------------------------------------------------------------

    def _flush_cur_line(self, eol: bool = True) -> None:
        """处理末尾未换行的当前行。"""
        line = self._cur_line
        if not line:
            if eol:
                sys.stdout.write("\n")
                sys.stdout.flush()
            return

        # 检查是否有待确认的表格候选（仅用于表格候选降级）
        if hasattr(self, "_table_candidate"):
            del self._table_candidate

        has_inline_md = bool(_INLINE_MD_RE.search(line))
        if has_inline_md and line.strip():
            written = _display_width(line)
            cols = shutil.get_terminal_size(fallback=(80, 24)).columns or 80
            n = max(1, (written + cols - 1) // cols)
            _erase_lines(n)
            self.console.print(Markdown(line))
        else:
            sys.stdout.write("\n")
            sys.stdout.flush()
        self._cur_line = ""
        self._cur_line_written = 0


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
    # 其他代码块使用 Panel 包裹，带语法高亮
    return _render_code_block(body, language=language)


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
    """渲染美观的表格，带主题色边框和表头样式。"""
    lines = [line for line in block.splitlines() if line.strip()]
    headers = _split_table_row(lines[0])
    rows = [_split_table_row(line) for line in lines[2:]]

    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style=f"bold {COLORS['claude_orange']}",
        expand=True,
        border_style=COLORS['border_default'],
        padding=(0, 2),
    )
    
    for header in headers:
        table.add_column(_render_inline_markdown(header or " "), overflow="fold")
    
    for row in rows:
        normalized = row + [""] * max(0, len(headers) - len(row))
        table.add_row(*[_render_inline_markdown(cell) for cell in normalized[: len(headers)]])
    
    return table


def _render_json_block(body: str):
    """渲染 JSON 代码块，带语法高亮。"""
    try:
        parsed = json.loads(body)
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception:
        pretty = body
    
    text = Text()
    lines = pretty.splitlines()
    
    for line in lines:
        # 高亮 JSON 语法元素
        line = line.replace('": "', f'": "{COLORS["code_string"]}')
        line = line.replace('": \'', f'": \'{COLORS["code_string"]}')
        text.append(line)
        text.append("\n")
    
    return Panel(
        text,
        title="json",
        border_style=COLORS['border_info'],
        style=CODE_BLOCK_STYLE,
        expand=False,
    )


def _render_text_block(body: str, title: str = "text"):
    """渲染纯文本块。"""
    return Panel(
        Text(body),
        title=title,
        border_style=COLORS['border_default'],
        expand=False,
    )


def _render_shell_block(body: str, title: str = "shell"):
    """渲染 Shell 命令块，带语法高亮。"""
    text = Text()
    lines = body.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("$ "):
            text.append("$ ", style=f"bold {COLORS['success']}")
            text.append(line[2:], style=COLORS['code_fg'])
        elif line.startswith("# "):
            text.append(line, style=f"dim {COLORS['code_comment']}")
        elif line.startswith("> "):
            text.append("> ", style=f"bold {COLORS['warning']}")
            text.append(line[2:], style=COLORS['code_fg'])
        elif line.startswith("+ "):
            text.append("+ ", style=f"bold {COLORS['secondary']}")
            text.append(line[2:], style=COLORS['code_fg'])
        elif line.startswith("! "):
            text.append("! ", style=f"bold {COLORS['error']}")
            text.append(line[2:], style=COLORS['code_fg'])
        else:
            text.append(line, style=COLORS['code_fg'])
        if index != len(lines) - 1:
            text.append("\n")
    
    return Panel(
        text,
        title=title,
        border_style=COLORS['border_success'],
        style=CODE_BLOCK_STYLE,
        expand=False,
    )


def _render_kv_block(body: str, title: str, border_style: str):
    """渲染键值对块（YAML/INI/TOML）。"""
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style=f"bold {border_style}",
        expand=True,
        border_style=COLORS['border_default'],
        padding=(0, 2),
    )
    table.add_column("Key", overflow="fold", style=COLORS['code_keyword'])
    table.add_column("Value", overflow="fold", style=COLORS['code_string'])
    
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
    
    return Panel(
        table,
        title=title,
        border_style=COLORS['border_default'],
        expand=False,
    )


def _render_sql_block(body: str):
    """渲染 SQL 代码块，带语法高亮。"""
    keywords = {
        "select", "from", "where", "group", "by", "order", "limit", "insert",
        "into", "values", "update", "set", "delete", "join", "left", "right",
        "inner", "outer", "and", "or", "as", "on", "having", "create", "table",
        "drop", "alter", "add", "primary", "key", "foreign", "references",
        "null", "not", "unique", "index", "view", "with", "case", "when",
        "then", "else", "end", "union", "all", "distinct", "count", "sum",
        "avg", "min", "max", "exists", "in", "like", "between", "is", "cast",
    }
    
    text = Text()
    token_re = re.compile(r"(\s+|,|\(|\)|;|>=|<=|!=|=|>|<)")
    
    for token in token_re.split(body):
        if not token:
            continue
        if token.isspace() or token in {",", "(", ")", ";", ">=", "<=", "!=", "=", ">", "<"}:
            text.append(token)
        elif token.lower() in keywords:
            text.append(token.upper(), style=f"bold {COLORS['code_keyword']}")
        elif token.startswith("'") or token.startswith('"'):
            text.append(token, style=f"{COLORS['code_string']}")
        elif token.replace(".", "").isdigit():
            text.append(token, style=f"{COLORS['code_number']}")
        else:
            text.append(token, style=COLORS['code_fg'])
    
    return Panel(
        text,
        title="sql",
        border_style=COLORS['border_cyan'],
        style=CODE_BLOCK_STYLE,
        expand=False,
    )


def _render_csv_block(body: str):
    """渲染 CSV 表格。"""
    lines = [line for line in body.splitlines() if line.strip()]
    if not lines:
        return Panel(Text(body), title="csv", border_style=COLORS['border_info'])
    
    rows = [line.split(",") for line in lines]
    headers = rows[0]
    
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style=f"bold {COLORS['info']}",
        expand=True,
        border_style=COLORS['border_default'],
        padding=(0, 2),
    )
    
    for header in headers:
        table.add_column(header.strip() or " ", overflow="fold")
    
    for row in rows[1:]:
        normalized = [cell.strip() for cell in row] + [""] * max(0, len(headers) - len(row))
        table.add_row(*normalized[: len(headers)])
    
    return Panel(
        table,
        title="csv",
        border_style=COLORS['border_info'],
        expand=False,
    )


def _render_code_block(body: str, language: str = "code"):
    """通用代码块渲染，带语法高亮支持。"""
    text = Text(body, style=COLORS['code_fg'])
    
    return Panel(
        text,
        title=language or "code",
        border_style=COLORS['border_default'],
        style=CODE_BLOCK_STYLE,
        expand=False,
    )


def _render_flowchart_block(body: str, orientation: str | None = None):
    """渲染流程图块。"""
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
        return Panel(Text(body), title=title, border_style=COLORS['border_magenta'])
    
    ascii_flow = _render_ascii_flowchart(nodes, edges, orientation=orientation)
    
    return Panel(
        Text(ascii_flow, style=COLORS['code_fg']),
        title=title,
        border_style=COLORS['border_magenta'],
        style=CODE_BLOCK_STYLE,
        expand=False,
    )


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
