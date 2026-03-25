"""
AnsysAgent - Maxwell 电机电磁仿真助手
安装后可用命令：ansys-agent
"""

import random
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.styles import Style as PtkStyle
    _PTK_AVAILABLE = True
except ImportError:
    _PTK_AVAILABLE = False

from agent.config_manager import run_config_wizard
from agent.logger import setup_logging, get_logger
from agent.role_manager import RoleManager, MAX_ROLES, MAX_LINES


def _find_env_path() -> Path:
    """
    定位 .env 文件路径，兼容开发模式和 PyInstaller 打包模式。

    优先级（从高到低）：
      1. {ANSYS_DATA_DIR}/.env  —— 用户通过 /config 保存的配置（可写，跨模式统一）
      2. 打包内置 _MEIPASS/.env  —— 随包附带的默认配置（只读，fallback）
      3. 项目根目录 .env        —— 开发模式 fallback
    """
    from agent.paths import ANSYS_DATA_DIR
    user_env = ANSYS_DATA_DIR / ".env"
    if user_env.exists():
        return user_env
    if getattr(sys, "frozen", False):
        bundled_env = Path(sys._MEIPASS) / ".env"  # type: ignore[attr-defined]
        if bundled_env.exists():
            return bundled_env
    # 开发模式：当前目录
    return Path(".env")


load_dotenv(_find_env_path())

# 初始化文件日志（加载 .env 之后立即执行）
setup_logging()
_log = get_logger("main")

# 启动日志查看 HTTP server（后台守护线程）
from agent.log_server import start_log_server as _start_log_server
_log_port = _start_log_server()

console = Console()
VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# 彩蛋素材
# ---------------------------------------------------------------------------

_COFFEE_ART = r"""
        ( (         ) )
      _____)_____(_____(
     |   ___________   |
     |  |           |  |
     |  |   ☕ ☕   |  |
     |  |___________|  |
     |_________________|
           |     |
         [_______|_]
"""

_MOTOR_ART = r"""
          ╔═══════════════════╗
          ║  ┌─────────────┐  ║
          ║  │  ╔═══════╗  │  ║
     >>==>║  │  ║  ⚡●  ║──╫══>> τ
          ║  │  ╚═══════╝  │  ║
          ║  └─────────────┘  ║
          ╚═══════════════════╝
              🔄  PMSM 36S/6P
"""

_STARTUP_QUOTES = [
    "今天也是元气满满地仿真的一天！🚀",
    "磁场不会说谎，但收敛需要耐心。🧲",
    "记住：网格越细，账期越长。📐",
    "一切玄学问题都可以用更细的网格解决。",
    "铁损也是损，省一分是一分。⚡",
    "转矩脉动不大，大的是截止日期。📅",
    "仿真跑完前，结果永远是薛定谔的猫。🐱",
    "永磁体不会累，但工程师会。",
]


def _maybe_show_startup_egg() -> None:
    """10% 概率在启动时显示一句工程师名言。"""
    if random.random() < 0.1:
        quote = random.choice(_STARTUP_QUOTES)
        console.print(Panel(
            f"[italic yellow]{quote}[/italic yellow]",
            title="💡 今日格言",
            border_style="dim yellow",
            expand=False,
        ))


# ---------------------------------------------------------------------------
# /命令自动补全
# ---------------------------------------------------------------------------

_SLASH_COMMANDS = [
    ("/help",   "查看帮助"),
    ("/config", "配置 LLM 提供商和 API Key"),
    ("/roles",  "管理 AI 角色（添加/修改/删除）"),
    ("/skills", "管理专业流程技能"),
    ("/mcp",    "管理 MCP server"),
    ("/clear",  "清空对话历史，开始新对话"),
    ("/new",    "清空对话历史，开始新对话"),
    ("/purge",  "删除所有本地数据（不可撤销）"),
    ("/clean",  "删除所有本地数据（不可撤销）"),
    ("/exit",   "退出程序"),
    ("/quit",   "退出程序"),
    ("/coffee", "☕ 彩蛋"),
    ("/motor",  "⚡ 彩蛋"),
]

