"""整车结构强度仿真 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import VSTRUCT_TOOL_DEFINITIONS, VSTRUCT_TOOL_REGISTRY


class VehicleStructuralAgent(SubAgentBase):
    name = "vehicle_structural"
    workflow_stages = ("plan", "load_model", "define_materials_loads", "solve", "postprocess", "summarize")
    description = (
        "整车结构强度仿真专家，负责加载整车/零部件 FE 模型、定义材料属性（线性/非线性）、"
        "配置边界条件和载荷（弯曲/扭转/准静态工况如过坎/急转弯）、"
        "运行静强度/模态/屈曲分析，以及提取应力/位移/安全系数等结构强度结果"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=VSTRUCT_TOOL_DEFINITIONS,
            tool_registry=VSTRUCT_TOOL_REGISTRY,
        )

    def _infer_structural_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("弯曲", "bending", "弯矩")):
            return "bending_analysis", [
                "加载整车模型",
                "定义材料和边界条件",
                "施加弯曲载荷（满载弯曲）",
                "运行静力分析",
                "提取弯曲应力和位移结果",
            ]
        if any(token in text for token in ("扭转", "torsion", "扭转载荷")):
            return "torsion_analysis", [
                "加载整车模型",
                "施加扭转载荷（单侧悬空）",
                "运行静力分析",
                "提取扭转刚度和应力分布",
            ]
        if any(token in text for token in ("过坎", "过坑", "bump", "pothole", "准静态", "quasi")):
            return "quasi_static", [
                "定义准静态载荷工况",
                "施加垂向/侧向/纵向加速度",
                "运行非线性静力分析",
                "提取极限强度和安全系数",
            ]
        if any(token in text for token in ("模态", "modal", "固有频率", "频率")):
            return "modal_analysis", [
                "加载结构模型",
                "配置模态分析参数",
                "运行模态求解",
                "提取固有频率和振型",
            ]
        if any(token in text for token in ("屈曲", "buckling", "稳定性")):
            return "buckling_analysis", [
                "加载结构模型",
                "施加预应力载荷",
                "运行屈曲分析",
                "提取屈曲载荷因子和模态",
            ]
        if any(token in text for token in ("安全系数", "safety", "强度评估")):
            return "strength_assessment", [
                "加载分析结果",
                "提取 Von Mises 应力分布",
                "计算安全系数",
                "评估结构强度裕度",
            ]
        return "structural_workflow", [
            "连接结构分析求解器",
            "加载模型并定义材料属性",
            "配置边界条件和载荷工况",
            "运行分析并提取结构强度结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_structural_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_structural_flow(task)
        return (
            f"当前结构强度分析工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "结构强度分析需要确保网格质量、材料属性和边界条件正确设置。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_structural_flow(task)
        run_context.metadata["structural_flow"] = flow_name
        run_context.metadata["structural_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("structural_flow", "structural_workflow")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
