"""电机成本估算 Sub-Agent：根据材料用量、制造工艺估算电机制造成本。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import COST_TOOL_DEFINITIONS, COST_TOOL_REGISTRY


class CostAgent(SubAgentBase):
    name = "cost"
    workflow_stages = (
        "plan",
        "collect_design_parameters",
        "estimate_cost",
        "compare_alternatives",
        "summarize",
    )
    description = (
        "电机成本估算专家，根据电机几何参数、材料类型和制造工艺，"
        "估算铁芯、绕组、永磁体、结构件、绝缘和加工费等成本明细，"
        "支持不同磁钢方案（NdFeB/铁氧体）成本对比，辅助选型和降本决策"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=COST_TOOL_DEFINITIONS,
            tool_registry=COST_TOOL_REGISTRY,
        )

    def _infer_cost_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("对比", "compare", "方案", "选型", "NdFeB", "铁氧体", "ferrite")):
            return "cost_comparison", [
                "提取两种方案的几何参数和材料配置",
                "分别估算两种方案成本",
                "对比成本差异并给出选型建议",
            ]
        if any(token in text for token in ("降本", "优化成本", "节约", "reduce")):
            return "cost_optimization", [
                "估算当前设计成本",
                "识别成本占比最高的组件",
                "给出材料替代或工艺优化建议",
            ]
        if any(token in text for token in ("单价", "价格", "price", "材料费")):
            return "price_inquiry", [
                "查询当前默认材料单价",
                "展示各材料的密度和单价信息",
            ]
        return "cost_estimation", [
            "获取电机几何参数和材料配置",
            "计算各组件材料用量",
            "估算制造成本并输出明细",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_cost_flow(task)
        return (
            f"[{flow_name}] {super().build_execution_plan(task, context)} "
            f"重点步骤: " + "；".join(checklist) + "。"
        )

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_cost_flow(task)
        return (
            f"当前成本分析工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "成本估算基于简化模型，结果仅供参考。\n"
            "如需精确成本，建议结合实际供应商报价和 BOM 清单。\n"
            "如果用户未提供几何参数，可从上下文中提取或使用默认值。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_cost_flow(task)
        run_context.metadata["cost_flow"] = flow_name
        run_context.metadata["cost_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("cost_flow", "cost_estimation")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
