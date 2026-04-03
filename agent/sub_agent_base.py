"""
Sub-Agent 基类：提供工具调用循环、LLM fallback 和结果结构。
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, RateLimitError, APIStatusError

from agent.logger import get_logger
from agent.omagent_runtime import OmAgentContext, OmAgentWorkflow, PlanningNode, SummaryNode, ToolLoopNode

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
    workflow_stages: tuple[str, ...] = ("plan", "execute", "summarize")

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

    def build_execution_plan(self, task: str, context: str = "") -> str:
        """生成执行计划摘要，供 workflow metadata 和 prompt 复用。"""
        tool_names = ", ".join(td["function"]["name"] for td in self.tool_definitions[:12])
        more = ""
        if len(self.tool_definitions) > 12:
            more = f" 等共 {len(self.tool_definitions)} 个工具"
        ctx = f"；会话上下文：{context}" if context else ""
        return (
            f"阶段: {' -> '.join(self.workflow_stages)}；"
            f"当前任务：{task}{ctx}；"
            f"可优先使用工具：{tool_names}{more}。"
        )

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        """为 LLM 注入阶段化执行约束。子类可覆写。"""
        return (
            f"请按照以下阶段推进：{' -> '.join(self.workflow_stages)}。\n"
            f"先判断前置条件，再调用工具；如果工具返回失败或警告，优先修复后再继续。\n"
            f"最终总结中明确说明已完成步骤、关键结果和剩余风险。"
        )

    def prepare_run_context(self, run_context: OmAgentContext, task: str, context: str = "") -> None:
        """准备 Sub-Agent 运行时上下文。子类可覆写。"""
        run_context.session_context = context
        run_context.metadata["agent_name"] = self.name
        run_context.metadata["workflow_stages"] = list(self.workflow_stages)
        run_context.metadata["execution_plan"] = self.build_execution_plan(task, context)
        run_context.metadata["stage_guidance"] = self.build_stage_guidance(task, context)
        run_context.metadata["tool_count"] = len(self.tool_definitions)
        if not run_context.messages:
            run_context.messages = [
                {"role": "system", "content": self.get_system_prompt(context)},
                {"role": "system", "content": run_context.metadata["stage_guidance"]},
                {"role": "user", "content": task},
            ]

    def finalize_run_context(self, run_context: OmAgentContext) -> None:
        """收尾整理上下文。子类可覆写。"""
        run_context.metadata["num_steps"] = len(run_context.steps)
        if run_context.success and run_context.output:
            run_context.metadata["final_summary"] = run_context.output
        elif run_context.success:
            run_context.output = f"{self.description}已完成任务，共执行 {len(run_context.steps)} 个步骤。"
            run_context.metadata["final_summary"] = run_context.output

    def build_workflow(self, task: str, context: str = "", max_turns: int = 30) -> OmAgentWorkflow:
        """构造当前 Sub-Agent 的 OmAgent 风格工作流。"""

        def _invoke_llm(run_context: OmAgentContext):
            return self._call_llm(
                messages=run_context.messages,
                max_tokens=4096,
                tools=self.tool_definitions,
                tool_choice="auto",
            )

        def _invoke_tool(tool_name: str, tool_input: dict[str, Any], _run_context: OmAgentContext) -> str:
            return self._execute_tool(tool_name, tool_input)

        return OmAgentWorkflow(
            name=f"{self.name}_workflow",
            nodes=[
                PlanningNode(
                    lambda run_context: self.prepare_run_context(run_context, task, context),
                    name="plan",
                ),
                ToolLoopNode(
                    llm_invoke=_invoke_llm,
                    tool_invoke=_invoke_tool,
                    max_turns=max_turns,
                ),
                SummaryNode(
                    self.finalize_run_context,
                    name="summarize",
                ),
            ],
        )

    # ------------------------------------------------------------------
    # 主执行方法
    # ------------------------------------------------------------------

    def execute(self, task: str, context: str = "", max_turns: int = 30) -> dict:
        """
        运行工具调用循环，直到 LLM 返回文本（无工具调用）或达到 max_turns。
        返回结构：{"success": bool, "agent": str, "result": str, "steps": list}
        """
        run_context = OmAgentContext(
            task=task,
            session_context=context,
            metadata={},
        )
        result = self.build_workflow(task=task, context=context, max_turns=max_turns).run(run_context)
        if result.success:
            return {
                "success": True,
                "agent": self.name,
                "result": result.output,
                "steps": result.steps,
                "metadata": result.metadata,
            }

        failure = result.error or f"Sub-agent '{self.name}' 已达到最大轮次 ({max_turns})，任务未完成"
        return {
            "success": False,
            "agent": self.name,
            "result": failure,
            "steps": result.steps,
            "metadata": result.metadata,
        }

    def run(self, task: str, context: str = "", max_turns: int = 30) -> dict:
        """OmAgent 风格别名，便于 Dispatcher/Workflow 统一调用。"""
        return self.execute(task=task, context=context, max_turns=max_turns)
