"""optiSLang 优化 + 参数扫描 Sub-Agent（增强版：支持热-电磁联合优化目标）。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import OPTIMIZATION_TOOL_DEFINITIONS, OPTIMIZATION_TOOL_REGISTRY


class OptimizationAgent(SubAgentBase):
    name = "optimization"
    workflow_stages = (
        "plan",
        "define_variables_and_responses",
        "setup_coupled_objectives",
        "run_study",
        "collect_results",
        "summarize",
    )
    description = (
        "Ansys optiSLang 优化与参数扫描专家，负责连接 optiSLang、设置设计变量和目标函数、"
        "运行敏感性分析和多目标优化，以及 Maxwell 参数化扫描（单参数线性扫描和二维效率 MAP）。"
        "增强支持热-电磁联合优化目标（如在温升约束下最大化效率、在退磁安全裕量约束下最小化磁钢用量等）"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=OPTIMIZATION_TOOL_DEFINITIONS,
            tool_registry=OPTIMIZATION_TOOL_REGISTRY,
        )

    def _infer_optimization_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("敏感性", "sensitivity")):
            return "sensitivity_study", [
                "确认设计变量和响应已定义",
                "运行敏感性分析",
                "汇总敏感度和关键影响因素",
            ]
        if any(token in text for token in ("扫描", "sweep", "efficiency map", "二维", "2d")):
            return "parametric_sweep", [
                "检查参数变量和结果表达式",
                "执行单参数或二维扫描",
                "提取扫描结果或效率 MAP",
            ]
        if any(token in text for token in (
            "温升", "thermal", "热", "温度", "temperature",
            "退磁", "demagnetization", "联合优化", "coupled",
            "约束", "constraint",
        )):
            return "coupled_optimization", [
                "定义电磁设计变量（槽宽/磁钢厚度/匝数等）",
                "定义热约束（最高温升 ≤ 绝缘等级限值）",
                "定义电磁目标（最大化效率/最小化损耗）",
                "运行联合优化并验证热约束满足",
            ]
        return "optimization_study", [
            "连接 optiSLang 或准备参数化设置",
            "定义变量、响应和优化目标",
            "运行优化并输出最优解结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_optimization_flow(task)
        return (
            f"[{flow_name}] {super().build_execution_plan(task, context)} "
            f"重点步骤: " + "；".join(checklist) + "。"
        )

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_optimization_flow(task)
        guidance = (
            f"当前优化工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "如果变量或响应未定义，先补齐定义；不要在缺少前置参数的情况下直接启动优化。"
        )
        if flow_name == "coupled_optimization":
            guidance += (
                "\n\n热-电磁联合优化关键指引：\n"
                "1. 电磁变量（槽宽、磁钢厚度、匝数等）通过 add_design_variable 定义\n"
                "2. 温升约束通过 add_response(response_type='constraint') 定义，如 'winding_max_temp ≤ 155'\n"
                "3. 电磁目标通过 add_response(response_type='objective') 定义，如 maximize efficiency\n"
                "4. 热响应值需从 Icepak/Motor-CAD 热仿真获取，确保变量变化后热仿真也被更新\n"
                "5. 如果同时有退磁约束，使用 check_demagnetization 结果作为额外约束响应"
            )
        return guidance

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_optimization_flow(task)
        run_context.metadata["optimization_flow"] = flow_name
        run_context.metadata["optimization_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("optimization_flow", "optimization_study")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
