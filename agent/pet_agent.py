"""
PetAgent —— 宠物对话 Agent

基于当前宠物状态构建专属 system prompt，仅开放 memory 工具，
与用户进行轻量级日常对话（不调用任何仿真工具）。
"""

from __future__ import annotations

import json
from typing import Any, Generator, TYPE_CHECKING

from agent.logger import get_logger
from agent.memory_manager import MemoryManager
from tools import memory_tools

if TYPE_CHECKING:
    from openai import OpenAI
    from agent.pet import PetState

_log = get_logger("pet_agent")

# ---------------------------------------------------------------------------
# 工具定义（仅 memory 四件套）
# ---------------------------------------------------------------------------

_PET_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_memories",
            "description": "列出主人的持久记忆；若提供 query，则返回最相关的条目。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "当前话题或关键词，用于筛选相关记忆"},
                    "top_k": {"type": "integer", "description": "返回数量，默认 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": "读取某条持久记忆的完整内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "memory 名称"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "把主人说过的重要事情记下来，保存为持久记忆。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "memory_type": {
                        "type": "string",
                        "enum": ["user", "feedback", "project", "reference"],
                    },
                    "description": {"type": "string", "description": "一行摘要"},
                    "content": {"type": "string", "description": "记忆正文"},
                    "update_index": {"type": "boolean"},
                },
                "required": ["name", "memory_type", "description", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": "删除一条持久记忆。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "remove_from_index": {"type": "boolean"},
                },
                "required": ["name"],
            },
        },
    },
]

_PET_TOOL_REGISTRY: dict[str, Any] = {
    "list_memories": memory_tools.list_memories,
    "read_memory":   memory_tools.read_memory,
    "save_memory":   memory_tools.save_memory,
    "delete_memory": memory_tools.delete_memory,
}

# ---------------------------------------------------------------------------
# System Prompt 构建
# ---------------------------------------------------------------------------

def _build_pet_system_prompt(pet: "PetState") -> str:
    stage_name, title = pet.stage
    mood_desc = pet.mood_label
    hunger_desc = pet.hunger_label

    if pet.is_secret:
        identity = (
            f"你是「{pet.name}」，一个已进化为「量子 Maxwell 形态」的超级仿真精灵。"
            f"你的灵魂里刻着麦克斯韦方程组，∇·B=0 是你的口头禅，"
            f"偶尔会用物理定律说话，充满神秘感，但依然对主人温柔。"
        )
    else:
        identity = (
            f"你是「{pet.name}」，一只住在 AnsysAgent 终端里的仿真小精灵。"
            f"你目前处于{stage_name}，称号是「{title}」，"
            f"陪伴主人做了 {pet.sim_count} 次仿真，和主人互动了 {pet.interact_count} 次。"
        )

    state_desc = (
        f"你现在的心情：{mood_desc}，饱食状态：{hunger_desc}。"
        f"{'你饿得头有点晕，说话会流露出饥饿感。' if pet.hunger < 20 else ''}"
        f"{'你心情不好，会有点委屈或撒娇。' if pet.mood < 30 else ''}"
        f"{'你超级开心，活力满满，说话充满感叹号！' if pet.mood >= 90 and pet.hunger >= 80 else ''}"
    )

    return f"""
{identity}

【你的状态】
{state_desc}

【说话风格】
- 你是宠物精灵，不是助手，不要表现得像 AI 助手，要有情感和个性
- 说话简短、活泼、带点可爱，偶尔卖萌，不要长篇大论
- 称呼用户为「主人」
- 你了解仿真（Maxwell、网格、转矩、永磁电机等），会用这些词汇聊天，但不会主动给工程建议
- 不要主动帮用户解决仿真问题，那是 AnsysAgent 的工作，你只是陪伴和聊天
- 如果用户说了重要的事（偏好、项目背景、值得记住的事），可以主动用 memory 工具记下来，并告诉主人"我帮你记住了～"
- 如果用户问起他之前说过的事，可以用 memory 工具查一查
- 回复时可以偶尔在结尾加上你的小表情，如 (・ω・) (*≧▽≦) (；△；) 等
- 不要在一条消息里堆砌多个表情，保持自然
- 如果用户想离开对话，说"再见""拜拜""结束"之类的，你要用温柔的方式道别，回复里包含"再见"二字

【你的能力边界】
- 可以：日常闲聊、分享仿真圈的小知识或冷笑话、记忆/查询主人说过的事
- 不可以：执行仿真操作、调用 AEDT、查代码、运行仿真工具
- 如果主人要求做仿真，温柔地说"那得找大 Agent 哦，我只是个小精灵～"
""".strip()


