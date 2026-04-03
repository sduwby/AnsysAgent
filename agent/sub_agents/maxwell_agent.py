"""Maxwell 电磁仿真 Sub-Agent（含网格、结果提取、RMXprt、Circuit、可视化）。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import MAXWELL_TOOL_DEFINITIONS, MAXWELL_TOOL_REGISTRY


class MaxwellAgent(SubAgentBase):
    name = "maxwell"
    workflow_stages = ("plan", "model_or_configure", "solve", "postprocess", "summarize")
    description = (
        "Ansys Maxwell 电磁仿真专家，负责几何建模、材料赋值、绕组配置、求解设置、"
        "网格控制、结果提取（转矩/反电动势/电感/效率 MAP/退磁校核）、"
        "场量可视化、RMXprt 快速初设计以及 Circuit 驱动器联仿"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=MAXWELL_TOOL_DEFINITIONS,
            tool_registry=MAXWELL_TOOL_REGISTRY,
        )

    def _infer_maxwell_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("效率", "efficiency", "map", "扫描", "sweep", "优化", "optimization")):
            return "performance_map", [
                "检查现有设计变量和已求解 setup",
                "必要时创建参数扫描或效率 MAP",
                "执行求解并收集扭矩/损耗/效率结果",
            ]
        if any(token in text for token in ("反电动势", "back emf", "bemf", "瞬态", "transient")):
            return "transient_postprocess", [
                "确认或建立瞬态求解设置",
                "运行求解并提取 Back EMF/波形数据",
                "校验结果是否已导出或可复用",
            ]
        if any(token in text for token in ("建模", "geometry", "pmsm", "电机", "槽", "极")):
            return "model_building", [
                "连接 AEDT 或打开现有项目",
                "建立或修正几何/材料/绕组/网格",
                "补充求解设置并在需要时运行校验求解",
            ]
        return "general_analysis", [
            "确认当前项目、设计和求解前置条件",
            "按需配置模型/网格/边界/设置",
            "执行求解并提取用户请求的结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_maxwell_flow(task)
        base_plan = super().build_execution_plan(task, context)
        return f"[{flow_name}] {base_plan} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_maxwell_flow(task)
        return (
            f"当前 Maxwell 工作流类型：{flow_name}。\n"
            f"请严格遵循阶段 {' -> '.join(self.workflow_stages)}。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "优先复用已有项目/设计/求解设置；只有在缺失时再创建新对象。\n"
            "如果结果提取依赖未求解 setup，先明确完成求解再提取。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_maxwell_flow(task)
        run_context.metadata["maxwell_flow"] = flow_name
        run_context.metadata["maxwell_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("maxwell_flow", "general_analysis")
        step_count = len(run_context.steps)
        if run_context.output:
            run_context.output = f"[{flow_name}] {run_context.output}"
            run_context.metadata["final_summary"] = run_context.output
        else:
            run_context.output = f"[{flow_name}] Maxwell 任务已完成，共执行 {step_count} 个步骤。"
            run_context.metadata["final_summary"] = run_context.output