if _PTK_AVAILABLE:
    class _SlashCompleter(Completer):
        """仅在输入以 '/' 开头时触发补全，实时按前缀过滤命令列表。"""

        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith("/"):
                return
            prefix = text.lower()
            for cmd, desc in _SLASH_COMMANDS:
                if cmd.startswith(prefix):
                    # 补全从当前输入位置开始（替换已输入的部分）
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display=HTML(f"<b>{cmd}</b>  <ansibrightblack>{desc}</ansibrightblack>"),
                    )

    _PTK_STYLE = PtkStyle.from_dict({
        "completion-menu.completion": "bg:#1e1e2e #cdd6f4",
        "completion-menu.completion.current": "bg:#89b4fa #1e1e2e bold",
        "scrollbar.background": "bg:#313244",
        "scrollbar.button": "bg:#89b4fa",
    })

    def _make_prompt_session() -> "PromptSession":
        return PromptSession(
            completer=_SlashCompleter(),
            complete_while_typing=True,
            style=_PTK_STYLE,
        )
else:
    def _make_prompt_session():  # type: ignore[misc]
        return None


WELCOME = (
    "[bold cyan]Ansys 电机仿真智能助手[/bold cyan]\n"
    "支持电磁仿真、热分析、NVH结构振动、Circuit联仿、参数化扫描与 optiSLang 优化\n"
    "基于 AEDT 2024，支持 DeepSeek / ChatGPT / Claude / Qwen / Gemini\n\n"
    "[dim]输入自然语言描述需求，例如：\n"
    "  • 帮我建一个36槽6极的永磁同步电机，外径150mm\n"
    "  • 运行磁静态仿真并获取转矩\n"
    "  • 导出反电动势波形到 /tmp/bemf.csv\n"
    "  /help 查看帮助 | /config 配置 LLM | /roles 管理角色 | /skills 管理技能 | /mcp 管理 MCP | /exit 退出[/dim]\n"
    f"[dim]📋 Log viewer: http://localhost:{{_log_port}}[/dim]"
)


# ---------------------------------------------------------------------------
# Roles 向导
# ---------------------------------------------------------------------------

def _read_multiline_content(console: Console, prompt_hint: str = "") -> str:
    """
    交互式读取多行内容。
    用户输入完毕后，在空行连续按两次 Enter（即输入一个空行后再 Enter）结束。
    返回完整内容字符串。
    """
    if prompt_hint:
        console.print(f"[dim]{prompt_hint}[/dim]")
    console.print("[dim]逐行输入内容，完成后连续按两次 Enter 结束：[/dim]")
    lines: list[str] = []
    prev_empty = False
    while True:
        try:
            line = input()
        except (KeyboardInterrupt, EOFError):
            if prev_empty:
                lines.append("")
            break
        if line == "":
            if prev_empty:
                break  # 连续两次空行 → 结束
            prev_empty = True
            continue
        if prev_empty:
            lines.append("")  # 保留中间的单个空行
            prev_empty = False
        lines.append(line)
    return "\n".join(lines).strip()


