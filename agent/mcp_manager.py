"""
MCP (Model Context Protocol) 管理器。

负责：
  - 读取 {ANSYS_DATA_DIR}/mcp_servers.json 配置
  - 以 stdio 协议启动并连接 MCP server 子进程
  - 将 MCP 工具转换为 OpenAI function calling 格式
  - 提供同步接口（内部使用后台线程 + asyncio event loop 解决 SDK 异步问题）

支持的 MCP server 配置格式（mcp_servers.json）：
{
  "server-name": {
    "command": "python",
    "args": ["-m", "some_mcp_server"],
    "env": {},            // 可选，额外环境变量
    "enabled": true,
    "description": "说明"
  }
}
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path
from typing import Any

from agent.paths import ANSYS_DATA_DIR
from agent.logger import get_logger

_log = get_logger("mcp_manager")

# MCP server 配置文件路径
MCP_CONFIG_PATH: Path = ANSYS_DATA_DIR / "mcp_servers.json"

# 默认 MCP servers 配置（首次运行时写入）
_DEFAULT_MCP_SERVERS: dict = {
    "duckduckgo": {
        "command": "python",
        "args": ["-m", "duckduckgo_mcp_server"],
        "env": {},
        "enabled": True,
        "description": "DuckDuckGo web search (free, no API key required)",
    }
}


def _ensure_default_config() -> None:
    """若配置文件不存在，写入默认配置。"""
    if not MCP_CONFIG_PATH.exists():
        MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        MCP_CONFIG_PATH.write_text(
            json.dumps(_DEFAULT_MCP_SERVERS, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        _log.info("已创建默认 MCP 配置: %s", MCP_CONFIG_PATH)


def _load_config() -> dict:
    """读取 mcp_servers.json，返回配置字典。"""
    _ensure_default_config()
    try:
        return json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        _log.warning("读取 MCP 配置失败: %s，使用默认配置", e)
        return _DEFAULT_MCP_SERVERS


# ---------------------------------------------------------------------------
# MCPManager
# ---------------------------------------------------------------------------

class MCPManager:
    """
    同步接口的 MCP 管理器。
    
    在后台线程中运行独立的 asyncio event loop，通过
    run_coroutine_threadsafe 提供线程安全的同步调用接口。
    
    优雅降级：若 mcp 包或 MCP server 不可用，相关工具静默跳过。
    """

    def __init__(self) -> None:
        self._tool_definitions: list[dict] = []   # OpenAI format
        self._tool_to_server: dict[str, str] = {}  # tool_name → server_name
        self._sessions: dict[str, Any] = {}        # server_name → ClientSession
        self._exit_stacks: dict[str, Any] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._available = False

        # 检查 mcp 包是否安装
        try:
            import mcp  # noqa: F401
            self._available = True
        except ImportError:
            _log.warning(
                "mcp 包未安装，MCP 功能不可用。请运行: pip install mcp duckduckgo-mcp-server"
            )
            return

        # 启动后台 event loop 线程
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever,
            name="mcp-event-loop",
            daemon=True,
        )
        self._thread.start()

        # 连接所有启用的 MCP servers
        self._run_sync(self._connect_all())

    # ------------------------------------------------------------------
    # 内部：同步包装
    # ------------------------------------------------------------------

    def _run_sync(self, coro, timeout: float = 30.0):
        """在后台 event loop 中执行协程，阻塞等待结果。"""
        if self._loop is None:
            raise RuntimeError("MCP event loop 未初始化")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ------------------------------------------------------------------
    # 内部：连接管理
    # ------------------------------------------------------------------

    async def _connect_all(self) -> None:
        """读取配置，依次连接所有启用的 MCP servers。"""
        config = _load_config()
        for name, cfg in config.items():
            if not cfg.get("enabled", True):
                continue
            try:
                await self._connect_server(name, cfg)
            except Exception as e:
                _log.warning("连接 MCP server '%s' 失败（已跳过）: %s", name, e)

    async def _connect_server(self, name: str, cfg: dict) -> None:
        """连接单个 MCP server，获取工具列表并注册。"""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from contextlib import AsyncExitStack

        command = cfg["command"]
        args = cfg.get("args", [])
        env = {**os.environ, **cfg.get("env", {})}

        params = StdioServerParameters(command=command, args=args, env=env)

        stack = AsyncExitStack()
        read, write = await stack.enter_async_context(stdio_client(params))
        session: ClientSession = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        self._sessions[name] = session
        self._exit_stacks[name] = stack

        # 获取工具列表
        tools_result = await session.list_tools()
        registered = []
        for tool in tools_result.tools:
            tool_name = f"mcp__{name}__{tool.name}"
            self._tool_to_server[tool_name] = name

            # 转换为 OpenAI function calling 格式
            input_schema = tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}}
            self._tool_definitions.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"[MCP:{name}] {tool.description or tool.name}",
                    "parameters": input_schema,
                },
            })
            registered.append(tool.name)

        _log.info("MCP server '%s' 连接成功，已注册工具: %s", name, registered)

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def get_tool_definitions(self) -> list[dict]:
        """返回所有 MCP 工具的 OpenAI function calling 定义列表。"""
        return list(self._tool_definitions)

    def has_tool(self, tool_name: str) -> bool:
        """检查是否为 MCP 管理的工具。"""
        return tool_name in self._tool_to_server

    def get_server_info(self) -> list[dict]:
        """返回所有已配置 MCP server 的状态信息（供 /mcp 向导展示）。"""
        config = _load_config()
        result = []
        for name, cfg in config.items():
            connected = name in self._sessions
            tool_count = sum(1 for v in self._tool_to_server.values() if v == name)
            result.append({
                "name": name,
                "description": cfg.get("description", ""),
                "enabled": cfg.get("enabled", True),
                "connected": connected,
                "tool_count": tool_count,
            })
        return result

    def toggle_server(self, name: str, enabled: bool) -> tuple[bool, str]:
        """启用或禁用指定 MCP server，更新配置文件（重启后生效）。"""
        config = _load_config()
        if name not in config:
            return False, f"MCP server '{name}' 不存在于配置中"
        config[name]["enabled"] = enabled
        MCP_CONFIG_PATH.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        action = "启用" if enabled else "禁用"
        _log.info("MCP server '%s' 已%s（重启后生效）", name, action)
        return True, f"MCP server '{name}' 已{action}（重启后生效）"

    def reconnect(self) -> str:
        """断开所有 MCP server 连接并重新连接所有启用的 server，返回结果摘要。"""
        if not self._available:
            return "MCP 功能不可用（mcp 包未安装）"
        try:
            # 先关闭现有连接
            self._run_sync(self._shutdown_all(), timeout=15.0)
        except Exception as e:
            _log.warning("断开 MCP server 时出现异常: %s", e)

        # 清空状态
        self._sessions.clear()
        self._exit_stacks.clear()
        self._tool_definitions.clear()
        self._tool_to_server.clear()

        # 重新连接
        try:
            self._run_sync(self._connect_all())
            connected = list(self._sessions.keys())
            if connected:
                return f"重新连接成功：{', '.join(connected)}（共 {len(self._tool_to_server)} 个工具）"
            else:
                return "重新连接完成，但无 server 成功连接（请检查配置或网络）"
        except Exception as e:
            _log.error("重新连接 MCP servers 失败: %s", e, exc_info=True)
            return f"重新连接失败: {e}"

    def call_tool(self, tool_name: str, args: dict) -> str:
        """
        调用 MCP 工具，返回 JSON 字符串结果。
        格式与其他工具保持一致：{"success": bool, "result"/"error": ...}
        """
        if not self._available:
            return json.dumps({"success": False, "error": "MCP 功能不可用（mcp 包未安装）"})

        server_name = self._tool_to_server.get(tool_name)
        if server_name is None:
            return json.dumps({"success": False, "error": f"未知 MCP 工具: {tool_name}"})

        # 提取原始 tool 名称（去掉 mcp__{server}__ 前缀）
        original_name = tool_name[len(f"mcp__{server_name}__"):]

        try:
            result = self._run_sync(
                self._call_tool_async(server_name, original_name, args),
                timeout=60.0,
            )
            return result
        except Exception as e:
            _log.error("MCP 工具 %s 调用失败: %s", tool_name, e, exc_info=True)
            return json.dumps({"success": False, "error": str(e)})

    async def _call_tool_async(self, server_name: str, tool_name: str, args: dict) -> str:
        """异步调用 MCP 工具。"""
        session = self._sessions.get(server_name)
        if session is None:
            return json.dumps({"success": False, "error": f"MCP server '{server_name}' 未连接"})

        result = await session.call_tool(tool_name, args)

        # 提取文本内容
        content_parts = []
        for content in result.content:
            if hasattr(content, "text"):
                content_parts.append(content.text)
            elif hasattr(content, "data"):
                content_parts.append(str(content.data))
            else:
                content_parts.append(str(content))

        text = "\n".join(content_parts)
        return json.dumps({"success": True, "result": text}, ensure_ascii=False)

    def shutdown(self) -> None:
        """关闭所有 MCP server 连接。"""
        if not self._available or self._loop is None:
            return
        try:
            self._run_sync(self._shutdown_all(), timeout=10.0)
        except Exception as e:
            _log.warning("MCP shutdown 异常: %s", e)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=2.0)
            self._available = False

    async def _shutdown_all(self) -> None:
        for name, stack in self._exit_stacks.items():
            try:
                await stack.aclose()
                _log.debug("MCP server '%s' 已关闭", name)
            except Exception as e:
                _log.warning("关闭 MCP server '%s' 异常: %s", name, e)
