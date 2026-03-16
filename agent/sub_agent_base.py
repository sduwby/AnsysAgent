"""
Sub-Agent 基类：提供工具调用循环、LLM fallback 和结果结构。
"""

from __future__ import annotations

import json

from openai import OpenAI, RateLimitError, APIStatusError

from agent.logger import get_logger

_FALLBACK_STATUS_CODES = {429, 402, 503}
_log = get_logger("sub_agent")


def _is_fallback_error(exc: Exception) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and exc.status_code in _FALLBACK_STATUS_CODES:
        return True
    return False


class SubAgentBase:
    """
    专业 Sub-Agent 基类。
    子类需设置 name / description，并可覆盖 get_system_prompt()。
    """

    name: str = "base"
    description: str = "通用 Sub-Agent"

    def __init__(
        self,
        client: OpenAI,
        model: str,
        fallback_clients: list[tuple[OpenAI, str, str]],
        tool_definitions: list[dict],
        tool_registry: dict[str, callable],
    ) -> None:
        self.client = client
        self.model = model
        self.fallback_clients = fallback_clients
        self.tool_definitions = tool_definitions
        self.tool_registry = tool_registry

    # ------------------------------------------------------------------
    # LLM 调用（带 fallback）
    # ------------------------------------------------------------------

    def _call_llm(self, messages: list[dict], **kwargs):
        def _create(client: OpenAI, model: str):
            return client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )

        try:
            return _create(self.client, self.model)
        except Exception as e:
            if not _is_fallback_error(e):
                raise

        for fb_client, fb_model, fb_name in self.fallback_clients:
            try:
                _log.info("[%s] LLM fallback → %s", self.name, fb_name)
                return _create(fb_client, fb_model)
            except Exception as e:
                if not _is_fallback_error(e):
                    raise

        raise RuntimeError(f"Sub-agent '{self.name}': 所有 LLM 提供商均失败")

    # ------------------------------------------------------------------
    # 工具执行
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        fn = self.tool_registry.get(tool_name)
        if fn is None:
            _log.warning("[%s] 未知工具: %s", self.name, tool_name)
            return json.dumps({"success": False, "error": f"未知工具: {tool_name}"})
        _log.info("[%s] 调用工具: %s | 参数: %s", self.name, tool_name,
                  json.dumps(tool_input, ensure_ascii=False)[:200])
        try:
            result = fn(**tool_input)
            return json.dumps(result, ensure_ascii=False)
        except Exception as exc:
            _log.error("[%s] 工具 %s 异常: %s", self.name, tool_name, exc, exc_info=True)
            return json.dumps({"success": False, "error": str(exc)})

    # ------------------------------------------------------------------
    # System prompt（子类可覆盖）
    # ------------------------------------------------------------------

    def get_system_prompt(self, context: str) -> str:
        ctx_section = f"\n\n## 当前会话上下文\n{context}" if context else ""
        return (
            f"你是 {self.description}。"
            f"请使用可用工具完成任务，执行完成后给出简洁的中文结果摘要。"
            f"不要询问用户确认，直接执行任务。"
            f"{ctx_section}"
        )

    # ------------------------------------------------------------------
    # 主执行方法
    # ------------------------------------------------------------------

    def execute(self, task: str, context: str = "", max_turns: int = 30) -> dict:
        """
        运行工具调用循环，直到 LLM 返回文本（无工具调用）或达到 max_turns。
        返回结构：{"success": bool, "agent": str, "result": str, "steps": list}
        """
        messages: list[dict] = [
            {"role": "system", "content": self.get_system_prompt(context)},
            {"role": "user", "content": task},
        ]
        steps: list[dict] = []

        for _turn in range(max_turns):
            resp = self._call_llm(
                messages=messages,
                max_tokens=4096,
                tools=self.tool_definitions,
                tool_choice="auto",
            )
            msg = resp.choices[0].message
            messages.append(msg.model_dump(exclude_unset=False))

            if not msg.tool_calls:
                # 最终文本回复 → 任务完成
                return {
                    "success": True,
                    "agent": self.name,
                    "result": msg.content or "",
                    "steps": steps,
                }

            # 执行所有工具调用
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}
                result_str = self._execute_tool(fn_name, fn_args)
                steps.append({"tool": fn_name, "args": fn_args, "result": result_str[:500]})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                })

        return {
            "success": False,
            "agent": self.name,
            "result": f"Sub-agent '{self.name}' 已达到最大轮次 ({max_turns})，任务未完成",
            "steps": steps,
        }
