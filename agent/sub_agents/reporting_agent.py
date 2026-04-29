"""报告生成 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import REPORTING_TOOL_DEFINITIONS, REPORTING_TOOL_REGISTRY


class ReportingAgent(SubAgentBase):
    name = "reporting"
    workflow_stages = ("plan", "collect_assets", "compose_report", "export_report", "summarize")
    description = (
        "仿真报告生成专家，负责使用 Ansys Dynamic Reporting、内置 HTML 模板或 Word (docx) 模板，"
        "生成包含文本、表格和仿真云图的分析报告，并导出为 HTML/PDF/DOCX 格式"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=REPORTING_TOOL_DEFINITIONS,
            tool_registry=REPORTING_TOOL_REGISTRY,
        )

    def _infer_reporting_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("pdf", "docx", "word", "导出", "export")):
            return "report_export", [
                "检查报告会话和章节内容",
                "执行 HTML/PDF/DOCX 导出",
                "确认输出文件已生成",
            ]
        if any(token in text for token in ("图片", "表格", "image", "table", "section", "章节")):
            return "report_composition", [
                "收集文本、图像和表格素材",
                "组织章节并插入报告内容",
                "生成最终报告草稿",
            ]
        return "report_generation", [
            "创建或连接报告会话",
            "整理结果素材并构建报告结构",
            "导出目标格式的分析报告",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_reporting_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_reporting_flow(task)
        return (
            f"当前报告工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "导出前先确认章节、表格和图片素材已经齐全，避免生成空报告。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_reporting_flow(task)
        run_context.metadata["reporting_flow"] = flow_name
        run_context.metadata["reporting_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("reporting_flow", "report_generation")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
