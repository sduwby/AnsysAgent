"""报告生成 Sub-Agent。"""
from __future__ import annotations
from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import REPORTING_TOOL_DEFINITIONS, REPORTING_TOOL_REGISTRY


class ReportingAgent(SubAgentBase):
    name = "reporting"
    description = (
        "仿真报告生成专家，负责使用 Ansys Dynamic Reporting 或内置 HTML 模板，"
        "生成包含文本、表格和仿真云图的分析报告，并导出为 HTML/PDF 格式"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=REPORTING_TOOL_DEFINITIONS,
            tool_registry=REPORTING_TOOL_REGISTRY,
        )
