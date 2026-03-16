"""optiSLang 优化 + 参数扫描 Sub-Agent。"""
from __future__ import annotations
from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import OPTIMIZATION_TOOL_DEFINITIONS, OPTIMIZATION_TOOL_REGISTRY


class OptimizationAgent(SubAgentBase):
    name = "optimization"
    description = (
        "Ansys optiSLang 优化与参数扫描专家，负责连接 optiSLang、设置设计变量和目标函数、"
        "运行敏感性分析和多目标优化，以及 Maxwell 参数化扫描（单参数线性扫描和二维效率 MAP）"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=OPTIMIZATION_TOOL_DEFINITIONS,
            tool_registry=OPTIMIZATION_TOOL_REGISTRY,
        )
