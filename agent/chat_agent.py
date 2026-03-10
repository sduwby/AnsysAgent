"""
对话 Agent：基于 DeepSeek（OpenAI 兼容接口）的主对话循环，支持工具调用。
"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent.prompt import SYSTEM_PROMPT
from agent.tool_definitions import TOOL_DEFINITIONS, TOOL_REGISTRY

console = Console()

# DeepSeek API 配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ---------------------------------------------------------------------------
# ChatAgent 主类
# ---------------------------------------------------------------------------

class ChatAgent:
    def __init__(self):
        # 初始化 DeepSeek 客户端（OpenAI 兼容接口）
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        self.model = DEEPSEEK_MODEL
        self.history: list[dict] = []

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

        while True:
            # 调用 DeepSeek API
            response = self.client.chat.completions.create(
                model=self.model,
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

        while True:
            # 检查是否有工具调用待处理（上一轮留下的）
            # 先用非流式做工具调用处理，只在最终回复时流式输出
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.history,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )

            msg = response.choices[0].message
            self.history.append(msg.model_dump(exclude_unset=False))

            if not msg.tool_calls:
                # 最终回复：用流式重新请求以获得逐 token 输出
                # 先从历史中移除刚刚添加的非流式回复
                self.history.pop()
                stream = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.history,
                    stream=True,
                )
                full_text = ""
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_text += delta.content
                        yield delta.content
                # 将完整回复存入历史
                self.history.append({"role": "assistant", "content": full_text})
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