def run_roles_wizard(console: Console) -> None:
    """
    Rich 交互式 Roles 管理向导。
    支持：列表查看、添加、删除、修改。
    """
    rm = RoleManager()

    while True:
        roles = rm.list_roles()

        # ── 显示当前 roles ─────────────────────────────────────────────
        if roles:
            role_lines = "\n".join(
                f"  [{i+1}] {name}  ({len((rm.get_role(name) or '').splitlines())} 行)"
                for i, name in enumerate(roles)
            )
        else:
            role_lines = "  （暂无 role）"

        console.print(Panel(
            role_lines,
            title=f"当前 Roles（{len(roles)}/{MAX_ROLES}）",
            border_style="blue",
        ))

        # ── 操作菜单 ──────────────────────────────────────────────────
        console.print("\n[bold]选择操作[/bold]（Enter 退出）:")
        console.print("  [1] 查看 role 内容")
        console.print("  [2] 添加新 role")
        console.print("  [3] 修改已有 role")
        console.print("  [4] 删除 role")

        choice = Prompt.ask("  操作编号", default="").strip()

        if choice == "":
            break

        # ── [1] 查看 ──────────────────────────────────────────────────
        if choice == "1":
            if not roles:
                console.print("[yellow]  暂无 role 可查看[/yellow]")
                continue
            name = Prompt.ask("  输入 role 名称").strip()
            content = rm.get_role(name)
            if content is None:
                console.print(f"[red]  Role '{name}' 不存在[/red]")
            else:
                console.print(Panel(content, title=f"Role: {name}", border_style="dim"))

        # ── [2] 添加 ──────────────────────────────────────────────────
        elif choice == "2":
            if len(roles) >= MAX_ROLES:
                console.print(f"[red]  已达到最大数量（{MAX_ROLES} 个），请先删除一个[/red]")
                continue
            name = Prompt.ask("  新 role 名称").strip()
            if not name:
                console.print("[yellow]  名称不能为空[/yellow]")
                continue
            content = _read_multiline_content(
                console,
                f"请输入 role 内容（最多 {MAX_LINES} 行）："
            )
            if not content:
                console.print("[yellow]  内容为空，已取消[/yellow]")
                continue
            ok, msg = rm.add_role(name, content)
            color = "green" if ok else "red"
            console.print(f"[{color}]  {msg}[/{color}]")

        # ── [3] 修改 ──────────────────────────────────────────────────
        elif choice == "3":
            if not roles:
                console.print("[yellow]  暂无 role 可修改[/yellow]")
                continue
            name = Prompt.ask("  要修改的 role 名称").strip()
            existing = rm.get_role(name)
            if existing is None:
                console.print(f"[red]  Role '{name}' 不存在[/red]")
                continue
            console.print(f"[dim]当前内容（{len(existing.splitlines())} 行），下面输入新内容：[/dim]")
            content = _read_multiline_content(
                console,
                f"请输入新内容（最多 {MAX_LINES} 行）："
            )
            if not content:
                console.print("[yellow]  内容为空，已取消[/yellow]")
                continue
            ok, msg = rm.update_role(name, content)
            color = "green" if ok else "red"
            console.print(f"[{color}]  {msg}[/{color}]")

        # ── [4] 删除 ──────────────────────────────────────────────────
        elif choice == "4":
            if not roles:
                console.print("[yellow]  暂无 role 可删除[/yellow]")
                continue
            name = Prompt.ask("  要删除的 role 名称").strip()
            confirm = Prompt.ask(f"  确认删除 '{name}'？(y/N)", default="n").strip().lower()
            if confirm == "y":
                ok, msg = rm.delete_role(name)
                color = "green" if ok else "red"
                console.print(f"[{color}]  {msg}[/{color}]")
            else:
                console.print("[dim]  已取消[/dim]")

        else:
            console.print("[yellow]  无效选项[/yellow]")


# ---------------------------------------------------------------------------
# Skills 向导
# ---------------------------------------------------------------------------

