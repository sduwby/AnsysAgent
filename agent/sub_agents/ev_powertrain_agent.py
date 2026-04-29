"""EV 整车电驱系统联仿 Sub-Agent（电池+控制器+电机）。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import EV_POWERTRAIN_TOOL_DEFINITIONS, EV_POWERTRAIN_TOOL_REGISTRY


class EVPowertrainAgent(SubAgentBase):
    name = "ev_powertrain"
    workflow_stages = (
        "plan",
        "setup_battery_and_controller",
        "link_motor",
        "run_cosimulation",
        "extract_results",
        "summarize",
    )
    description = (
        "EV 整车电驱系统联仿专家，负责电池等效电路建模、电机控制器（逆变器+FOC）配置、"
        "Maxwell 电机链接、电池→控制器→电机联合瞬态仿真，以及电驱系统性能结果提取"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=EV_POWERTRAIN_TOOL_DEFINITIONS,
            tool_registry=EV_POWERTRAIN_TOOL_REGISTRY,
        )

    def _infer_powertrain_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("电池", "battery", "soc")):
            return "battery_setup", [
                "配置电池等效电路模型参数",
                "验证电池 OCV 和内阻",
                "连接逆变器拓扑",
            ]
        if any(token in text for token in ("控制器", "controller", "foc", "逆变器", "inverter")):
            return "controller_setup", [
                "配置逆变器拓扑和开关参数",
                "设置控制策略（FOC/DTC）和 PWM 调制",
                "验证母线电压和开关频率",
            ]
        if any(token in text for token in ("联仿", "cosimul", "驱动工况", "wltc", "nedc")):
            return "powertrain_cosimulation", [
                "确认电池→控制器→电机链路完整",
                "配置驱动工况和仿真参数",
                "运行联合仿真并提取系统级结果",
            ]
        if any(token in text for token in ("结果", "result", "波形", "提取")):
            return "powertrain_postprocess", [
                "提取电池电流/电压波形",
                "提取电机转矩/转速曲线",
                "计算系统效率和能耗",
            ]
        return "powertrain_setup", [
            "创建电池和控制器模型",
            "链接 Maxwell 电机设计",
            "配置并运行电驱系统联仿",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_powertrain_flow(task)
        return (
            f"[{flow_name}] {super().build_execution_plan(task, context)} "
            f"重点步骤: " + "；".join(checklist) + "。"
        )

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_powertrain_flow(task)
        return (
            f"当前电驱系统工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "注意：电池模型和控制器模型必须先创建，再链接 Maxwell 电机，最后运行联仿。\n"
            "如果某个步骤失败，优先检查前置条件是否满足。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_powertrain_flow(task)
        run_context.metadata["powertrain_flow"] = flow_name
        run_context.metadata["powertrain_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("powertrain_flow", "powertrain_setup")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
