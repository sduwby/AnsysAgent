"""碰撞安全仿真 Sub-Agent（LS-DYNA via PyDyna）。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import CRASH_TOOL_DEFINITIONS, CRASH_TOOL_REGISTRY


class CrashAgent(SubAgentBase):
    name = "crash"
    workflow_stages = ("plan", "prepare_model", "setup_contacts_materials", "configure_crash_case", "solve", "postprocess", "summarize")
    description = (
        "LS-DYNA 碰撞安全仿真专家，负责通过 PyDyna 构建碰撞仿真 Deck、"
        "加载整车 .k 模型、配置材料/截面/接触/刚性壁障、设置正面/侧面/后部碰撞及行人保护工况、"
        "运行 LS-DYNA 显式动力学求解、提取碰撞加速度/侵入量/能量和假人损伤指标"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=CRASH_TOOL_DEFINITIONS,
            tool_registry=CRASH_TOOL_REGISTRY,
        )

    def _infer_crash_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("正面碰撞", "frontal", "偏置", "offset")):
            return "frontal_crash", [
                "创建或加载碰撞 Deck",
                "配置正面碰撞材料和接触",
                "设置正面碰撞工况控制卡片",
                "运行 LS-DYNA 求解",
                "提取加速度和假人损伤结果",
            ]
        if any(token in text for token in ("侧面碰撞", "side", "柱碰", "pole")):
            return "side_impact", [
                "加载整车模型",
                "配置侧面碰撞接触和材料",
                "设置侧面碰撞壁障和初始速度",
                "运行 LS-DYNA 求解",
                "提取侧面侵入量和 TTI 指标",
            ]
        if any(token in text for token in ("后部碰撞", "rear", "追尾", "尾碰")):
            return "rear_impact", [
                "加载后碰模型",
                "配置后部碰撞工况",
                "运行 LS-DYNA 求解",
                "提取后碰结构响应",
            ]
        if any(token in text for token in ("行人保护", "pedestrian", "头部冲击", "腿部冲击")):
            return "pedestrian_protection", [
                "配置行人保护冲击器模型",
                "设置头部/腿部冲击工况",
                "运行 LS-DYNA 求解",
                "提取 HIC 和腿部损伤指标",
            ]
        if any(token in text for token in ("材料", "接触", "deck", "构建", "关键字")):
            return "model_setup", [
                "创建碰撞 Deck",
                "添加材料、截面、部件",
                "配置接触和壁障",
            ]
        return "crash_workflow", [
            "创建或加载碰撞 Deck",
            "配置材料和接触",
            "设置碰撞工况",
            "运行 LS-DYNA 显式动力学求解",
            "提取碰撞结果和损伤指标",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_crash_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_crash_flow(task)
        return (
            f"当前碰撞仿真工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "注意：LS-DYNA 使用 mm-ton-s 单位制；接触定义是碰撞仿真的关键。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_crash_flow(task)
        run_context.metadata["crash_flow"] = flow_name
        run_context.metadata["crash_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("crash_flow", "crash_workflow")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