def run_skills_wizard(console: Console) -> None:
    """Rich 交互式 Skills 管理向导。"""
    from agent.skill_manager import SkillManager
    sm = SkillManager.get_instance()

    while True:
        sm.reload()
        skills = sm.get_available_skills()

        # ── 显示技能列表 ───────────────────────────────────────────────
        if skills:
            lines = []
            for skill in skills:
                tag = "[dim](内置)[/dim]" if not sm.is_user_skill(skill.name) else "[green](用户)[/green]"
                desc = skill.description[:50] + ("…" if len(skill.description) > 50 else "")
                lines.append(f"  {tag} [bold]{skill.name}[/bold]\n       {desc}")
            panel_text = "\n".join(lines)
        else:
            panel_text = "  （暂无技能）"

        console.print(Panel(
            panel_text,
            title=f"可用技能（{len(skills)} 个）",
            border_style="magenta",
        ))

        # ── 操作菜单 ──────────────────────────────────────────────────
        console.print("\n[bold]选择操作[/bold]（Enter 退出）:")
        console.print("  [1] 查看技能内容")
        console.print("  [2] 添加用户自定义技能")
        console.print("  [3] 删除用户自定义技能")

        choice = Prompt.ask("  操作编号", default="").strip()
        if choice == "":
            break

        # ── [1] 查看 ──────────────────────────────────────────────────
        if choice == "1":
            if not skills:
                console.print("[yellow]  暂无技能可查看[/yellow]")
                continue
            name = Prompt.ask("  技能名称").strip()
            skill = sm.get_skill(name)
            if skill is None:
                console.print(f"[red]  技能 '{name}' 不存在[/red]")
            else:
                preview = skill.content[:3000] + ("\n…（内容过长，已截断）" if len(skill.content) > 3000 else "")
                console.print(Panel(preview, title=f"Skill: {name}", border_style="dim"))

        # ── [2] 添加 ──────────────────────────────────────────────────
        elif choice == "2":
            name = Prompt.ask("  技能名称（英文或中文，用于目录命名）").strip()
            if not name:
                console.print("[yellow]  名称不能为空[/yellow]")
                continue
            description = Prompt.ask("  技能简介（一句话描述）").strip()
            if not description:
                console.print("[yellow]  简介不能为空[/yellow]")
                continue
            content = _read_multiline_content(console, "请输入技能正文内容（Markdown 格式）：")
            if not content:
                console.print("[yellow]  内容为空，已取消[/yellow]")
                continue
            ok, msg = sm.create_user_skill(name, description, content)
            color = "green" if ok else "red"
            console.print(f"[{color}]  {msg}[/{color}]")

        # ── [3] 删除 ──────────────────────────────────────────────────
        elif choice == "3":
            user_skills = [s.name for s in skills if sm.is_user_skill(s.name)]
            if not user_skills:
                console.print("[yellow]  暂无可删除的用户自定义技能（内置技能不可删除）[/yellow]")
                continue
            name = Prompt.ask("  要删除的技能名称").strip()
            confirm = Prompt.ask(f"  确认删除 '{name}'？(y/N)", default="n").strip().lower()
            if confirm == "y":
                ok, msg = sm.delete_user_skill(name)
                color = "green" if ok else "red"
                console.print(f"[{color}]  {msg}[/{color}]")
            else:
                console.print("[dim]  已取消[/dim]")

        else:
            console.print("[yellow]  无效选项[/yellow]")


# ---------------------------------------------------------------------------
# MCP 向导
# ---------------------------------------------------------------------------

def run_mcp_wizard(console: Console, mcp_manager) -> None:
    """Rich 交互式 MCP 管理向导。"""
    if not mcp_manager or not getattr(mcp_manager, "_available", False):
        console.print(Panel(
            "[red]MCP 功能不可用[/red]：mcp 包未安装。\n"
            "请运行：[bold]pip install mcp duckduckgo-mcp-server[/bold]",
            title="MCP 状态",
            border_style="red",
        ))
        return

    from agent.mcp_manager import MCP_CONFIG_PATH

    while True:
        servers = mcp_manager.get_server_info()

        # ── 显示 server 状态 ──────────────────────────────────────────
        if servers:
            lines = []
            for srv in servers:
                if srv["connected"]:
                    status = "[green]● 已连接[/green]"
                elif not srv["enabled"]:
                    status = "[dim]○ 已禁用[/dim]"
                else:
                    status = "[red]✗ 未连接[/red]"
                desc = srv["description"][:45] + ("…" if len(srv["description"]) > 45 else "")
                lines.append(
                    f"  {status} [bold]{srv['name']}[/bold]  ({srv['tool_count']} tools)\n"
                    f"       [dim]{desc}[/dim]"
                )
            panel_text = "\n".join(lines)
        else:
            panel_text = "  （无 MCP server 配置）"

        console.print(Panel(
            panel_text,
            title=f"MCP Servers（配置文件: {MCP_CONFIG_PATH}）",
            border_style="cyan",
        ))

        # ── 操作菜单 ──────────────────────────────────────────────────
        console.print("\n[bold]选择操作[/bold]（Enter 退出）:")
        console.print("  [1] 查看某 server 的可用工具")
        console.print("  [2] 禁用 server")
        console.print("  [3] 启用 server")
        console.print("  [4] 重新连接所有 server（热重载）")

        choice = Prompt.ask("  操作编号", default="").strip()
        if choice == "":
            break

        # ── [1] 查看工具 ──────────────────────────────────────────────
        if choice == "1":
            name = Prompt.ask("  Server 名称").strip()
            tools = [k for k, v in mcp_manager._tool_to_server.items() if v == name]
            if not tools:
                console.print(f"[yellow]  '{name}' 暂无可用工具（未连接或不存在）[/yellow]")
            else:
                tool_list = "\n".join(f"  • {t}" for t in sorted(tools))
                console.print(Panel(tool_list, title=f"{name} 工具列表", border_style="dim"))

        # ── [2] 禁用 ──────────────────────────────────────────────────
        elif choice == "2":
            name = Prompt.ask("  要禁用的 server 名称").strip()
            ok, msg = mcp_manager.toggle_server(name, enabled=False)
            color = "green" if ok else "red"
            console.print(f"[{color}]  {msg}[/{color}]")

        # ── [3] 启用 ──────────────────────────────────────────────────
        elif choice == "3":
            name = Prompt.ask("  要启用的 server 名称").strip()
            ok, msg = mcp_manager.toggle_server(name, enabled=True)
            color = "green" if ok else "red"
            console.print(f"[{color}]  {msg}[/{color}]")

        # ── [4] 重新连接 ───────────────────────────────────────────────
        elif choice == "4":
            console.print("[dim]  正在重新连接所有 MCP server…[/dim]")
            result_msg = mcp_manager.reconnect()
            color = "green" if "成功" in result_msg else "yellow"
            console.print(f"[{color}]  {result_msg}[/{color}]")

        else:
            console.print("[yellow]  无效选项[/yellow]")


