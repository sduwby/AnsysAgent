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
from agent.logger import get_logger

console = Console()
_log = get_logger("chat_agent")

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
# 上下文 token 估算
# ---------------------------------------------------------------------------

try:
    import tiktoken as _tiktoken
    _ENC = _tiktoken.get_encoding("cl100k_base")  # gpt-4 / gpt-4o / DeepSeek 等均使用此编码
except Exception:
    _ENC = None


def _estimate_tokens(messages: list[dict]) -> int:
    """
    精确计算消息列表的 token 数量（使用 tiktoken）。
    若 tiktoken 不可用则降级为字符数 // 2 的粗略估算。
    """
    if _ENC is None:
        # 降级：字符估算
        total_chars = 0
        for msg in messages:
            content = msg.get("content") or ""
            if isinstance(content, list):
                content = json.dumps(content, ensure_ascii=False)
            total_chars += len(content)
        return total_chars // 2

    total = 0
    for msg in messages:
        content = msg.get("content") or ""
        if isinstance(content, list):
            content = json.dumps(content, ensure_ascii=False)
        total += len(_ENC.encode(content))
        total += 4  # 每条消息固定开销：<|start|>role\n content<|end|>
    total += 2  # 对话整体开销
    return total


_COMPRESS_THRESHOLD = 80_000   # 超过此 token 数触发压缩
_KEEP_RECENT = 20              # 压缩后保留的最新消息条数

_COMPRESS_SYSTEM = (
    "你是一个专业的工程对话摘要助手。"
    "请将下面的对话历史压缩为简洁摘要，必须保留：\n"
    "1. 所有仿真参数（几何尺寸、材料、绕组参数等）\n"
    "2. 用户的关键操作步骤和意图\n"
    "3. 重要的数值结果（转矩、效率、温升、应力等）\n"
    "4. 已完成的操作和当前状态\n"
    "摘要用中文输出，不超过 800 字。"
)


# ---------------------------------------------------------------------------
# ChatAgent 主类
# ---------------------------------------------------------------------------

class ChatAgent:
    def __init__(self):
        self._init_client()
        self.history: list[dict] = []

    def _maybe_compress_history(self) -> None:
        """
        若历史消息估算 token 超过阈值，将旧消息压缩为摘要。
        保留最近 _KEEP_RECENT 条消息，旧消息发给 LLM 生成摘要后以 user 角色插入。
        """
        if _estimate_tokens(self.history) <= _COMPRESS_THRESHOLD:
            return
        if len(self.history) <= _KEEP_RECENT:
            return

        old_msgs = self.history[:-_KEEP_RECENT]
        recent_msgs = self.history[-_KEEP_RECENT:]

        # 将旧消息序列化为文本供 LLM 压缩
        old_text = "\n".join(
            f"[{m['role'].upper()}] {m.get('content') or ''}" for m in old_msgs
        )
        compress_request = [{"role": "user", "content": f"请压缩以下对话历史：\n\n{old_text}"}]

        try:
            _log.info("触发历史压缩，旧消息 %d 条，估算 token %d",
                      len(old_msgs), _estimate_tokens(old_msgs))
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": _COMPRESS_SYSTEM}] + compress_request,
                max_tokens=1024,
            )
            summary = resp.choices[0].message.content or ""
            summary_msg = {
                "role": "user",
                "content": f"[以下是之前对话的摘要，请在后续回复中参考]\n{summary}",
            }
            self.history = [summary_msg] + recent_msgs
            _log.info("历史压缩完成，摘要 %d 字，保留最近 %d 条消息", len(summary), len(recent_msgs))
            console.print(f"[dim]📦 上下文已压缩（保留最近 {_KEEP_RECENT} 条）[/dim]")
        except Exception as e:
            # 压缩失败不影响主流程，仅记录警告
            _log.warning("历史压缩失败，跳过: %s", e)

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
                _log.error("API 请求异常（非回退类）: %s", e, exc_info=True)
                raise
            if _is_payment_error(e):
                _log.warning("提供商 %s 余额不足 (402)", self._primary_provider)
                console.print(
                    "[bold yellow]💸 遇到了一点问题，这个问题充钱就能解决[/bold yellow]"
                )
            else:
                _log.warning("提供商 %s 触发回退: %s", self._primary_provider, type(e).__name__)
            console.print(
                f"[yellow]⚠ 主提供商 ({self._primary_provider}) 请求失败（{type(e).__name__}），"
                f"尝试回退...[/yellow]"
            )

        # 依次尝试回退提供商
        for fb_client, fb_model, fb_name in self._fallback_clients:
            try:
                _log.info("回退切换到: %s (%s)", fb_name, fb_model)
                console.print(f"[dim]  → 切换到 {fb_name} ({fb_model})[/dim]")
                return call_fn(fb_client, fb_model, **kwargs)
            except Exception as e:
                if not _is_fallback_error(e):
                    _log.error("回退提供商 %s 异常（非回退类）: %s", fb_name, e, exc_info=True)
                    raise
                if _is_payment_error(e):
                    _log.warning("回退提供商 %s 余额不足 (402)", fb_name)
                    console.print(
                        f"[bold yellow]💸 {fb_name} 也遇到了一点问题，这个问题充钱就能解决[/bold yellow]"
                    )
                else:
                    _log.warning("回退提供商 %s 失败: %s", fb_name, type(e).__name__)
                    console.print(f"[yellow]  → {fb_name} 也失败（{type(e).__name__}），继续...[/yellow]")

        _log.error("所有提供商均请求失败")
        raise RuntimeError("所有可用提供商均请求失败，请检查网络或 API 余额。")

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """执行指定工具，返回 JSON 字符串结果。"""
        fn = TOOL_REGISTRY.get(tool_name)
        if fn is None:
            _log.warning("未知工具: %s", tool_name)
            return json.dumps({"success": False, "error": f"未知工具: {tool_name}"})
        _log.info("调用工具: %s | 参数: %s", tool_name, json.dumps(tool_input, ensure_ascii=False))
        try:
            result = fn(**tool_input)
            result_str = json.dumps(result, ensure_ascii=False)
            if result.get("success"):
                _log.info("工具 %s 成功: %s", tool_name, str(result.get("result", ""))[:200])
            else:
                _log.warning("工具 %s 失败: %s", tool_name, result.get("error", ""))
            return result_str
        except Exception as e:
            _log.error("工具 %s 执行异常: %s", tool_name, e, exc_info=True)
            return json.dumps({"success": False, "error": str(e)})

    def chat(self, user_message: str) -> str:
        """发送用户消息，返回最终 Assistant 回复（非流式）。"""
        self.history.append({"role": "user", "content": user_message})
        self._maybe_compress_history()

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
        self._maybe_compress_history()

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
