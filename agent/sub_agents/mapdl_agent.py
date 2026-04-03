"""MAPDL 结构/NVH/DPF Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import MAPDL_TOOL_DEFINITIONS, MAPDL_TOOL_REGISTRY


class MapdlAgent(SubAgentBase):
    name = "mapdl"
    workflow_stages = ("plan", "prepare_structural_case", "solve", "postprocess", "summarize")
    description = (
        "PyMAPDL/Mechanical/DPF 结构仿真专家，负责连接 Mechanical/MAPDL、"
        "导入电磁力、运行模态/谐响应/NVH 分析、提取振动和结构结果，"
        "以及使用 PyDPF-Post 进行应力/温度/变形场后处理和 CSV 导出"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=MAPDL_TOOL_DEFINITIONS,
            tool_registry=MAPDL_TOOL_REGISTRY,
        )

    def _infer_mapdl_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("模态", "谐响应", "nvh", "harmonic", "modal")):
            return "nvh_analysis", [
                "确认结构模型和载荷输入",
                "配置模态或谐响应分析",
                "提取频率响应或振动结果",
            ]
        if any(token in text for token in ("应力", "stress", "位移", "dpf", "温度场", "导出 csv")):
            return "structural_postprocess", [
                "确认结果文件可访问",
                "使用 MAPDL/DPF 提取结构场结果",
                "按需导出应力/温度/位移数据",
            ]
        return "structural_solve", [
            "连接 MAPDL 或 Mechanical",
            "准备结构工况与载荷",
            "执行求解并收集结构结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_mapdl_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_mapdl_flow(task)
        return (
            f"当前 MAPDL 工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "如果结果提取依赖已有 rst/rth 等结果文件，先校验文件路径与分析类型匹配。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_mapdl_flow(task)
        run_context.metadata["mapdl_flow"] = flow_name
        run_context.metadata["mapdl_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("mapdl_flow", "structural_solve")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