# ---------------------------------------------------------------------------
# 帮助
# ---------------------------------------------------------------------------

def _show_help(console: Console) -> None:
    """用多块彩色 Panel 展示功能指南，风格与 /config 一致。"""
    from agent.paths import ANSYS_DATA_DIR

    data_dir = str(ANSYS_DATA_DIR)

    # ── 标题 ──────────────────────────────────────────────────────────────
    console.print(Panel(
        "[bold cyan]AnsysAgent 功能指南[/bold cyan]\n"
        "[dim]输入对应命令进入交互向导，或直接用自然语言描述仿真需求。[/dim]",
        border_style="cyan",
        padding=(0, 2),
    ))

    # ── /config ───────────────────────────────────────────────────────────
    console.print(Panel(
        "  交互式配置 LLM 提供商、API Key 和模型\n"
        "  支持：[cyan]DeepSeek / OpenAI / Qwen / Gemini / GLM / MiniMax[/cyan]\n"
        f"  配置持久化至：[dim]{data_dir}/.env[/dim]",
        title="[bold green]/config[/bold green]  — LLM 配置",
        border_style="green",
        padding=(0, 2),
    ))

    # ── /roles ────────────────────────────────────────────────────────────
    console.print(Panel(
        '  为 AI 设置自定义角色行为（如"用中文回答"、"专注于电磁仿真"等）\n'
        "  操作：[yellow]添加（add）/ 修改（change）/ 删除（delete）/ 查看[/yellow]\n"
        "  每次对话前自动注入到系统提示词\n"
        "  限制：最多 [bold]5[/bold] 个角色，每个最多 [bold]200[/bold] 行\n"
        f"  存储位置：[dim]{data_dir}/roles/[/dim]",
        title="[bold yellow]/roles[/bold yellow]  — 角色管理",
        border_style="yellow",
        padding=(0, 2),
    ))

    # ── Skill ─────────────────────────────────────────────────────────────
    console.print(Panel(
        "  AI 可主动调用 [cyan]use_skill[/cyan] 工具加载专业仿真流程指南\n"
        "  内置技能：\n"
        "    • [bold]maxwell-motor-workflow[/bold]  Maxwell 电机 2D 仿真标准流程\n"
        "    • [bold]thermal-em-coupling[/bold]     电磁-热耦合仿真流程\n"
        "  用 [bold]/skills[/bold] 管理技能：查看 / 添加用户自定义技能 / 删除\n"
        "  自定义技能存储目录：\n"
        f"    [dim]{data_dir}/skills/[/dim]\n"
        "  文件格式：YAML frontmatter（name / description）+ Markdown 正文",
        title="[bold magenta]/skills[/bold magenta]      — 专业流程指南",
        border_style="magenta",
        padding=(0, 2),
    ))

    # ── RAG ───────────────────────────────────────────────────────────────
    console.print(Panel(
        "  自动检索本地知识文档辅助 AI 回答 API 用法、错误处理、仿真步骤等\n"
        "  内置文档：[dim]docs/api/[/dim]（API 速查表）、[dim]knowledge/official/[/dim]（官方教程）\n"
        f"  自定义文档：将 PDF / PPTX / IPYNB 等放入 [dim]{data_dir}/knowledge/internal/[/dim]\n"
        '              然后告诉 AI "重建知识索引"\n'
        f"  索引缓存：[dim]{data_dir}/.rag/keyword_index.json[/dim]\n"
        "  （删除缓存文件可强制从头重建索引）",
        title="[bold blue]RAG[/bold blue]         — 本地知识库",
        border_style="blue",
        padding=(0, 2),
    ))

    # ── 其他命令 ──────────────────────────────────────────────────────────
    console.print(Panel(
        "  [dim]/clear  /new[/dim]   → 清空对话历史，开始新对话\n"
        "  [dim]/purge  /clean[/dim] → [red]删除所有本地数据[/red]（配置/索引/日志/角色/技能），不可撤销\n"
        "  [dim]/mcp[/dim]            → 管理 MCP server（查看状态 / 启用 / 禁用工具）\n"
        "  [dim]/exit  /quit[/dim]   → 退出程序（也可按 Ctrl+C）\n"
        "  [dim]/coffee[/dim]        → ☕ 彩蛋\n"
        "  [dim]/motor[/dim]         → ⚡ 彩蛋",
        title="其他命令",
        border_style="dim",
        padding=(0, 2),
    ))


