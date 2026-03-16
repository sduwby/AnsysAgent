"""Fluent CFD 流体 Sub-Agent。"""
from __future__ import annotations
from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import FLUENT_TOOL_DEFINITIONS, FLUENT_TOOL_REGISTRY


class FluentAgent(SubAgentBase):
    name = "fluent"
    description = (
        "Ansys Fluent CFD 流体仿真专家，负责连接 Fluent、读取网格、配置湍流模型和边界条件、"
        "设置求解器、运行稳态流体仿真、提取压降/速度/温度结果和导出数据"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=FLUENT_TOOL_DEFINITIONS,
            tool_registry=FLUENT_TOOL_REGISTRY,
        )
