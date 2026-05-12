"""高级网格划分 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import MESHING_TOOL_DEFINITIONS, MESHING_TOOL_REGISTRY


class AdvancedMeshingAgent(SubAgentBase):
    name = "advanced_meshing"
    workflow_stages = ("plan", "import_geometry", "configure_mesh", "generate_mesh", "check_quality", "export", "summarize")
    description = (
        "高级网格划分专家，负责使用 Fluent Meshing / Mechanical 生成结构网格（四面体/六面体）"
        "和流体网格（多面体/Mosaic/边界层），支持几何导入、网格质量检查、局部细化，"
        "以及导出为 Fluent (.msh)、MAPDL (.cdb)、Abaqus (.inp) 等格式"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=MESHING_TOOL_DEFINITIONS,
            tool_registry=MESHING_TOOL_REGISTRY,
        )

    def _infer_mesh_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("流体网格", "流体 mesh", "多面体", "polyhedral", "边界层", "bl")):
            return "fluid_meshing", [
                "导入几何文件",
                "启动 Fluent Meshing",
                "配置多面体/边界层网格参数",
                "生成流体计算域网格",
                "检查网格质量",
            ]
        if any(token in text for token in ("结构网格", "结构 mesh", "四面体", "六面体", "hex", "tet")):
            return "structural_meshing", [
                "导入 CAD 几何",
                "配置四面体/六面体网格参数",
                "生成结构 FE 网格",
                "检查网格质量（偏斜度/纵横比）",
            ]
        if any(token in text for token in ("细化", "refine", "局部加密", "自适应")):
            return "mesh_refinement", [
                "识别高梯度区域",
                "配置局部细化参数",
                "执行局部网格细化",
                "验证细化后网格质量",
            ]
        if any(token in text for token in ("质量", "quality", "检查", "check")):
            return "quality_check", [
                "检查正交质量/偏斜度/纵横比",
                "识别低质量单元",
                "报告网格质量统计",
            ]
        if any(token in text for token in ("导入", "import", "几何", "geometry", "step", "stl")):
            return "geometry_import", [
                "导入 STEP/IGES/STL 几何文件",
                "检查几何完整性",
                "准备网格划分几何",
            ]
        return "meshing_workflow", [
            "启动网格划分会话",
            "导入几何并配置网格参数",
            "生成网格并检查质量",
            "导出网格文件",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_mesh_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_mesh_flow(task)
        return (
            f"当前网格划分工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "网格质量直接影响仿真精度和收敛性，生成后务必检查质量指标。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_mesh_flow(task)
        run_context.metadata["meshing_flow"] = flow_name
        run_context.metadata["meshing_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("meshing_flow", "meshing_workflow")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