def _stream_response(agent, user_input: str) -> str:
    """流式渲染 agent 回复，工具调用实时显示。返回完整回复文本（用于日志）。"""
    text_buf = ""
    in_text = False

    for chunk in agent.chat_stream(user_input):
        if chunk.startswith("\x00TOOL\x00"):
            # 工具调用通知
            payload = chunk[len("\x00TOOL\x00"):]
            console.print(f"[dim]🔧 调用工具: [bold]{payload.split(':', 1)[0]}[/bold][/dim]")
        elif chunk.startswith("\x00TOOL_RESULT\x00"):
            # 工具执行结果
            result = chunk[len("\x00TOOL_RESULT\x00"):]
            color = "green" if result.startswith("✓") else "red"
            console.print(f"[{color}]  {result}[/{color}]")
        else:
            # 正常文本 token，累积后流式输出
            text_buf += chunk
            if not in_text:
                in_text = True
                console.print()  # 换行，与工具输出分隔

            # 直接打印每个 token（不等待整段完成）
            console.print(chunk, end="", highlight=False, markup=False)

    if in_text:
        console.print()  # 最后换行

    return text_buf


@click.command()
@click.version_option(VERSION, prog_name="ansys-agent")
@click.option(
    "-p", "--prompt",
    default=None,
    help="直接执行单条指令后退出（不进入交互模式）",
)
def cli(prompt: str | None):
    """Ansys Maxwell 电机电磁仿真 AI 助手。"""
    from agent.chat_agent import ChatAgent

    agent = ChatAgent()
    try:
        if prompt:
            # 单次执行模式：ansys-agent -p "..."
            _log.info("单次执行模式 | 指令: %s", prompt)
            try:
                reply = _stream_response(agent, prompt)
                _log.info("回复: %s", reply[:500] + ("..." if len(reply) > 500 else ""))
            except Exception as e:
                _log.error("单次执行失败: %s", e, exc_info=True)
                console.print(f"[red]错误: {e}[/red]")
                sys.exit(1)
            return

        # 交互模式
        _log.info("进入交互模式")
        console.print(Panel.fit(WELCOME, title="🤖 AnsysAgent", border_style="cyan"))
        _maybe_show_startup_egg()

        # 初始化 prompt_toolkit 会话（支持 /命令自动补全）
        ptk_session = _make_prompt_session()

        while True:
            try:
                if ptk_session is not None:
                    user_input = ptk_session.prompt("\n用户> ").strip()
                else:
                    user_input = Prompt.ask("\n[bold green]用户[/bold green]").strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]再见。[/dim]")
                _log.info("用户退出（KeyboardInterrupt/EOFError）")
                break

            if not user_input:
                continue
            if user_input.lower() in ("/exit", "/quit", "quit", "exit", "q", "退出"):
                console.print("[dim]再见。[/dim]")
                _log.info("用户主动退出")
                break
            if user_input.lower() == "/coffee":
                console.print(f"[yellow]{_COFFEE_ART}[/yellow]")
                console.print("[bold yellow]⚡ 工程师加燃料完毕，继续仿真！[/bold yellow]")
                continue
            if user_input.lower() == "/motor":
                console.print(f"[cyan]{_MOTOR_ART}[/cyan]")
                console.print("[bold cyan]这就是你在仿真的东西，加油！💪[/bold cyan]")
                continue
            if user_input.lower() == "/config":
                try:
                    run_config_wizard(console)
                    # 热重载 .env → 覆盖 os.environ → 重建 LLM 客户端
                    load_dotenv(override=True)
                    agent.reload_config()
                    console.print("[green]✓ 配置已生效[/green]")
                    _log.info("LLM 配置已变更并热重载")
                except Exception as e:
                    _log.error("配置变更失败: %s", e, exc_info=True)
                    console.print(f"[red]配置失败: {e}[/red]")
                continue
            if user_input.lower() == "/roles":
                try:
                    run_roles_wizard(console)
                    _log.info("用户完成 roles 管理")
                except Exception as e:
                    _log.error("Roles 管理异常: %s", e, exc_info=True)
                    console.print(f"[red]Roles 操作失败: {e}[/red]")
                continue
            if user_input.lower() == "/skills":
                try:
                    run_skills_wizard(console)
                    _log.info("用户完成 skills 管理")
                except Exception as e:
                    _log.error("Skills 管理异常: %s", e, exc_info=True)
                    console.print(f"[red]Skills 操作失败: {e}[/red]")
                continue
            if user_input.lower() == "/mcp":
                try:
                    run_mcp_wizard(console, agent._mcp_manager if hasattr(agent, "_mcp_manager") else None)
                    _log.info("用户完成 MCP 管理")
                except Exception as e:
                    _log.error("MCP 管理异常: %s", e, exc_info=True)
                    console.print(f"[red]MCP 操作失败: {e}[/red]")
                continue
            if user_input.lower() == "/help":
                _show_help(console)
                continue
            if user_input.lower() in ("/clear", "/new", "新建对话"):
                agent.history.clear()
                _log.info("用户清空对话历史")
                console.print("[dim]✓ 对话历史已清空，开始新对话。[/dim]")
                continue
            if user_input.lower() in ("/purge", "/clean", "清除本地数据"):
                from agent.paths import ANSYS_DATA_DIR
                import shutil
                console.print(Panel(
                    f"  即将删除：[bold red]{ANSYS_DATA_DIR}[/bold red]\n"
                    "  包含：.env（LLM 配置）、.rag（知识索引）、logs（日志）、\n"
                    "        roles（角色）、skills（技能）、knowledge（用户知识库）、mcp_servers.json",
                    title="[bold red]⚠ 警告：此操作不可撤销[/bold red]",
                    border_style="red",
                    padding=(0, 2),
                ))
                confirm = Prompt.ask("  确认删除所有本地数据？输入 [bold red]yes[/bold red] 继续", default="no").strip().lower()
                if confirm == "yes":
                    try:
                        shutil.rmtree(ANSYS_DATA_DIR)
                        _log.info("用户清除了所有本地数据: %s", ANSYS_DATA_DIR)
                        console.print(f"[green]✓ 已删除 {ANSYS_DATA_DIR}，程序将退出（下次启动将重新初始化）。[/green]")
                        break
                    except Exception as e:
                        _log.error("清除本地数据失败: %s", e, exc_info=True)
                        console.print(f"[red]删除失败: {e}[/red]")
                else:
                    console.print("[dim]  已取消。[/dim]")
                continue

            _log.info("用户输入: %s", user_input)
            try:
                reply = _stream_response(agent, user_input)
                _log.info("Agent 回复: %s", reply[:500] + ("..." if len(reply) > 500 else ""))
            except KeyboardInterrupt:
                console.print("\n[yellow]已中断。[/yellow]")
                _log.warning("用户中断了当前请求")
            except Exception as e:
                _log.error("处理用户输入时出错: %s", e, exc_info=True)
                console.print(f"[red]错误: {e}[/red]")
    finally:
        try:
            agent.shutdown()
        except Exception as e:
            _log.warning("关闭 Agent 资源时发生异常: %s", e)


if __name__ == "__main__":
    cli()
