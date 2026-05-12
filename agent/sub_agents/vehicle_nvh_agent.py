"""整车 NVH 仿真 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import VEHICLE_NVH_TOOL_DEFINITIONS, VEHICLE_NVH_TOOL_REGISTRY


class VehicleNVHAgent(SubAgentBase):
    name = "vehicle_nvh"
    workflow_stages = ("plan", "load_model", "configure_nvh", "solve", "postprocess", "summarize")
    description = (
        "整车 NVH 仿真专家，负责白车身/整车模态分析、频率响应分析（FRF）、"
        "声腔模态和声固耦合分析、路噪/风噪传递路径分析，"
        "以及声品质评价（响度/尖锐度/粗糙度）和 NVH 性能指标提取"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=VEHICLE_NVH_TOOL_DEFINITIONS,
            tool_registry=VEHICLE_NVH_TOOL_REGISTRY,
        )

    def _infer_nvh_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("模态", "modal", "固有频率", "振型")):
            return "modal_analysis", [
                "加载整车 NVH 模型",
                "配置模态分析参数（自由/约束状态）",
                "运行模态分析",
                "提取固有频率和振型",
            ]
        if any(token in text for token in ("频率响应", "frf", "传递函数", "导纳")):
            return "frequency_response", [
                "加载结构模型",
                "配置激励点和响应点",
                "运行谐响应分析",
                "提取 FRF 曲线和共振频率",
            ]
        if any(token in text for token in ("声腔", "acoustic", "声学", "声固耦合")):
            return "acoustic_analysis", [
                "加载声腔模型",
                "配置声固耦合边界",
                "运行声学模态分析",
                "提取声腔共振频率和 SPL",
            ]
        if any(token in text for token in ("路噪", "road noise", "路面噪声", "路噪传递")):
            return "road_noise", [
                "加载整车和路面激励模型",
                "配置悬架传递路径",
                "运行路噪仿真",
                "提取传递路径贡献和车内 SPL",
            ]
        if any(token in text for token in ("风噪", "wind noise", "气动噪声")):
            return "wind_noise", [
                "配置气动声学激励源",
                "运行风噪仿真",
                "提取车窗声压级和声品质指标",
            ]
        if any(token in text for token in ("声品质", "sound quality", "响度", "尖锐度")):
            return "sound_quality", [
                "加载 NVH 时域/频域数据",
                "计算响度（sone）和尖锐度（acum）",
                "评估声品质主观评价指标",
            ]
        return "nvh_workflow", [
            "连接 NVH 求解器",
            "加载整车模型（结构+声腔）",
            "配置 NVH 分析工况",
            "运行分析并提取 NVH 结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_nvh_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_nvh_flow(task)
        return (
            f"当前整车 NVH 工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "NVH 分析通常需要高频分辨率，注意频率范围和阻尼参数设置。"
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
        flow_name = run_context.metadata.get("nvh_flow", "nvh_workflow")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
