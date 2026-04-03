"""Icepak 热分析 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import ICEPAK_TOOL_DEFINITIONS, ICEPAK_TOOL_REGISTRY


class IcepakAgent(SubAgentBase):
    name = "icepak"
    workflow_stages = ("plan", "configure_thermal_model", "solve", "postprocess", "summarize")
    description = "Ansys Icepak 热仿真专家，负责连接 Icepak、设置热源边界条件、运行稳态热仿真和提取温升结果"

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=ICEPAK_TOOL_DEFINITIONS,
            tool_registry=ICEPAK_TOOL_REGISTRY,
        )

    def _infer_icepak_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("耦合", "loss", "损耗", "maxwell", "电磁热")):
            return "em_thermal_coupling", [
                "检查电磁损耗输入是否可用",
                "设置热源与边界条件",
                "运行热分析并校验温升分布",
            ]
        if any(token in text for token in ("温度", "温升", "temperature", "thermal result", "结果")):
            return "thermal_postprocess", [
                "确认已有热模型和求解设置",
                "必要时运行热求解",
                "提取绕组/定转子温度结果",
            ]
        return "thermal_setup", [
            "连接或打开 Icepak 设计",
            "配置热源、开口和热求解设置",
            "运行求解并输出温度结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_icepak_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_icepak_flow(task)
        return (
            f"当前 Icepak 工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "优先复用已有热边界和热源配置；若热源来自电磁损耗，先确认损耗输入有效。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_icepak_flow(task)
        run_context.metadata["icepak_flow"] = flow_name
        run_context.metadata["icepak_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("icepak_flow", "thermal_setup")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
