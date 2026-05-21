"""Maxwell 电磁仿真 Sub-Agent（含网格、结果提取、RMXprt、Circuit、可视化）。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import MAXWELL_TOOL_DEFINITIONS, MAXWELL_TOOL_REGISTRY


class MaxwellAgent(SubAgentBase):
    name = "maxwell"
    workflow_stages = ("plan", "model_or_configure", "solve", "postprocess", "summarize")
    description = (
        "Ansys Maxwell 电磁仿真专家，负责几何建模、材料赋值、绕组配置、求解设置、"
        "网格控制、结果提取（转矩/反电动势/电感/效率 MAP/退磁校核）、"
        "场量可视化、RMXprt 快速初设计以及 Circuit 驱动器联仿"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=MAXWELL_TOOL_DEFINITIONS,
            tool_registry=MAXWELL_TOOL_REGISTRY,
        )

    def _infer_maxwell_flow(self, task: str) -> tuple[str, list[str]]:
        """
        根据任务描述推断 Maxwell 工作流类型和执行清单。
        
        Args:
            task: 用户任务描述
        
        Returns:
            tuple[str, list[str]]: (工作流类型名称，执行检查清单)
        """
        text = task.lower()
        
        # 否定词检测：如果是取消/删除操作，走通用流程
        if self.has_negative_words(text):
            return "general_analysis", [
                "确认当前项目、设计和求解前置条件",
                "按需配置模型/网格/边界/设置",
                "执行求解并提取用户请求的结果",
            ]
        
        # 多任务组合检测：如果包含多个关键词，按优先级排序
        tasks = []
        
        # 1. 效率 MAP/参数扫描（优先级最高，因为需要完整的建模 + 求解 + 后处理）
        if any(token in text for token in ("效率", "efficiency", "map", "扫描", "sweep", "优化", "optimization", "parametric")):
            tasks.append(("performance_map", [
                "检查现有设计变量和已求解 setup",
                "必要时创建参数扫描或效率 MAP",
                "执行求解并收集扭矩/损耗/效率结果",
            ]))
        
        # 2. 反电动势/瞬态分析
        if any(token in text for token in ("反电动势", "back emf", "bemf", "瞬态", "transient", "波形")):
            tasks.append(("transient_postprocess", [
                "确认或建立瞬态求解设置",
                "运行求解并提取 Back EMF/波形数据",
                "校验结果是否已导出或可复用",
            ]))
        
        # 3. 建模任务（基础任务，优先级最低）
        if any(token in text for token in ("建模", "geometry", "pmsm", "电机", "槽", "极", "创建", "建立")):
            tasks.append(("model_building", [
                "连接 AEDT 或打开现有项目",
                "建立或修正几何/材料/绕组/网格",
                "补充求解设置并在需要时运行校验求解",
            ]))
        
        # 4. 结果提取（单独一类）
        if any(token in text for token in ("提取", "结果", "torque", "损耗", "loss", "电感", "inductance")):
            if not tasks:  # 仅当没有其他任务时才单独列出
                tasks.append(("result_extraction", [
                    "确认已完成求解",
                    "提取用户请求的结果（转矩/反电动势/损耗/电感等）",
                    "必要时导出结果数据",
                ]))
        
        # 如果没有匹配到特定任务，走通用流程
        if not tasks:
            return "general_analysis", [
                "确认当前项目、设计和求解前置条件",
                "按需配置模型/网格/边界/设置",
                "执行求解并提取用户请求的结果",
            ]
        
        # 如果只有一个任务，直接返回
        if len(tasks) == 1:
            return tasks[0]
        
        # 多个任务组合：返回复合类型，合并检查清单
        flow_names = [t[0] for t in tasks]
        combined_checklist = []
        for _, checklist in tasks:
            combined_checklist.extend(checklist)
        
        return ("+".join(flow_names), combined_checklist)

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_maxwell_flow(task)
        base_plan = super().build_execution_plan(task, context)
        return f"[{flow_name}] {base_plan} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_maxwell_flow(task)
        return (
            f"当前 Maxwell 工作流类型：{flow_name}。\n"
            f"请严格遵循阶段 {' -> '.join(self.workflow_stages)}。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "优先复用已有项目/设计/求解设置；只有在缺失时再创建新对象。\n"
            "如果结果提取依赖未求解 setup，先明确完成求解再提取。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_maxwell_flow(task)
        run_context.metadata["maxwell_flow"] = flow_name
        run_context.metadata["maxwell_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("maxwell_flow", "general_analysis")
        step_count = len(run_context.steps)
        if run_context.output:
            run_context.output = f"[{flow_name}] {run_context.output}"
            run_context.metadata["final_summary"] = run_context.output
        else:
            run_context.output = f"[{flow_name}] Maxwell 任务已完成，共执行 {step_count} 个步骤。"
            run_context.metadata["final_summary"] = run_context.output
