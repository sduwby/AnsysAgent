"""Motor-CAD 解析初设计 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import MOTORCAD_TOOL_DEFINITIONS, MOTORCAD_TOOL_REGISTRY


class MotorCADAgent(SubAgentBase):
    name = "motorcad"
    workflow_stages = ("plan", "configure_geometry", "run_analytical_analysis", "export_or_postprocess", "summarize")
    description = (
        "Ansys Motor-CAD 解析法初设计专家，负责连接 Motor-CAD、配置电机几何参数、"
        "运行 EM/热网络/NVH 分析、生成效率 MAP，并将结果导出到 Maxwell 进行精确 FEM 仿真"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=MOTORCAD_TOOL_DEFINITIONS,
            tool_registry=MOTORCAD_TOOL_REGISTRY,
        )

    def _infer_motorcad_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("maxwell", "导出", "export")):
            return "export_to_maxwell", [
                "确认 Motor-CAD 几何与设计参数已定义",
                "运行必要的解析分析",
                "导出到 Maxwell 供后续 FEM 精化",
            ]
        if any(token in text for token in ("效率", "map", "thermal", "nvh", "性能", "温升")):
            return "analytical_performance", [
                "配置几何与工况参数",
                "执行 EM/热/NVH 分析",
                "提取性能图谱或关键指标",
            ]
        return "initial_design", [
            "连接 Motor-CAD 并设置几何参数",
            "运行解析初设计分析",
            "输出设计性能或准备下游导出",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_motorcad_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_motorcad_flow(task)
        return (
            f"当前 Motor-CAD 工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "如果目标是导出到 Maxwell，先确保解析法模型已完成关键参数和性能求解。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_motorcad_flow(task)
        run_context.metadata["motorcad_flow"] = flow_name
        run_context.metadata["motorcad_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("motorcad_flow", "initial_design")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
