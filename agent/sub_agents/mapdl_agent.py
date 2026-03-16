"""MAPDL 结构/NVH/DPF Sub-Agent。"""
from __future__ import annotations
from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import MAPDL_TOOL_DEFINITIONS, MAPDL_TOOL_REGISTRY


class MapdlAgent(SubAgentBase):
    name = "mapdl"
    description = (
        "PyMAPDL/Mechanical/DPF 结构仿真专家，负责连接 Mechanical/MAPDL、"
        "导入电磁力、运行模态/谐响应/NVH 分析、提取振动和结构结果，"
        "以及使用 PyDPF-Post 进行应力/温度/变形场后处理和 CSV 导出"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=MAPDL_TOOL_DEFINITIONS,
            tool_registry=MAPDL_TOOL_REGISTRY,
        )
