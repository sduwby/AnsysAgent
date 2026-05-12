"""疲劳耐久仿真 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import FATIGUE_TOOL_DEFINITIONS, FATIGUE_TOOL_REGISTRY


class FatigueAgent(SubAgentBase):
    name = "fatigue"
    workflow_stages = ("plan", "load_structural_results", "define_fatigue_properties", "configure_load_spectrum", "solve", "postprocess", "summarize")
    description = (
        "疲劳耐久仿真专家，负责基于 S-N/E-N 曲线的整车和零部件疲劳寿命分析、"
        "载荷谱定义（恒幅/变幅/块谱）、平均应力修正（Goodman/Gerber/SWT）、"
        "Miner 线性损伤累积、疲劳热点识别和寿命预测"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=FATIGUE_TOOL_DEFINITIONS,
            tool_registry=FATIGUE_TOOL_REGISTRY,
        )

    def _infer_fatigue_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("s-n", "sn", "高周", "high cycle", "应力寿命")):
            return "sn_analysis", [
                "加载结构应力结果",
                "定义 S-N 曲线材料参数",
                "配置载荷谱",
                "运行应力-寿命疲劳分析",
                "提取疲劳寿命分布",
            ]
        if any(token in text for token in ("e-n", "en", "低周", "low cycle", "应变寿命")):
            return "en_analysis", [
                "加载结构应变结果",
                "定义 E-N 曲线材料参数",
                "配置应变控制载荷谱",
                "运行应变-寿命疲劳分析",
                "提取低周疲劳寿命",
            ]
        if any(token in text for token in ("裂纹", "crack", "断裂", "fracture")):
            return "crack_growth", [
                "定义裂纹初始尺寸",
                "配置断裂力学材料参数",
                "运行裂纹扩展分析",
                "提取裂纹扩展寿命",
            ]
        if any(token in text for token in ("损伤", "damage", "miners")):
            return "damage_analysis", [
                "加载疲劳分析结果",
                "计算 Miner 线性损伤累积",
                "评估结构损伤分布",
            ]
        return "fatigue_workflow", [
            "连接疲劳分析求解器",
            "加载结构结果并定义疲劳材料",
            "配置载荷谱和修正方法",
            "运行疲劳分析并提取寿命结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_fatigue_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_fatigue_flow(task)
        return (
            f"当前疲劳分析工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "疲劳分析依赖结构分析结果（应力/应变场），请确保先完成结构分析。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_fatigue_flow(task)
        run_context.metadata["fatigue_flow"] = flow_name
        run_context.metadata["fatigue_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("fatigue_flow", "fatigue_workflow")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
