"""Motor-CAD 解析初设计 Sub-Agent。"""
from __future__ import annotations
from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import MOTORCAD_TOOL_DEFINITIONS, MOTORCAD_TOOL_REGISTRY


class MotorCADAgent(SubAgentBase):
    name = "motorcad"
    description = (
        "Ansys Motor-CAD 解析法初设计专家，负责连接 Motor-CAD、配置电机几何参数、"
        "运行 EM/热网络/NVH 分析、生成效率 MAP，并将结果导出到 Maxwell 进行精确 FEM 仿真"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=MOTORCAD_TOOL_DEFINITIONS,
            tool_registry=MOTORCAD_TOOL_REGISTRY,
        )
