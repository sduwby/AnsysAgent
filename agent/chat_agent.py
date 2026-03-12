"""
对话 Agent：基于多提供商（OpenAI 兼容接口）的主对话循环，支持工具调用。
"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI, RateLimitError, APIStatusError
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent.config_manager import load_llm_config, PROVIDERS, FALLBACK_CHAIN, get_provider_api_key
from agent.prompt import SYSTEM_PROMPT
from agent.tool_definitions import TOOL_DEFINITIONS, TOOL_REGISTRY

console = Console()

# 触发回退的错误码（限速 / 余额不足）
_FALLBACK_STATUS_CODES = {429, 402, 503}


def _is_fallback_error(exc: Exception) -> bool:
    """判断异常是否应触发回退到下一个提供商。"""
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in _FALLBACK_STATUS_CODES:
        return True
    return False


def _is_payment_error(exc: Exception) -> bool:
    """判断是否为余额不足错误 (402)。"""
    return isinstance(exc, APIStatusError) and exc.status_code == 402


# ---------------------------------------------------------------------------
# ChatAgent 主类
# ---------------------------------------------------------------------------

class ChatAgent:
    def __init__(self):
        self._init_client()
        self.history: list[dict] = []

    def _init_client(self) -> None:
        """从当前环境配置初始化主客户端，并预构建回退客户端列表。"""
        cfg = load_llm_config()
        self.client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
        self.model = cfg.model
        self._primary_provider = cfg.provider
        self._primary_model = cfg.model
        # 预构建回退链客户端 [(client, model, provider_name), ...]
        self._fallback_clients: list[tuple[OpenAI, str, str]] = []
        for provider_key in FALLBACK_CHAIN:
            if provider_key == cfg.provider:
                continue  # 跳过与主提供商相同的
            pinfo = PROVIDERS.get(provider_key)
            if not pinfo:
                continue
            api_key = get_provider_api_key(provider_key)
            if not api_key:
                continue
            fb_client = OpenAI(api_key=api_key, base_url=pinfo["base_url"])
            fb_model = pinfo["models"][0]
            self._fallback_clients.append((fb_client, fb_model, pinfo["name"]))

    def reload_config(self) -> None:
        """重新加载配置并重建客户端（保留对话历史）。"""
        self._init_client()

    def _call_with_fallback(self, call_fn, *args, **kwargs):
        """
        执行 call_fn(client, model, *args, **kwargs)，失败时按回退链重试。
        call_fn 签名：call_fn(client: OpenAI, model: str, **kwargs) -> response
        """
        # 先用主客户端尝试
        try:
            return call_fn(self.client, self.model, **kwargs)
        except Exception as e:
            if not _is_fallback_error(e):
                raise
            if _is_payment_error(e):
                console.print(
                    "[bold yellow]💸 遇到了一点问题，这个问题充钱就能解决[/bold yellow]"
                )
            console.print(
                f"[yellow]⚠ 主提供商 ({self._primary_provider}) 请求失败（{type(e).__name__}），"
                f"尝试回退...[/yellow]"
            )

        # 依次尝试回退提供商
        for fb_client, fb_model, fb_name in self._fallback_clients:
            try:
                console.print(f"[dim]  → 切换到 {fb_name} ({fb_model})[/dim]")
                return call_fn(fb_client, fb_model, **kwargs)
            except Exception as e:
                if not _is_fallback_error(e):
                    raise
                if _is_payment_error(e):
                    console.print(
                        f"[bold yellow]💸 {fb_name} 也遇到了一点问题，这个问题充钱就能解决[/bold yellow]"
                    )
                else:
                    console.print(f"[yellow]  → {fb_name} 也失败（{type(e).__name__}），继续...[/yellow]")

        raise RuntimeError("所有可用提供商均请求失败，请检查网络或 API 余额。")

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """执行指定工具，返回 JSON 字符串结果。"""
        fn = TOOL_REGISTRY.get(tool_name)
        if fn is None:
            return json.dumps({"success": False, "error": f"未知工具: {tool_name}"})
        try:
            result = fn(**tool_input)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def chat(self, user_message: str) -> str:
        """发送用户消息，返回最终 Assistant 回复（非流式）。"""
        self.history.append({"role": "user", "content": user_message})

        def _create(client: OpenAI, model: str, **kwargs):
            return client.chat.completions.create(model=model, **kwargs)

        while True:
            response = self._call_with_fallback(
                _create,
                max_tokens=4096,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.history,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )

            msg = response.choices[0].message

            # 将 assistant 消息加入历史
            self.history.append(msg.model_dump(exclude_unset=False))

            # 没有工具调用，直接返回文本
            if not msg.tool_calls:
                return msg.content or ""

            # 执行所有工具调用
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                console.print(
                    f"[dim]🔧 调用工具: [bold]{fn_name}[/bold] "
                    f"{json.dumps(fn_args, ensure_ascii=False)}[/dim]"
                )
                result_str = self._execute_tool(fn_name, fn_args)
                result_data = json.loads(result_str)
                if result_data.get("success"):
                    console.print(f"[green]  ✓ {result_data.get('result', 'OK')}[/green]")
                else:
                    console.print(f"[red]  ✗ {result_data.get('error', '错误')}[/red]")

                # 将工具结果追加到历史
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str,
                })

    def chat_stream(self, user_message: str):
        """
        流式对话：生成器，逐 token yield 文本片段。
        工具调用期间会 yield 特殊前缀 '\r\x00TOOL\x00' 开头的状态行。
        """
        self.history.append({"role": "user", "content": user_message})

        def _create(client: OpenAI, model: str, **kwargs):
            return client.chat.completions.create(model=model, **kwargs)

        while True:
            # 先用非流式做工具调用处理，只在最终回复时流式输出
            response = self._call_with_fallback(
                _create,
                max_tokens=4096,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.history,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )

            msg = response.choices[0].message
            self.history.append(msg.model_dump(exclude_unset=False))

            if not msg.tool_calls:
                # 直接从非流式响应逐字符 yield，避免第二次 API 请求导致的
                # token 浪费和结果不一致风险（第二次请求也可能返回工具调用）。
                # history 在第 177 行已包含此条 assistant 消息，无需再追加。
                content = msg.content or ""
                for char in content:
                    yield char
                return

            # 有工具调用：通知调用方，执行工具
            for tool_call in msg.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                yield f"\x00TOOL\x00{fn_name}:{json.dumps(fn_args, ensure_ascii=False)}"

                result_str = self._execute_tool(fn_name, fn_args)
                result_data = json.loads(result_str)
                status = "✓" if result_data.get("success") else "✗"
                detail = result_data.get("result") or result_data.get("error") or ""
                yield f"\x00TOOL_RESULT\x00{status} {detail}"

                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result_str,
                })
