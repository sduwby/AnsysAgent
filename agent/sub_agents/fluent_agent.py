"""Fluent CFD 流体 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import FLUENT_TOOL_DEFINITIONS, FLUENT_TOOL_REGISTRY


class FluentAgent(SubAgentBase):
    name = "fluent"
    workflow_stages = ("plan", "read_or_prepare_mesh", "configure_solver", "solve", "postprocess", "summarize")
    description = (
        "Ansys Fluent CFD 流体仿真专家，负责连接 Fluent、读取网格、配置湍流模型和边界条件、"
        "设置求解器、运行稳态流体仿真、提取压降/速度/温度结果和导出数据"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=FLUENT_TOOL_DEFINITIONS,
            tool_registry=FLUENT_TOOL_REGISTRY,
        )

    def _infer_fluent_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("网格", "mesh", "read mesh", "导入网格")):
            return "mesh_preparation", [
                "读取或校验 Fluent 网格",
                "检查材料模型和边界区域",
                "确认求解器前置条件可用",
            ]
        if any(token in text for token in ("压降", "速度", "velocity", "pressure", "流量", "温度场")):
            return "cfd_postprocess", [
                "确认求解已完成或可执行",
                "提取压降/速度/温度结果",
                "按需导出数据文件",
            ]
        return "cfd_solve", [
            "连接 Fluent 并读取网格",
            "配置流体模型、边界条件和求解器",
            "运行求解并输出关键 CFD 结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_fluent_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_fluent_flow(task)
        return (
            f"当前 Fluent 工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "边界条件与湍流模型需要和网格/工况一致；如果缺少网格，先补网格再尝试求解。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_fluent_flow(task)
        run_context.metadata["fluent_flow"] = flow_name
        run_context.metadata["fluent_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("fluent_flow", "cfd_solve")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
