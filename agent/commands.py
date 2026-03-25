"""
Slash 命令系统：Command 基类、CommandRegistry、CommandContext 与 DispatchResult。

用法（在 main.py 中）：
    1. 调用 `command_registry.register(name, description, handler, aliases)` 注册命令
    2. 在主循环中调用 `command_registry.dispatch(user_input, ctx)` 路由

设计原则：
    - commands.py 只定义**结构**，不耦合任何 wizard 或 agent 实现
    - handler 通过依赖注入（CommandContext）获取 console / agent 引用
    - 补全列表 (slash_completion_list) 由注册表自动生成，无需手动维护
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from rich.console import Console


# ---------------------------------------------------------------------------
# DispatchResult 常量
# ---------------------------------------------------------------------------

class DispatchResult:
    """dispatch() 方法的返回值枚举。"""
    HANDLED = "handled"          # 命令已执行；主循环应 continue
    EXIT = "exit"                # 退出程序；主循环应 break
    NOT_A_COMMAND = "not_a"      # 非斜杠命令或未知命令；交给 LLM 处理


# ---------------------------------------------------------------------------
# CommandContext（运行时上下文，传给 handler）
# ---------------------------------------------------------------------------

@dataclass
class CommandContext:
    """命令执行所需的运行时依赖，由主循环在调用前填充。"""
    console: "Console"
    agent: object          # ChatAgent 实例
    args: str = ""         # 命令后跟随的参数字符串（如 /history 5 → args="5"）


# ---------------------------------------------------------------------------
# Command（命令描述载体）
# ---------------------------------------------------------------------------

@dataclass
class Command:
    """
    描述一条 slash 命令的元信息与处理函数。

    Attributes:
        name        主命令名，含 / 前缀（如 "/help"）
        description 一句话描述（用于补全菜单和 /help 展示）
        handler     Callable[[CommandContext], str]，返回 DispatchResult.* 常量
        aliases     备用命令名列表（均含 / 前缀，如 ["/quit"] 是 "/exit" 的别名）
    """
    name: str
    description: str
    handler: Callable[["CommandContext"], str]
    aliases: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CommandRegistry
# ---------------------------------------------------------------------------

class CommandRegistry:
    """
    命令注册表：管理所有斜杠命令，提供路由分发功能。

    示例::

        registry = CommandRegistry()

        def _handle_help(ctx: CommandContext) -> str:
            ctx.console.print("帮助内容...")
            return DispatchResult.HANDLED

        registry.register("/help", "查看帮助", _handle_help, aliases=[])

        # 主循环中：
        ctx = CommandContext(console=console, agent=agent)
        result = registry.dispatch(user_input, ctx)
        if result == DispatchResult.EXIT:
            break
        elif result == DispatchResult.HANDLED:
            continue
        # else: NOT_A_COMMAND → 交给 LLM
    """

    def __init__(self) -> None:
        # 内部映射：命令名（小写，含别名）→ Command
        self._map: dict[str, Command] = {}
        # 保留注册顺序，供 /help 按顺序展示
        self._ordered: list[Command] = []

    # ------------------------------------------------------------------
    # 注册
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[["CommandContext"], str],
        aliases: list[str] | None = None,
    ) -> Command:
        """
        注册一条斜杠命令。

        Args:
            name        主命令名（含 /，如 "/help"）
            description 一句话描述
            handler     处理函数，接受 CommandContext，返回 DispatchResult.*
            aliases     别名列表（均含 /）

        Returns:
            注册后的 Command 对象（通常无需使用）。
        """
        cmd = Command(
            name=name,
            description=description,
            handler=handler,
            aliases=aliases or [],
        )
        self._map[name.lower()] = cmd
        for alias in cmd.aliases:
            self._map[alias.lower()] = cmd
        self._ordered.append(cmd)
        return cmd

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get(self, name: str) -> Command | None:
        """按名称（或别名）查找命令，不存在返回 None。"""
        return self._map.get(name.lower())

    def all_commands(self) -> list[Command]:
        """按注册顺序返回所有主命令（不含别名副本）。"""
        return list(self._ordered)

    def slash_completion_list(self) -> list[tuple[str, str]]:
        """
        返回 [(命令名, 描述), ...] 供 prompt_toolkit 补全菜单使用。
        主命令与别名均包含，按名称字母序排序。
        """
        return sorted((name, cmd.description) for name, cmd in self._map.items())

    # ------------------------------------------------------------------
    # 分发
    # ------------------------------------------------------------------

    def dispatch(self, user_input: str, ctx: CommandContext) -> str:
        """
        将用户输入路由到匹配的命令处理函数。

        规则：
            - 输入必须以 "/" 开头，否则返回 NOT_A_COMMAND
            - 命令名后可跟参数（空格分隔），写入 ctx.args
            - 命令名未匹配（未知 / 命令）同样返回 NOT_A_COMMAND，由上层决定是否转发 LLM

        Args:
            user_input  原始用户输入（未做 strip/lower）
            ctx         CommandContext，args 会在匹配后被覆写

        Returns:
            DispatchResult.HANDLED  — 命令已处理，主循环 continue
            DispatchResult.EXIT     — 退出程序，主循环 break
            DispatchResult.NOT_A_COMMAND — 非命令或未知命令，交给 LLM
        """
        stripped = user_input.strip()
        if not stripped.startswith("/"):
            return DispatchResult.NOT_A_COMMAND

        parts = stripped.split(None, 1)
        cmd_name = parts[0].lower()
        ctx.args = parts[1] if len(parts) > 1 else ""

        cmd = self.get(cmd_name)
        if cmd is None:
            return DispatchResult.NOT_A_COMMAND

        return cmd.handler(ctx)


# ---------------------------------------------------------------------------
# 全局注册表单例（由 main.py 调用 register 填充）
# ---------------------------------------------------------------------------

command_registry = CommandRegistry()
