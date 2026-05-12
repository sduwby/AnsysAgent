"""整车 CFD 仿真 Sub-Agent（Fluent CFD）。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import VEHICLE_CFD_TOOL_DEFINITIONS, VEHICLE_CFD_TOOL_REGISTRY


class VehicleCFDAgent(SubAgentBase):
    name = "vehicle_cfd"
    workflow_stages = ("plan", "load_mesh", "configure_models", "setup_boundaries", "solve", "postprocess", "summarize")
    description = (
        "整车 CFD 流体仿真专家，负责外流场气动分析（风阻系数 Cd/升力系数 Cl）、"
        "发动机舱热管理仿真、电池热管理 CFD、整车风噪（气动声学）分析，"
        "以及 Fluent 仿真结果的提取和可视化"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=VEHICLE_CFD_TOOL_DEFINITIONS,
            tool_registry=VEHICLE_CFD_TOOL_REGISTRY,
        )

    def _infer_cfd_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("风阻", "气动", "aero", "drag", "外流场", "cd", "cl")):
            return "external_aero", [
                "加载车辆外流场网格",
                "配置湍流模型和边界条件",
                "运行稳态/瞬态外流场仿真",
                "提取风阻系数和升力系数",
            ]
        if any(token in text for token in ("发动机舱", "engine bay", "散热", "机舱热")):
            return "engine_thermal", [
                "加载发动机舱模型",
                "配置热源和散热边界",
                "运行发动机舱热管理仿真",
                "提取温度分布结果",
            ]
        if any(token in text for token in ("电池", "battery", "热管理", "冷却")):
            return "battery_thermal", [
                "加载电池包 CFD 模型",
                "配置电池生热和冷却边界",
                "运行电池热管理仿真",
                "提取电池温度场和冷却效率",
            ]
        if any(token in text for token in ("风噪", "气动噪声", "aeroacoustic")):
            return "wind_noise_cfd", [
                "加载整车外流场高精度网格",
                "配置大涡模拟（LES）或 DES",
                "运行瞬态气动声学仿真",
                "提取噪声源和声压级分布",
            ]
        return "vehicle_cfd", [
            "连接 Fluent 求解器",
            "加载网格并配置物理模型",
            "设置边界条件和求解器参数",
            "运行仿真并提取气动/热管理结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_cfd_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_cfd_flow(task)
        return (
            f"当前整车 CFD 工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "整车 CFD 网格通常较大，注意计算资源和收敛性监控。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_cfd_flow(task)
        run_context.metadata["cfd_flow"] = flow_name
        run_context.metadata["cfd_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("cfd_flow", "vehicle_cfd")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
