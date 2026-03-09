"""
AnsysAgent - Maxwell Motor EM Simulation Assistant
Usage: python main.py
"""

import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

load_dotenv()

console = Console()


def main():
    # Validate environment
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Error: ANTHROPIC_API_KEY not set. Create a .env file with ANTHROPIC_API_KEY=...[/red]")
        sys.exit(1)

    from agent.chat_agent import ChatAgent

    agent = ChatAgent()

    console.print(Panel.fit(
        "[bold cyan]Ansys Maxwell Motor EM Simulation Assistant[/bold cyan]\n"
        "Specialized in electric motor electromagnetic simulation via AEDT 2024\n\n"
        "[dim]Type your request in natural language. Examples:\n"
        "  • 帮我建一个36槽6极的永磁同步电机，外径150mm，转子外径85mm\n"
        "  • 运行磁静态仿真并获取转矩\n"
        "  • 导出反电动势波形到 /tmp/bemf.csv\n"
        "  • quit 退出[/dim]",
        title="🤖 AnsysAgent",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        console.print()
        try:
            response = agent.chat(user_input)
            console.print(Panel(
                Markdown(response),
                title="[bold blue]Assistant[/bold blue]",
                border_style="blue",
            ))
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
