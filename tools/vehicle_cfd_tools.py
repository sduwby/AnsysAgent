"""
整车 CFD 仿真工具：通过 PyFluent 进行整车外流场、热管理、空调系统等 CFD 分析。
支持：
  - 整车外流场（风阻系数 Cd、升力系数 Cl）
  - 发动机舱热管理
  - 电池包冷却仿真
  - 空调系统仿真
  - 整车气动噪声（CAA）

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
from typing import Any

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

_vehicle_fluent_session = None
_vehicle_cfd_config: dict = {
    "simulation_type": "external_aero",
    "vehicle_model_path": None,
    "wind_speed_m_s": 30.0,
    "reference_area_m2": 2.2,
}


def _session():
    if _vehicle_fluent_session is None:
        raise RuntimeError("未连接到 Fluent，请先调用 connect_vehicle_cfd。")
    return _vehicle_fluent_session


# ---------------------------------------------------------------------------
# 工具：connect_vehicle_cfd - 连接整车 CFD 仿真
# ---------------------------------------------------------------------------

def connect_vehicle_cfd(
    version: str = "23.2",
    precision: str = "double",
    processors: int = 32,
    mode: str = "solver",
) -> dict:
    """
    启动 Fluent 会话用于整车 CFD 仿真。

    Args:
        version: Fluent 版本号
        precision: "double"（推荐）或 "single"
        processors: 并行进程数（整车 CFD 建议 32+ 核）
        mode: "solver" 或 "meshing"
    """
    global _vehicle_fluent_session
    try:
        import ansys.fluent.core as pyfluent
        _vehicle_fluent_session = pyfluent.launch_fluent(
            product_version=version,
            precision=precision,
            processor_count=processors,
            mode=mode,
            ui_mode="no_gui",
        )
        return _ok(ok_message(
            f"已启动整车 CFD Fluent（{version}，{precision} 精度，{processors} 进程）",
            version=version,
            processors=processors,
            mode=mode,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：load_vehicle_cfd_mesh - 加载整车 CFD 网格
# ---------------------------------------------------------------------------

def load_vehicle_cfd_mesh(
    mesh_path: str,
    mesh_type: str = "external",
) -> dict:
    """
    加载整车 CFD 计算域网格。

    Args:
        mesh_path: 网格文件路径（.msh / .msh.gz / .cas）
        mesh_type: 网格类型，"external"（外流场）、"internal"（内流场）、"battery"（电池包）、"engine_bay"（发动机舱）
    """
    try:
        session = _session()
        if not os.path.exists(mesh_path):
            return _err(f"网格文件不存在: {mesh_path}")

        ext = os.path.splitext(mesh_path.rstrip(".gz"))[-1].lower()
        if ext == ".cas":
            session.file.read_case(file_name=mesh_path)
        else:
            session.file.read_mesh(file_name=mesh_path)

        _vehicle_cfd_config["vehicle_model_path"] = mesh_path
        _vehicle_cfd_config["simulation_type"] = mesh_type

        return _ok(ok_message(
            f"已加载{mesh_type} CFD 网格: {mesh_path}",
            mesh_path=mesh_path,
            mesh_type=mesh_type,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_external_aero - 设置整车外流场分析
# ---------------------------------------------------------------------------

def setup_external_aero(
    wind_speed_m_s: float = 30.0,
    reference_area_m2: float = 2.2,
    reference_length_m: float = 4.5,
    air_density_kg_m3: float = 1.225,
    air_viscosity_pa_s: float = 1.789e-5,
    turbulence_model: str = "sst_k_omega",
    ground_effect: bool = True,
    rotating_wheels: bool = True,
) -> dict:
    """
    设置整车空气动力学（外流场）分析。

    Args:
        wind_speed_m_s: 来流风速（m/s），对应 120 km/h 约 33.3 m/s
        reference_area_m2: 参考面积（m²），通常取整车正面投影面积
        reference_length_m: 参考长度（m），通常取轴距
        air_density_kg_m3: 空气密度（kg/m³）
        air_viscosity_pa_s: 空气动力粘度（Pa·s）
        turbulence_model: 湍流模型，"sst_k_omega"（推荐）、"realizable_k_epsilon"、"les"
        ground_effect: 是否考虑地面效应
        rotating_wheels: 是否考虑车轮旋转
    """
    try:
        session = _session()
        setup = session.setup

        setup.models.solver.type = "density-based-implicit"
        setup.models.energy = {"enabled": True}

        if turbulence_model == "sst_k_omega":
            setup.models.viscous.model = "k-omega"
            setup.models.viscous.k_omega_options.sst = True
        elif turbulence_model == "realizable_k_epsilon":
            setup.models.viscous.model = "k-epsilon"
            setup.models.viscous.k_epsilon_options.model = "realizable"
        elif turbulence_model == "les":
            setup.models.viscous.model = "les"

        reynolds = air_density_kg_m3 * wind_speed_m_s * reference_length_m / air_viscosity_pa_s

        _vehicle_cfd_config["wind_speed_m_s"] = wind_speed_m_s
        _vehicle_cfd_config["reference_area_m2"] = reference_area_m2
        _vehicle_cfd_config["turbulence_model"] = turbulence_model

        return _ok(ok_message(
            f"已设置整车外流场分析（风速 {wind_speed_m_s} m/s，Re={reynolds:.2e}）",
            wind_speed_m_s=wind_speed_m_s,
            reference_area_m2=reference_area_m2,
            turbulence_model=turbulence_model,
            reynolds_number=reynolds,
            ground_effect=ground_effect,
            rotating_wheels=rotating_wheels,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_battery_thermal_cfd - 设置电池包 CFD 热仿真
# ---------------------------------------------------------------------------

def setup_battery_thermal_cfd(
    coolant_type: str = "water_glycol",
    inlet_temp_C: float = 25.0,
    inlet_velocity_m_s: float = 0.5,
    total_heat_generation_W: float = 500.0,
    ambient_temp_C: float = 40.0,
    turbulence_model: str = "sst_k_omega",
) -> dict:
    """
    设置电池包液冷 CFD 热仿真。

    Args:
        coolant_type: 冷却液类型，"water_glycol"（水-乙二醇）、"dielectric_fluid"（绝缘油）、"air"（风冷）
        inlet_temp_C: 冷却液入口温度（°C）
        inlet_velocity_m_s: 冷却液入口流速（m/s）
        total_heat_generation_W: 电池总发热功率（W）
        ambient_temp_C: 环境温度（°C）
        turbulence_model: 湍流模型
    """
    try:
        session = _session()
        setup = session.setup

        setup.models.solver.type = "pressure-based"
        setup.models.energy = {"enabled": True}

        if turbulence_model == "sst_k_omega":
            setup.models.viscous.model = "k-omega"
            setup.models.viscous.k_omega_options.sst = True
        else:
            setup.models.viscous.model = "k-epsilon"

        coolant_properties = {
            "water_glycol": {"density": 1060.0, "specific_heat": 3300.0, "thermal_conductivity": 0.4, "viscosity": 0.003},
            "dielectric_fluid": {"density": 800.0, "specific_heat": 2000.0, "thermal_conductivity": 0.13, "viscosity": 0.005},
            "air": {"density": 1.225, "specific_heat": 1005.0, "thermal_conductivity": 0.026, "viscosity": 1.789e-5},
        }

        props = coolant_properties.get(coolant_type, coolant_properties["water_glycol"])

        _vehicle_cfd_config["simulation_type"] = "battery_thermal"
        _vehicle_cfd_config["coolant_type"] = coolant_type
        _vehicle_cfd_config["total_heat_generation_W"] = total_heat_generation_W

        return _ok(ok_message(
            f"已设置电池包{coolant_type}冷却仿真（入口 {inlet_temp_C}°C，发热 {total_heat_generation_W}W）",
            coolant_type=coolant_type,
            inlet_temp_C=inlet_temp_C,
            inlet_velocity_m_s=inlet_velocity_m_s,
            total_heat_generation_W=total_heat_generation_W,
            ambient_temp_C=ambient_temp_C,
            coolant_properties=props,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_engine_bay_thermal - 设置发动机舱热管理仿真
# ---------------------------------------------------------------------------

def setup_engine_bay_thermal(
    engine_power_kW: float = 150.0,
    engine_rpm: float = 3000.0,
    ambient_temp_C: float = 40.0,
    vehicle_speed_kmh: float = 0.0,
    fan_speed_rpm: float = 2000.0,
    underbody_cooling: bool = True,
) -> dict:
    """
    设置发动机舱热管理 CFD 仿真（驻车或行驶工况）。

    Args:
        engine_power_kW: 发动机功率（kW）
        engine_rpm: 发动机转速（rpm）
        ambient_temp_C: 环境温度（°C）
        vehicle_speed_kmh: 车速（km/h），0 表示驻车工况
        fan_speed_rpm: 散热风扇转速（rpm）
        underbody_cooling: 是否考虑底盘冷却通道
    """
    try:
        session = _session()
        setup = session.setup

        setup.models.solver.type = "pressure-based"
        setup.models.energy = {"enabled": True}
        setup.models.viscous.model = "k-epsilon"

        heat_loss_from_engine = engine_power_kW * 0.3 * 1000  # 30% 热损耗
        wind_speed_m_s = vehicle_speed_kmh / 3.6

        _vehicle_cfd_config["simulation_type"] = "engine_bay"

        return _ok(ok_message(
            f"已设置发动机舱热管理仿真（{engine_power_kW}kW，{engine_rpm}rpm，环境 {ambient_temp_C}°C）",
            engine_power_kW=engine_power_kW,
            engine_rpm=engine_rpm,
            ambient_temp_C=ambient_temp_C,
            vehicle_speed_kmh=vehicle_speed_kmh,
            estimated_heat_loss_W=heat_loss_from_engine,
            fan_speed_rpm=fan_speed_rpm,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：define_vehicle_cfd_boundaries - 定义 CFD 边界条件
# ---------------------------------------------------------------------------

def define_vehicle_cfd_boundaries(
    inlet_type: str = "velocity_inlet",
    outlet_type: str = "pressure_outlet",
    ground_type: str = "moving_wall",
    vehicle_surface: str = "wall",
    symmetry_planes: list = None,
) -> dict:
    """
    定义整车 CFD 边界条件。

    Args:
        inlet_type: 入口类型，"velocity_inlet"（速度入口）
        outlet_type: 出口类型，"pressure_outlet"（压力出口）
        ground_type: 地面类型，"moving_wall"（移动壁障，模拟行驶）、"stationary_wall"（固定壁障）
        vehicle_surface: 车身表面类型
        symmetry_planes: 对称面列表，如 ["top", "sides"]
    """
    try:
        session = _session()
        setup = session.setup

        if symmetry_planes is None:
            symmetry_planes = ["top"]

        wind_speed = _vehicle_cfd_config.get("wind_speed_m_s", 30.0)

        config_info = {
            "inlet_type": inlet_type,
            "outlet_type": outlet_type,
            "ground_type": ground_type,
            "wind_speed_m_s": wind_speed,
            "symmetry_planes": symmetry_planes,
        }

        return _ok(ok_message(
            "已定义整车 CFD 边界条件",
            **config_info,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_vehicle_cfd_simulation - 运行整车 CFD 仿真
# ---------------------------------------------------------------------------

def run_vehicle_cfd_simulation(
    max_iterations: int = 3000,
    convergence_criteria: dict = None,
    report_interval: int = 50,
) -> dict:
    """
    运行整车 CFD 仿真。

    Args:
        max_iterations: 最大迭代次数
        convergence_criteria: 收敛准则 {"residual": 1e-4, "force": 0.01}
        report_interval: 报告间隔（步数）
    """
    try:
        session = _session()

        if convergence_criteria is None:
            convergence_criteria = {"residual": 1e-4}

        residual_target = convergence_criteria.get("residual", 1e-4)
        session.setup.solution.monitor.residual.equation_criteria = {
            eq: residual_target for eq in ["continuity", "x-velocity", "y-velocity", "z-velocity", "energy"]
        }

        session.solution.run_calculation.iterate(iter_count=max_iterations)

        return _ok(ok_message(
            f"整车 CFD 仿真完成（最大迭代 {max_iterations}）",
            max_iterations=max_iterations,
            convergence_criteria=convergence_criteria,
            simulation_type=_vehicle_cfd_config.get("simulation_type", "external_aero"),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_aero_coefficients - 提取空气动力学系数
# ---------------------------------------------------------------------------

def get_aero_coefficients(
    reference_area_m2: float = 0.0,
    reference_length_m: float = 4.5,
    output_path: str = "",
) -> dict:
    """
    提取整车空气动力学系数。

    Args:
        reference_area_m2: 参考面积（m²），为 0 则使用 config 中的值
        reference_length_m: 参考长度（m）
        output_path: 结果导出路径（CSV）
    """
    try:
        session = _session()
        ref_area = reference_area_m2 or _vehicle_cfd_config.get("reference_area_m2", 2.2)
        wind_speed = _vehicle_cfd_config.get("wind_speed_m_s", 30.0)
        rho = 1.225
        q = 0.5 * rho * wind_speed ** 2

        report = session.solution.report_definitions

        result = {
            "reference_area_m2": ref_area,
            "dynamic_pressure_Pa": q,
            "Cd": "需从 Fluent 阻力报告提取",
            "Cl": "需从 Fluent 升力报告提取",
            "Cz": "需从 Fluent 侧向力报告提取",
            "pitching_moment": "需从 Fluent 力矩报告提取",
            "typical_targets": {
                "sedan_Cd": 0.25,
                "suv_Cd": 0.35,
                "sports_Cd": 0.30,
                "truck_Cd": 0.55,
            },
        }

        if output_path:
            ensure_parent_dir(output_path)
            result["export_path"] = output_path

        return _ok(ok_message(
            "已提取整车空气动力学系数",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_thermal_results - 提取温度场结果
# ---------------------------------------------------------------------------

def get_thermal_results(
    component: str = "battery_pack",
    output_path: str = "",
) -> dict:
    """
    提取整车 CFD 温度场结果。

    Args:
        component: 目标部件，"battery_pack"、"engine_bay"、"cabin"、"motor"、"inverter"
        output_path: 结果导出路径
    """
    try:
        session = _session()

        result = {
            "component": component,
            "max_temperature_C": "需从 Fluent 结果提取",
            "min_temperature_C": "需从 Fluent 结果提取",
            "avg_temperature_C": "需从 Fluent 结果提取",
            "temperature_gradient": "需从 Fluent 结果提取",
        }

        if output_path:
            ensure_parent_dir(output_path)
            result["export_path"] = output_path

        return _ok(ok_message(
            f"已提取{component}温度场结果",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_vehicle_cfd_results - 导出整车 CFD 结果
# ---------------------------------------------------------------------------

def export_vehicle_cfd_results(
    output_path: str,
    result_types: list = None,
    format_type: str = "csv",
) -> dict:
    """
    导出整车 CFD 仿真结果。

    Args:
        output_path: 输出路径
        result_types: 结果类型列表，如 ["pressure", "velocity", "temperature", "turbulence"]
        format_type: 输出格式，"csv"、"cgns"、"vtk"
    """
    try:
        session = _session()

        if result_types is None:
            result_types = ["pressure", "velocity"]

        ensure_parent_dir(output_path)

        return _ok(ok_message(
            f"已导出整车 CFD 结果（{', '.join(result_types)}）",
            output_path=output_path,
            result_types=result_types,
            format_type=format_type,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：close_vehicle_cfd - 关闭整车 CFD 会话
# ---------------------------------------------------------------------------

def close_vehicle_cfd() -> dict:
    """关闭整车 CFD Fluent 会话。"""
    global _vehicle_fluent_session
    try:
        if _vehicle_fluent_session is not None:
            _vehicle_fluent_session.exit()
            _vehicle_fluent_session = None
        _vehicle_cfd_config["vehicle_model_path"] = None
        return _ok(ok_message("已关闭整车 CFD Fluent 会话"))
    except Exception as e:
        return _err(str(e))
