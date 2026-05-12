"""整车动力学 VD 仿真 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import VD_TOOL_DEFINITIONS, VD_TOOL_REGISTRY


class VehicleDynamicsAgent(SubAgentBase):
    name = "vehicle_dynamics"
    workflow_stages = ("plan", "define_vehicle", "configure_manuever", "solve", "postprocess", "summarize")
    description = (
        "整车动力学 VD 仿真专家，负责定义整车动力学参数（质量/轴距/悬架/K&C）、"
        "配置操稳性工况（稳态回转/转向瞬态/侧风稳定性）、"
        "平顺性分析（随机路面/脉冲激励）、制动和加速性能仿真，"
        "以及横摆角速度/侧向加速度/车身侧倾角等操稳性指标提取"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=VD_TOOL_DEFINITIONS,
            tool_registry=VD_TOOL_REGISTRY,
        )

    def _infer_vd_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("操稳", "稳态回转", "cornering", "不足转向", "转向")):
            return "handling_analysis", [
                "定义整车动力学参数",
                "配置稳态回转/转向瞬态工况",
                "运行多体动力学仿真",
                "提取不足转向梯度和横摆响应",
            ]
        if any(token in text for token in ("平顺", "ride", "随机路面", "路面激励", "过坎")):
            return "ride_comfort", [
                "定义整车质量和悬架参数",
                "配置随机路面谱和行驶速度",
                "运行平顺性仿真",
                "提取座椅加速度和 ISO 2631 评价",
            ]
        if any(token in text for token in ("制动", "braking", "刹车", "制动距离")):
            return "braking_analysis", [
                "定义制动系统参数",
                "配置制动工况",
                "运行制动仿真",
                "提取制动距离和方向稳定性",
            ]
        if any(token in text for token in ("悬架", "suspension", "kc", "运动学", "弹性运动学")):
            return "suspension_kc", [
                "定义悬架几何参数",
                "配置轮跳/转向输入",
                "运行 K&C 分析",
                "提取外倾角/前束角/侧倾中心",
            ]
        if any(token in text for token in ("加速", "acceleration", "动力性")):
            return "acceleration_analysis", [
                "定义传动系统参数",
                "配置加速工况",
                "运行加速性能仿真",
                "提取 0-100 加速时间和距离",
            ]
        return "vd_workflow", [
            "连接动力学求解器",
            "定义整车参数",
            "配置仿真工况",
            "运行仿真并提取 VD 结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_vd_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_vd_flow(task)
        return (
            f"当前整车动力学工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "整车动力学仿真通常需要先定义整车参数，再配置具体工况。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_vd_flow(task)
        run_context.metadata["vd_flow"] = flow_name
        run_context.metadata["vd_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("vd_flow", "vd_workflow")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
