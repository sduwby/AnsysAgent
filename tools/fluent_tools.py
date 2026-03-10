"""
Fluent 流体分析工具：通过 ansys-fluent-core（PyFluent）驱动 Ansys Fluent 进行 CFD 仿真。
涵盖完整工作流：网格读取、物理模型配置、边界条件、求解器设置、求解计算及结果提取。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
from typing import Any

from tools.utils import _ok, _err

_fluent_session = None  # 全局 Fluent 会话实例


def _session():
    if _fluent_session is None:
        raise RuntimeError("未连接到 Fluent，请先调用 connect_fluent。")
    return _fluent_session


# ---------------------------------------------------------------------------
# 工具：connect_fluent - 启动/连接 Fluent
# ---------------------------------------------------------------------------

def connect_fluent(
    version: str = "23.2",
    precision: str = "double",
    processors: int = 4,
    mode: str = "solver",
) -> dict:
    """
    启动 Ansys Fluent 会话（通过 ansys-fluent-core）。

    Args:
        version: Fluent 版本号，如 "23.2"（2023 R2）、"24.1"（2024 R1）
        precision: 精度，"double"（双精度，推荐）或 "single"
        processors: 并行进程数（CPU 核心数）
        mode: 运行模式，"solver"（求解器）或 "meshing"（网格划分）
    """
    global _fluent_session
    try:
        import ansys.fluent.core as pyfluent

        _fluent_session = pyfluent.launch_fluent(
            product_version=version,
            precision=precision,
            processor_count=processors,
            mode=mode,
            ui_mode="no_gui",  # 服务器模式，无 GUI
        )
        return _ok(f"已启动 Fluent {version}（{precision} 精度，{processors} 进程）")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：read_fluent_mesh - 读取网格/Case 文件
# ---------------------------------------------------------------------------

def read_fluent_mesh(mesh_file_path: str) -> dict:
    """
    读取网格或 Case 文件到 Fluent。

    Args:
        mesh_file_path: 网格文件路径（支持 .msh、.msh.gz、.cas、.cas.gz）
    """
    try:
        session = _session()
        ext = os.path.splitext(mesh_file_path.rstrip(".gz"))[-1].lower()

        if ext in (".cas",):
            session.file.read_case(file_name=mesh_file_path)
            return _ok(f"已读取 Case 文件: {mesh_file_path}")
        else:
            session.file.read_mesh(file_name=mesh_file_path)
            return _ok(f"已读取网格文件: {mesh_file_path}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_fluid_models - 配置流体物理模型
# ---------------------------------------------------------------------------

def setup_fluid_models(
    viscous_model: str = "k-epsilon",
    k_epsilon_variant: str = "realizable",
    energy_on: bool = False,
    turbulence_intensity: float = 0.05,
    turbulent_length_scale: float | None = None,
) -> dict:
    """
    配置 Fluent 流体物理模型（湍流模型、能量方程）。

    Args:
        viscous_model: 湍流模型，可选：
            "laminar"（层流）、"k-epsilon"（k-ε）、"k-omega"（k-ω）、
            "sst"（k-ω SST）、"realizable-ke"（Realizable k-ε）、
            "rng-ke"（RNG k-ε）
        k_epsilon_variant: k-epsilon 子模型，"standard"、"rng" 或 "realizable"
        energy_on: 是否开启能量方程（温度计算）
        turbulence_intensity: 湍流强度（入射边界参考值），默认 5%
        turbulent_length_scale: 湍流长度尺度（m），None 则自动估算
    """
    try:
        session = _session()
        setup = session.setup

        # 配置湍流模型
        viscous = setup.models.viscous
        if viscous_model == "laminar":
            viscous.model = "laminar"
        elif viscous_model in ("k-epsilon", "realizable-ke", "rng-ke"):
            viscous.model = "k-epsilon"
            variant_map = {
                "standard": "standard",
                "rng": "rng",
                "realizable": "realizable",
            }
            viscous.k_epsilon_model = variant_map.get(k_epsilon_variant, "realizable")
        elif viscous_model in ("k-omega", "sst"):
            viscous.model = "k-omega"
            viscous.k_omega_model = "sst" if viscous_model == "sst" else "standard"
        else:
            viscous.model = viscous_model

        # 配置能量方程
        if energy_on:
            setup.models.energy.enabled = True

        return _ok(
            f"物理模型已配置：湍流={viscous_model}，"
            f"能量方程={'开启' if energy_on else '关闭'}，"
            f"湍流强度={turbulence_intensity * 100:.1f}%"
        )
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：define_boundary_conditions - 设置边界条件
# ---------------------------------------------------------------------------

def define_boundary_conditions(
    boundary_name: str,
    bc_type: str,
    velocity_magnitude: float | None = None,
    pressure_value: float | None = None,
    temperature: float | None = None,
    turbulence_intensity: float = 0.05,
    hydraulic_diameter: float | None = None,
) -> dict:
    """
    设定指定边界的边界条件。

    Args:
        boundary_name: 边界名称（与网格中定义一致，如 "inlet"、"outlet"、"wall"）
        bc_type: 边界类型，"velocity-inlet"、"pressure-inlet"、"pressure-outlet"、
                 "wall"、"symmetry"、"periodic"
        velocity_magnitude: 速度大小（m/s），velocity-inlet 必填
        pressure_value: 压力值（Pa），pressure-inlet/pressure-outlet 使用
        temperature: 温度（K），开启能量方程时使用
        turbulence_intensity: 湍流强度（0~1），默认 0.05（5%）
        hydraulic_diameter: 水力直径（m），用于湍流长度尺度估算
    """
    try:
        session = _session()
        bcs = session.setup.boundary_conditions

        if bc_type == "velocity-inlet":
            bc = bcs.velocity_inlet[boundary_name]
            if velocity_magnitude is not None:
                bc.momentum.velocity.value = velocity_magnitude
            bc.turbulence.turbulent_intensity = turbulence_intensity
            if hydraulic_diameter is not None:
                bc.turbulence.hydraulic_diameter = hydraulic_diameter
            if temperature is not None:
                bc.thermal.temperature.value = temperature

        elif bc_type in ("pressure-inlet", "pressure-outlet"):
            if bc_type == "pressure-inlet":
                bc = bcs.pressure_inlet[boundary_name]
            else:
                bc = bcs.pressure_outlet[boundary_name]
            if pressure_value is not None:
                bc.momentum.gauge_pressure.value = pressure_value
            if temperature is not None:
                bc.thermal.temperature.value = temperature

        elif bc_type == "wall":
            bc = bcs.wall[boundary_name]
            if temperature is not None:
                bc.thermal.thermal_conditions = "temperature"
                bc.thermal.temperature.value = temperature

        info_parts = [f"边界={boundary_name}，类型={bc_type}"]
        if velocity_magnitude is not None:
            info_parts.append(f"速度={velocity_magnitude} m/s")
        if pressure_value is not None:
            info_parts.append(f"压力={pressure_value} Pa")
        if temperature is not None:
            info_parts.append(f"温度={temperature} K")

        return _ok("，".join(info_parts))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_fluent_solver - 配置求解器
# ---------------------------------------------------------------------------

def setup_fluent_solver(
    scheme: str = "coupled",
    convergence_absolute: float = 1e-4,
    max_iterations: int = 500,
    under_relaxation_velocity: float = 0.7,
    under_relaxation_pressure: float = 0.3,
) -> dict:
    """
    配置 Fluent 求解算法和收敛参数。

    Args:
        scheme: 求解算法，"coupled"（耦合求解，推荐）或 "simple"（分离求解）
        convergence_absolute: 收敛绝对残差标准（所有方程），默认 1e-4
        max_iterations: 最大迭代步数
        under_relaxation_velocity: 速度亚松弛因子（SIMPLE 算法用）
        under_relaxation_pressure: 压力亚松弛因子（SIMPLE 算法用）
    """
    try:
        session = _session()
        methods = session.solution.methods

        if scheme == "coupled":
            methods.p_v_coupling.flow_scheme = "Coupled"
        else:
            methods.p_v_coupling.flow_scheme = "SIMPLE"
            controls = session.solution.controls
            controls.under_relaxation["mom"] = under_relaxation_velocity
            controls.under_relaxation["pressure"] = under_relaxation_pressure

        # 设置收敛标准
        monitors = session.solution.monitor
        residuals = monitors.residuals
        for eq in ["continuity", "x-velocity", "y-velocity", "z-velocity"]:
            try:
                residuals.equations[eq].absolute_criteria = convergence_absolute
            except Exception:
                pass

        return _ok(
            f"求解器已配置：算法={scheme}，收敛标准={convergence_absolute}，"
            f"最大迭代={max_iterations}"
        )
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：initialize_fluent - 初始化流场
# ---------------------------------------------------------------------------

def initialize_fluent(
    method: str = "hybrid",
    reference_velocity: float | None = None,
    reference_pressure: float | None = None,
) -> dict:
    """
    初始化 Fluent 流场。

    Args:
        method: 初始化方法，"hybrid"（混合初始化，推荐）或 "standard"（标准初始化）
        reference_velocity: 参考速度（m/s），standard 初始化用
        reference_pressure: 参考压力（Pa），standard 初始化用
    """
    try:
        session = _session()
        initialization = session.solution.initialization

        if method == "hybrid":
            initialization.hybrid_initialize()
        else:
            if reference_velocity is not None:
                initialization.initial_values["velocity"] = reference_velocity
            if reference_pressure is not None:
                initialization.initial_values["gauge-pressure"] = reference_pressure
            initialization.initialize()

        return _ok(f"流场初始化完成（方法={method}）")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_fluent_simulation - 执行迭代计算
# ---------------------------------------------------------------------------

def run_fluent_simulation(
    iterations: int = 300,
    report_interval: int = 10,
) -> dict:
    """
    执行 Fluent 稳态迭代计算。

    Args:
        iterations: 最大迭代步数
        report_interval: 每隔多少步输出一次残差报告
    """
    try:
        session = _session()
        run_calc = session.solution.run_calculation
        run_calc.iter_count = iterations
        run_calc.iterate(iter_count=iterations)

        return _ok(f"流体仿真计算完成（迭代 {iterations} 步）")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_fluent_results - 提取流体仿真结果
# ---------------------------------------------------------------------------

def get_fluent_results(
    surfaces: list[str] | None = None,
    quantities: list[str] | None = None,
) -> dict:
    """
    提取指定边界面的流场结果（面积加权平均值）。

    Args:
        surfaces: 要提取结果的面名称列表，如 ["inlet", "outlet"]；
                  None 则尝试提取 inlet 和 outlet
        quantities: 要提取的物理量，如 ["pressure", "velocity-magnitude",
                    "temperature", "wall-shear-stress"]；
                    None 则默认提取压力和速度
    """
    try:
        session = _session()

        if surfaces is None:
            surfaces = ["inlet", "outlet"]
        if quantities is None:
            quantities = ["pressure", "velocity-magnitude"]

        results = {}
        for surface in surfaces:
            results[surface] = {}
            for qty in quantities:
                try:
                    value = session.fields.reduction.area_average(
                        expression=qty,
                        locations=[surface],
                    )
                    results[surface][qty] = round(float(value), 6) if value is not None else None
                except Exception as e:
                    results[surface][qty] = f"提取失败: {str(e)}"

        # 计算压降（若 inlet 和 outlet 均有压力数据）
        try:
            p_in = results.get("inlet", {}).get("pressure")
            p_out = results.get("outlet", {}).get("pressure")
            if isinstance(p_in, (int, float)) and isinstance(p_out, (int, float)):
                results["pressure_drop_Pa"] = round(p_in - p_out, 4)
        except Exception:
            pass

        return _ok(results)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_fluent_data - 导出结果数据
# ---------------------------------------------------------------------------

def export_fluent_data(
    output_path: str,
    surfaces: list[str] | None = None,
    quantities: list[str] | None = None,
    export_format: str = "csv",
) -> dict:
    """
    将 Fluent 仿真结果导出为文件。

    Args:
        output_path: 输出文件路径（不含扩展名时自动追加）
        surfaces: 要导出数据的边界面列表；None 则导出所有面
        quantities: 要导出的物理量列表；None 则导出全部可用量
        export_format: 导出格式，"csv"（表格）或 "case-data"（保存 Case+Data 文件）
    """
    try:
        session = _session()

        if export_format == "case-data":
            # 保存 Case+Data 文件（.cas.gz + .dat.gz）
            if not output_path.endswith(".cas"):
                output_path = output_path + ".cas"
            session.file.write_case_data(file_name=output_path)
            return _ok(f"Case+Data 文件已保存至: {output_path[:-4]}.cas.gz/.dat.gz")

        # CSV 导出：通过 report 导出面数据
        if not output_path.endswith(".csv"):
            output_path = output_path + ".csv"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if surfaces is None:
            surfaces = ["inlet", "outlet"]
        if quantities is None:
            quantities = ["pressure", "velocity-magnitude", "wall-shear-stress"]

        # 写入 CSV（手动汇总面平均值）
        import csv
        rows = []
        for surface in surfaces:
            row = {"surface": surface}
            for qty in quantities:
                try:
                    val = session.fields.reduction.area_average(
                        expression=qty,
                        locations=[surface],
                    )
                    row[qty] = round(float(val), 6) if val is not None else ""
                except Exception:
                    row[qty] = ""
            rows.append(row)

        if rows:
            fieldnames = ["surface"] + quantities
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

        return _ok(f"结果已导出至: {output_path}（{len(rows)} 个面，{len(quantities)} 个物理量）")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_fluid_material - 配置流体物性参数
# ---------------------------------------------------------------------------

def setup_fluid_material(
    material_name: str = "air",
    density: float | None = None,
    viscosity: float | None = None,
    thermal_conductivity: float | None = None,
    specific_heat: float | None = None,
    density_model: str = "constant",
) -> dict:
    """
    配置 Fluent 流体域的物性参数（密度、动力黏度、导热系数、比热容）。

    Args:
        material_name: 材料名称，默认 "air"；可使用 "water-liquid"、"water-vapor" 等
                       Fluent 内置材料，或自定义名称
        density: 密度（kg/m³），None 则保持当前值
        viscosity: 动力黏度（Pa·s），None 则保持当前值
        thermal_conductivity: 导热系数（W/(m·K)），None 则保持当前值；
                              开启能量方程时生效
        specific_heat: 比热容（J/(kg·K)），None 则保持当前值；
                       开启能量方程时生效
        density_model: 密度模型，"constant"（常数）、"ideal-gas"（理想气体，
                       需开启能量方程）、"boussinesq"（Boussinesq 近似，自然对流用）
    """
    try:
        session = _session()
        materials = session.setup.materials.fluid

        # 获取或创建材料
        if material_name not in materials:
            materials.create(material_name)
        mat = materials[material_name]

        # 密度模型
        if density_model == "ideal-gas":
            mat.density.option = "ideal-gas"
        elif density_model == "boussinesq":
            mat.density.option = "boussinesq"
            if density is not None:
                mat.density.value = density
        else:
            mat.density.option = "constant"
            if density is not None:
                mat.density.value = density

        # 动力黏度
        if viscosity is not None:
            mat.viscosity.option = "constant"
            mat.viscosity.value = viscosity

        # 导热系数
        if thermal_conductivity is not None:
            mat.thermal_conductivity.option = "constant"
            mat.thermal_conductivity.value = thermal_conductivity

        # 比热容
        if specific_heat is not None:
            mat.specific_heat.option = "constant"
            mat.specific_heat.value = specific_heat

        info_parts = [f"材料={material_name}，密度模型={density_model}"]
        if density is not None:
            info_parts.append(f"密度={density} kg/m³")
        if viscosity is not None:
            info_parts.append(f"黏度={viscosity} Pa·s")
        if thermal_conductivity is not None:
            info_parts.append(f"导热系数={thermal_conductivity} W/(m·K)")
        if specific_heat is not None:
            info_parts.append(f"比热容={specific_heat} J/(kg·K)")

        return _ok("，".join(info_parts))
    except Exception as e:
        return _err(str(e))
