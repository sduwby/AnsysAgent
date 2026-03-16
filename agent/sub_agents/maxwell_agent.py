"""Maxwell 电磁仿真 Sub-Agent（含网格、结果提取、RMXprt、Circuit、可视化）。"""
from __future__ import annotations
from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import MAXWELL_TOOL_DEFINITIONS, MAXWELL_TOOL_REGISTRY


class MaxwellAgent(SubAgentBase):
    name = "maxwell"
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
