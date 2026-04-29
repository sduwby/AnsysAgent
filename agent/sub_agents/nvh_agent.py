"""NVH（噪声、振动与声振粗糙度）Sub-Agent：整合电磁力→结构振动→声学完整链路。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import NVH_TOOL_DEFINITIONS, NVH_TOOL_REGISTRY


class NVHAgent(SubAgentBase):
    name = "nvh"
    workflow_stages = (
        "plan",
        "extract_electromagnetic_forces",
        "setup_structural_model",
        "modal_analysis",
        "harmonic_response",
        "noise_evaluation",
        "summarize",
    )
    description = (
        "电机 NVH（噪声、振动与声振粗糙度）分析专家，负责从 Maxwell 电磁仿真提取电磁力，"
        "导入 Mechanical/MAPDL 结构模型，运行模态和谐响应分析，评估振动加速度和声压级，"
        "完成电磁力→结构振动→声学的完整 NVH 链路"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=NVH_TOOL_DEFINITIONS,
            tool_registry=NVH_TOOL_REGISTRY,
        )

    def _infer_nvh_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("完整", "full", "链路", "chain", "端到端", "end")):
            return "nvh_full_chain", [
                "从 Maxwell 提取电磁力（径向+切向）",
                "导入结构模型作为载荷",
                "运行模态分析获取固有频率",
                "运行谐响应分析获取振动响应",
                "估算声压级（SPL）",
            ]
        if any(token in text for token in ("电磁力", "force", "maxwell", "激励")):
            return "em_force_extraction", [
                "连接 Maxwell 并确认仿真已完成",
                "提取径向/切向电磁力密度",
                "导出力数据为结构分析可用格式",
            ]
        if any(token in text for token in ("模态", "modal", "固有频率", "振型")):
            return "nvh_modal", [
                "连接 Mechanical/MAPDL",
                "设置足够的模态阶数和频率范围",
                "提取固有频率和振型",
            ]
        if any(token in text for token in ("谐响应", "harmonic", "振动", "vibration")):
            return "nvh_harmonic", [
                "确认电磁力已导入结构模型",
                "设置频率范围和步数",
                "运行谐响应分析并提取振动速度/加速度",
            ]
        if any(token in text for token in ("噪声", "noise", "声压", "spl", "声学")):
            return "nvh_noise", [
                "确认谐响应分析已完成",
                "提取表面振动速度",
                "计算等效声压级",
            ]
        return "nvh_analysis", [
            "提取电磁力并导入结构模型",
            "运行模态和谐响应分析",
            "评估振动和噪声水平",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_nvh_flow(task)
        return (
            f"[{flow_name}] {super().build_execution_plan(task, context)} "
            f"重点步骤: " + "；".join(checklist) + "。"
        )

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_nvh_flow(task)
        return (
            f"当前 NVH 工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "NVH 分析必须按顺序：先提取电磁力 → 再导入结构 → 模态 → 谐响应 → 噪声评估。\n"
            "如果需要一键跑全流程，可使用 run_nvh_full_chain 工具。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_nvh_flow(task)
        run_context.metadata["nvh_flow"] = flow_name
        run_context.metadata["nvh_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("nvh_flow", "nvh_analysis")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
