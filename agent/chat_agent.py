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
from tools import maxwell_tools, result_tools

console = Console()

# DeepSeek API 配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_API_KEY = "sk-00c8bde0c3124692907b0a97672cde25"

# ---------------------------------------------------------------------------
# 工具注册表：工具名 -> 可调用函数
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, callable] = {
    "connect_aedt": maxwell_tools.connect_aedt,
    "create_maxwell_project": maxwell_tools.create_maxwell_project,
    "create_motor_geometry": maxwell_tools.create_motor_geometry,
    "assign_material": maxwell_tools.assign_material,
    "setup_winding": maxwell_tools.setup_winding,
    "add_solution_setup": maxwell_tools.add_solution_setup,
    "run_simulation": maxwell_tools.run_simulation,
    "get_torque": result_tools.get_torque,
    "get_back_emf": result_tools.get_back_emf,
    "get_flux_density": result_tools.get_flux_density,
    "get_losses": result_tools.get_losses,
    "export_results": result_tools.export_results,
}

# ---------------------------------------------------------------------------
# 工具定义（OpenAI function calling 格式，DeepSeek 兼容）
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "connect_aedt",
            "description": "连接到运行中的 AEDT 实例或启动新实例。",
            "parameters": {
                "type": "object",
                "properties": {
                    "version": {"type": "string", "description": "AEDT 版本号，如 '2024.1'"},
                    "is_3d": {"type": "boolean", "description": "True 使用 Maxwell 3D，False 使用 Maxwell 2D"},
                    "non_graphical": {"type": "boolean", "description": "是否无界面运行（批处理模式）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_maxwell_project",
            "description": "创建新的 Maxwell 2D/3D 项目和设计。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "项目名称"},
                    "design_name": {"type": "string", "description": "设计名称"},
                },
                "required": ["project_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_motor_geometry",
            "description": "在 Maxwell 2D 中建立 PMSM 电机几何模型（定子、转子、永磁体、气隙）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stator_outer_radius": {"type": "number", "description": "定子外径（mm）"},
                    "stator_inner_radius": {"type": "number", "description": "定子内径（mm）"},
                    "rotor_outer_radius": {"type": "number", "description": "转子外径（mm）"},
                    "rotor_inner_radius": {"type": "number", "description": "转子内径（mm）"},
                    "num_slots": {"type": "integer", "description": "定子槽数"},
                    "num_poles": {"type": "integer", "description": "极数"},
                    "magnet_thickness": {"type": "number", "description": "永磁体厚度（mm）"},
                    "stack_length": {"type": "number", "description": "轴向叠片长度（mm）"},
                },
                "required": [
                    "stator_outer_radius", "stator_inner_radius",
                    "rotor_outer_radius", "rotor_inner_radius",
                    "num_slots", "num_poles", "magnet_thickness",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_material",
            "description": "为几何体对象赋予材料。",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "几何体名称"},
                    "material_name": {"type": "string", "description": "材料名称（需在 AEDT 材料库中存在）"},
                },
                "required": ["object_name", "material_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_winding",
            "description": "配置绕组相激励。",
            "parameters": {
                "type": "object",
                "properties": {
                    "phase_name": {"type": "string", "description": "相名称，如 PhaseA"},
                    "conductor_names": {"type": "array", "items": {"type": "string"}, "description": "导体对象名称列表"},
                    "current_amplitude": {"type": "number", "description": "峰值电流（A）"},
                    "frequency": {"type": "number", "description": "电频率（Hz），磁静态置 0"},
                    "phase_angle": {"type": "number", "description": "相位角（度）"},
                },
                "required": ["phase_name", "conductor_names", "current_amplitude"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_solution_setup",
            "description": "添加求解设置（瞬态 / 磁静态 / 涡流）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "solver_type": {"type": "string", "enum": ["Transient", "Magnetostatic", "EddyCurrent"], "description": "求解器类型"},
                    "stop_time": {"type": "number", "description": "仿真结束时间（秒，瞬态专用）"},
                    "time_step": {"type": "number", "description": "时间步长（秒，瞬态专用）"},
                    "num_passes": {"type": "integer", "description": "自适应网格剖分最大迭代次数"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_simulation",
            "description": "运行（求解）仿真。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_torque",
            "description": "提取平均转矩和转矩波形。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string"},
                    "sweep_name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_back_emf",
            "description": "提取指定相的反电动势波形。",
            "parameters": {
                "type": "object",
                "properties": {
                    "phase_name": {"type": "string", "description": "相名称，如 PhaseA"},
                    "setup_name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flux_density",
            "description": "获取指定点的磁通密度幅值。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string"},
                    "point": {"type": "array", "items": {"type": "number"}, "description": "[x, y, z]（mm）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_losses",
            "description": "获取平均铁耗和铜耗。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_results",
            "description": "将仿真结果导出为 CSV 文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "输出文件路径"},
                    "result_type": {"type": "string", "enum": ["torque", "back_emf", "losses"], "description": "结果类型"},
                },
                "required": ["output_path"],
            },
        },
    },
]


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
