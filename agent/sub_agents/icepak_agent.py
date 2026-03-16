"""Icepak 热分析 Sub-Agent。"""
from __future__ import annotations
from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import ICEPAK_TOOL_DEFINITIONS, ICEPAK_TOOL_REGISTRY


class IcepakAgent(SubAgentBase):
    name = "icepak"
    description = "Ansys Icepak 热仿真专家，负责连接 Icepak、设置热源边界条件、运行稳态热仿真和提取温升结果"

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=ICEPAK_TOOL_DEFINITIONS,
            tool_registry=ICEPAK_TOOL_REGISTRY,
        )
