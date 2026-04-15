"""
轻量级 OmAgent 风格运行时：
- Context: 统一保存任务、消息、步骤、共享状态
- Node:    可组合执行单元
- Workflow: 顺序驱动多个 Node

这里不依赖外部 omagent 包，先在现有项目内提供兼容的工作流抽象，
用于把 Main Agent / Sub-Agent 从“直接 while 循环”升级为“显式 workflow + node”。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable
from itertools import count


@dataclass
class OmAgentContext:
    """单次工作流执行期间共享的上下文。"""

    task: str
    session_context: str = ""
    knowledge_context: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    output: str = ""
    success: bool = False
    error: str = ""


@dataclass
class OmAgentResult:
    """标准工作流结果。"""

    success: bool
    output: str
    steps: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class OmAgentNode(ABC):
    """工作流节点基类。"""

    name = "node"

    @abstractmethod
    def run(self, context: OmAgentContext) -> None:
        """原地更新 context。"""

    def stream(self, context: OmAgentContext):
        """默认流式实现：退化为同步执行。"""
        self.run(context)
        return
        yield


class OmAgentWorkflow:
    """顺序执行节点的最小工作流。"""

    def __init__(self, name: str, nodes: list[OmAgentNode]) -> None:
        self.name = name
        self.nodes = nodes

    def run(self, context: OmAgentContext) -> OmAgentResult:
        for node in self.nodes:
            node.run(context)
            if context.error:
                break
        return OmAgentResult(
            success=context.success and not context.error,
            output=context.output,
            steps=context.steps,
            metadata=context.metadata,
            error=context.error,
        )

    def stream(self, context: OmAgentContext):
        for node in self.nodes:
            yield from node.stream(context)
            if context.error:
                break


class FunctionNode(OmAgentNode):
    """用普通函数快速构造节点。"""

    name = "function"

    def __init__(self, fn: Callable[[OmAgentContext], None], name: str = "function") -> None:
        self._fn = fn
        self.name = name

    def run(self, context: OmAgentContext) -> None:
        self._fn(context)


class PlanningNode(OmAgentNode):
    """显式规划节点。"""

    name = "planning"

    def __init__(self, planner: Callable[[OmAgentContext], None], name: str = "planning") -> None:
        self._planner = planner
        self.name = name

    def run(self, context: OmAgentContext) -> None:
        self._planner(context)
        context.metadata["planning_completed"] = True


class SummaryNode(OmAgentNode):
    """显式总结节点。"""

    name = "summary"

    def __init__(self, summarizer: Callable[[OmAgentContext], None], name: str = "summary") -> None:
        self._summarizer = summarizer
        self.name = name

    def run(self, context: OmAgentContext) -> None:
        self._summarizer(context)
        context.metadata["summary_completed"] = True


def _dump_message(message: Any) -> dict[str, Any]:
    """兼容 OpenAI SDK message 对象和普通 dict。"""
    if isinstance(message, dict):
        return message
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_unset=False)
    return {"role": "assistant", "content": str(message)}


def _parse_tool_arguments(arguments: str) -> dict[str, Any]:
    try:
        return json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return {}


class ToolLoopNode(OmAgentNode):
    """
    通用工具调用节点。

    通过回调注入 LLM 调用、工具执行和消息落盘逻辑，供 Main Agent 与 Sub-Agent 共用。
    """

    name = "tool_loop"

    def __init__(
        self,
        llm_invoke: Callable[[OmAgentContext], Any],
        tool_invoke: Callable[[str, dict[str, Any], OmAgentContext], str],
        *,
        max_turns: int | None = None,
        on_assistant_message: Callable[[dict[str, Any], OmAgentContext], None] | None = None,
        before_tool: Callable[[str, dict[str, Any], OmAgentContext], None] | None = None,
        after_tool: Callable[[str, dict[str, Any], str, OmAgentContext], None] | None = None,
        result_builder: Callable[[OmAgentContext], str] | None = None,
        step_recorder: Callable[[str, dict[str, Any], str, OmAgentContext], dict[str, Any]] | None = None,
    ) -> None:
        self._llm_invoke = llm_invoke
        self._tool_invoke = tool_invoke
        self._max_turns = max_turns
        self._on_assistant_message = on_assistant_message
        self._before_tool = before_tool
        self._after_tool = after_tool
        self._result_builder = result_builder
        self._step_recorder = step_recorder

    def run(self, context: OmAgentContext) -> None:
        turns = range(self._max_turns) if self._max_turns is not None else count()
        for _turn in turns:
            response = self._llm_invoke(context)
            msg = response.choices[0].message
            msg_dict = _dump_message(msg)
            context.messages.append(msg_dict)
            if self._on_assistant_message:
                self._on_assistant_message(msg_dict, context)

            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                context.output = self._result_builder(context) if self._result_builder else (msg.content or "")
                context.success = True
                return

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = _parse_tool_arguments(tool_call.function.arguments)

                if self._before_tool:
                    self._before_tool(tool_name, tool_args, context)

                result = self._tool_invoke(tool_name, tool_args, context)
                step = (
                    self._step_recorder(tool_name, tool_args, result, context)
                    if self._step_recorder
                    else {"tool": tool_name, "args": tool_args, "result": result[:500]}
                )
                context.steps.append(step)

                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
                context.messages.append(tool_message)

                if self._after_tool:
                    self._after_tool(tool_name, tool_args, result, context)

        if self._max_turns is not None:
            context.error = f"工作流超过最大轮次 ({self._max_turns})"


class StreamingToolLoopNode(OmAgentNode):
    """
    流式工具调用节点。

    llm_stream_invoke 需要返回一个可迭代的流式响应对象。
    """

    name = "streaming_tool_loop"

    def __init__(
        self,
        llm_stream_invoke: Callable[[OmAgentContext], Any],
        tool_invoke: Callable[[str, dict[str, Any], OmAgentContext], str],
        *,
        max_turns: int | None = None,
        on_assistant_message: Callable[[dict[str, Any], OmAgentContext], None] | None = None,
        before_tool: Callable[[str, dict[str, Any], OmAgentContext], str | None] | None = None,
        after_tool: Callable[[str, dict[str, Any], str, OmAgentContext], str | None] | None = None,
    ) -> None:
        self._llm_stream_invoke = llm_stream_invoke
        self._tool_invoke = tool_invoke
        self._max_turns = max_turns
        self._on_assistant_message = on_assistant_message
        self._before_tool = before_tool
        self._after_tool = after_tool

    def run(self, context: OmAgentContext) -> None:
        for _ in self.stream(context):
            pass

    def stream(self, context: OmAgentContext):
        turns = range(self._max_turns) if self._max_turns is not None else count()
        for _turn in turns:
            stream = self._llm_stream_invoke(context)
            full_content = ""
            tool_calls_acc: dict[int, dict[str, str]] = {}

            for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta

                if getattr(delta, "content", None):
                    full_content += delta.content
                    yield delta.content

                if getattr(delta, "tool_calls", None):
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                        entry = tool_calls_acc[idx]
                        if getattr(tc_delta, "id", None):
                            entry["id"] += tc_delta.id
                        if getattr(tc_delta, "function", None):
                            if getattr(tc_delta.function, "name", None):
                                entry["name"] += tc_delta.function.name
                            if getattr(tc_delta.function, "arguments", None):
                                entry["arguments"] += tc_delta.function.arguments

            if tool_calls_acc:
                tool_calls_list = [
                    {
                        "id": v["id"],
                        "type": "function",
                        "function": {"name": v["name"], "arguments": v["arguments"]},
                    }
                    for _, v in sorted(tool_calls_acc.items())
                ]
                assistant_message = {
                    "role": "assistant",
                    "content": full_content or None,
                    "tool_calls": tool_calls_list,
                }
            else:
                assistant_message = {"role": "assistant", "content": full_content}

            context.messages.append(assistant_message)
            if self._on_assistant_message:
                self._on_assistant_message(assistant_message, context)

            if not tool_calls_acc:
                context.output = full_content
                context.success = True
                return

            for idx in sorted(tool_calls_acc.keys()):
                entry = tool_calls_acc[idx]
                tool_name = entry["name"]
                tool_args = _parse_tool_arguments(entry["arguments"])

                if self._before_tool:
                    before_payload = self._before_tool(tool_name, tool_args, context)
                    if before_payload:
                        yield before_payload

                result = self._tool_invoke(tool_name, tool_args, context)
                context.steps.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": result[:500],
                })
                tool_message = {
                    "role": "tool",
                    "tool_call_id": entry["id"],
                    "content": result,
                }
                context.messages.append(tool_message)

                if self._after_tool:
                    after_payload = self._after_tool(tool_name, tool_args, result, context)
                    if after_payload:
                        yield after_payload

        if self._max_turns is not None:
            context.error = f"工作流超过最大轮次 ({self._max_turns})"
