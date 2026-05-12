"""Sub-agents package."""
from agent.sub_agents.maxwell_agent import MaxwellAgent
from agent.sub_agents.icepak_agent import IcepakAgent
from agent.sub_agents.fluent_agent import FluentAgent
from agent.sub_agents.mapdl_agent import MapdlAgent
from agent.sub_agents.motorcad_agent import MotorCADAgent
from agent.sub_agents.optimization_agent import OptimizationAgent
from agent.sub_agents.reporting_agent import ReportingAgent
from agent.sub_agents.ev_powertrain_agent import EVPowertrainAgent
from agent.sub_agents.nvh_agent import NVHAgent
from agent.sub_agents.cost_agent import CostAgent
from agent.sub_agents.crash_agent import CrashAgent
from agent.sub_agents.vehicle_cfd_agent import VehicleCFDAgent
from agent.sub_agents.fatigue_agent import FatigueAgent
from agent.sub_agents.vehicle_dynamics_agent import VehicleDynamicsAgent
from agent.sub_agents.vehicle_structural_agent import VehicleStructuralAgent
from agent.sub_agents.advanced_meshing_agent import AdvancedMeshingAgent
from agent.sub_agents.vehicle_nvh_agent import VehicleNVHAgent
from agent.sub_agents.test_data_agent import TestDataAgent

__all__ = [
    "MaxwellAgent", "IcepakAgent", "FluentAgent", "MapdlAgent",
    "MotorCADAgent", "OptimizationAgent", "ReportingAgent",
    "EVPowertrainAgent", "NVHAgent", "CostAgent",
    "CrashAgent", "VehicleCFDAgent", "FatigueAgent",
    "VehicleDynamicsAgent", "VehicleStructuralAgent",
    "AdvancedMeshingAgent", "VehicleNVHAgent", "TestDataAgent",
]