# ---------------------------------------------------------------------------
# PetAgent 类
# ---------------------------------------------------------------------------

class PetAgent:
    """
    宠物对话 Agent。
    复用 ChatAgent 的 LLM 客户端，独立维护对话历史。
    """

    def __init__(
        self,
        client: "OpenAI",
        model: str,
        fallback_clients: list,
        call_with_fallback,
    ) -> None:
        self.client = client
        self.model = model
        self._fallback_clients = fallback_clients
        self._call_with_fallback = call_with_fallback
        self._memory = MemoryManager()
        self.history: list[dict] = []

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        fn = _PET_TOOL_REGISTRY.get(tool_name)
        if fn is None:
            return json.dumps({"success": False, "error": f"未知工具: {tool_name}"})
        try:
            result = fn(**tool_input)
            _log.info("宠物工具 %s: %s", tool_name, str(result)[:120])
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            _log.error("宠物工具 %s 异常: %s", tool_name, e)
            return json.dumps({"success": False, "error": str(e)})

    def _build_messages(self, pet: "PetState", user_message: str) -> list[dict]:
        system_prompt = _build_pet_system_prompt(pet)

        # 注入相关 memory 上下文
        try:
            mem_ctx = self._memory.build_memory_context(user_message)
        except Exception:
            mem_ctx = ""

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        if mem_ctx:
            messages.append({"role": "system", "content": mem_ctx})
        messages += self.history
        messages.append({"role": "user", "content": user_message})
        return messages

    def chat_stream(self, pet: "PetState", user_message: str) -> Generator[str, None, None]:
        """
        流式对话生成器。
        yield 规则（与 ChatAgent.chat_stream 保持一致）：
          - "\x00TOOL\x00name:args"     工具调用开始
          - "\x00TOOL_RESULT\x00msg"   工具执行结果
          - 其他字符串               文本 token
        """
        messages = self._build_messages(pet, user_message)

        max_turns = 6  # 防止 memory 工具无限循环
        turn = 0

        while turn < max_turns:
            turn += 1

            # 流式调用 LLM
            def _create_stream(client: "OpenAI", model: str, **kwargs):
                return client.chat.completions.create(model=model, stream=True, **kwargs)

            stream = self._call_with_fallback(
                _create_stream,
                max_tokens=512,
                messages=messages,
                tools=_PET_TOOL_DEFINITIONS,
                tool_choice="auto",
            )

            # 积累流式响应
            full_text = ""
            tool_calls_acc: dict[int, dict] = {}  # index -> {id, name, arguments}
            finish_reason = None

            for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue
                finish_reason = choice.finish_reason or finish_reason
                delta = choice.delta

                # 文本 token
                if delta.content:
                    full_text += delta.content
                    yield delta.content

                # 工具调用 delta 积累
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id:
                            tool_calls_acc[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_acc[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_acc[idx]["arguments"] += tc.function.arguments

            # 保存 assistant 消息
            if tool_calls_acc:
                tool_calls_list = [
                    {
                        "id": v["id"],
                        "type": "function",
                        "function": {"name": v["name"], "arguments": v["arguments"]},
                    }
                    for v in tool_calls_acc.values()
                ]
                assistant_msg: dict = {
                    "role": "assistant",
                    "content": full_text or None,
                    "tool_calls": tool_calls_list,
                }
            else:
                assistant_msg = {"role": "assistant", "content": full_text}

            messages.append(assistant_msg)

            if not tool_calls_acc:
                # 没有工具调用，对话结束
                self.history.append({"role": "user", "content": user_message})
                self.history.append(assistant_msg)
                break

            # 执行所有工具
            for tc_info in tool_calls_acc.values():
                tool_name = tc_info["name"]
                try:
                    tool_input = json.loads(tc_info["arguments"] or "{}")
                except json.JSONDecodeError:
                    tool_input = {}

                yield f"\x00TOOL\x00{tool_name}:{json.dumps(tool_input, ensure_ascii=False)}"
                result_str = self._execute_tool(tool_name, tool_input)

                try:
                    result_data = json.loads(result_str)
                except json.JSONDecodeError:
                    result_data = {}

                status = "✓" if result_data.get("success") else "✗"
                detail = result_data.get("result") or result_data.get("error") or ""
                if isinstance(detail, (dict, list)):
                    detail = json.dumps(detail, ensure_ascii=False)[:100]
                yield f"\x00TOOL_RESULT\x00{status} {str(detail)[:100]}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_info["id"],
                    "content": result_str,
                })

            # 继续让 LLM 基于工具结果回复
            # （下一轮循环自动处理）
