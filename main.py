"""
AnsysAgent - Maxwell 电机电磁仿真助手
安装后可用命令：ansys-agent
"""

import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

load_dotenv()

console = Console()
VERSION = "0.1.0"

WELCOME = (
    "[bold cyan]Ansys 电机仿真智能助手[/bold cyan]\n"
    "支持电磁仿真、热分析、NVH结构振动、Circuit联仿、参数化扫描与 optiSLang 优化\n"
    "基于 AEDT 2024 + DeepSeek\n\n"
    "[dim]输入自然语言描述需求，例如：\n"
    "  • 帮我建一个36槽6极的永磁同步电机，外径150mm\n"
    "  • 运行磁静态仿真并获取转矩\n"
    "  • 导出反电动势波形到 /tmp/bemf.csv\n"
    "  输入 /exit 或按 Ctrl+C 退出[/dim]"
)


def _stream_response(agent, user_input: str) -> None:
    """流式渲染 agent 回复，工具调用实时显示。"""
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
        try:
            _stream_response(agent, prompt)
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")
            sys.exit(1)
        return

    # 交互模式
    console.print(Panel.fit(WELCOME, title="🤖 AnsysAgent", border_style="cyan"))

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]用户[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]再见。[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("/exit", "/quit", "quit", "exit", "q", "退出"):
            console.print("[dim]再见。[/dim]")
            break

        try:
            _stream_response(agent, user_input)
        except KeyboardInterrupt:
            console.print("\n[yellow]已中断。[/yellow]")
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")


if __name__ == "__main__":
    cli()

