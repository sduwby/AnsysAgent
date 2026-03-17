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

from agent.config_manager import run_config_wizard
from agent.logger import setup_logging, get_logger


def _find_env_path() -> Path:
    """
    定位 .env 文件路径，兼容开发模式和 PyInstaller 打包模式。

    优先级（从高到低）：
      1. {tmp}/.AnsysAgent/.env  —— 用户通过 /config 保存的配置（可写，跨模式统一）
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


WELCOME = (
    "[bold cyan]Ansys 电机仿真智能助手[/bold cyan]\n"
    "支持电磁仿真、热分析、NVH结构振动、Circuit联仿、参数化扫描与 optiSLang 优化\n"
    "基于 AEDT 2024，支持 DeepSeek / ChatGPT / Claude / Qwen / Gemini\n\n"
    "[dim]输入自然语言描述需求，例如：\n"
    "  • 帮我建一个36槽6极的永磁同步电机，外径150mm\n"
    "  • 运行磁静态仿真并获取转矩\n"
    "  • 导出反电动势波形到 /tmp/bemf.csv\n"
    "  输入 /config 修改 LLM 配置 | 输入 /exit 或按 Ctrl+C 退出[/dim]"
)


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

    while True:
        try:
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


if __name__ == "__main__":
    cli()

