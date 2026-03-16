"""Sub-agents package."""
from agent.sub_agents.maxwell_agent import MaxwellAgent
from agent.sub_agents.icepak_agent import IcepakAgent
from agent.sub_agents.fluent_agent import FluentAgent
from agent.sub_agents.mapdl_agent import MapdlAgent
from agent.sub_agents.motorcad_agent import MotorCADAgent
from agent.sub_agents.optimization_agent import OptimizationAgent
from agent.sub_agents.reporting_agent import ReportingAgent

__all__ = [
    "MaxwellAgent", "IcepakAgent", "FluentAgent", "MapdlAgent",
    "MotorCADAgent", "OptimizationAgent", "ReportingAgent",
]
