"""
Fluent 流体分析工具：通过 ansys-fluent-core（PyFluent）驱动 Ansys Fluent 进行 CFD 仿真。
涵盖完整工作流：网格读取、物理模型配置、边界条件、求解器设置、求解计算及结果提取。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
from typing import Any

from tools.utils import _ok, _err, ensure_parent_dir, ok_message, append_warnings

_fluent_session = None  # 全局 Fluent 会话实例
_fluent_runtime_config = {
    "turbulence_intensity": 0.05,
    "turbulent_length_scale": None,
    "max_iterations": 500,
}


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
        return _ok(ok_message(
            f"已启动 Fluent {version}（{precision} 精度，{processors} 进程）",
            version=version,
            precision=precision,
            processors=processors,
            mode=mode,
        ))
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
            return _ok(ok_message(f"已读取 Case 文件: {mesh_file_path}", mesh_file_path=mesh_file_path, file_type="case"))
        else:
            session.file.read_mesh(file_name=mesh_file_path)
            return _ok(ok_message(f"已读取网格文件: {mesh_file_path}", mesh_file_path=mesh_file_path, file_type="mesh"))
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
        warnings: list[str] = []

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

        # 记录默认湍流参数，供后续边界条件配置复用
        _fluent_runtime_config["turbulence_intensity"] = turbulence_intensity
        _fluent_runtime_config["turbulent_length_scale"] = turbulent_length_scale

        # 尝试写入可用的全局湍流长度尺度接口（不同版本 API 字段可能不同）
        if turbulent_length_scale is not None:
            applied = False
            for attr_name in ("turbulent_length_scale", "length_scale"):
                if hasattr(viscous, attr_name):
                    try:
                        setattr(viscous, attr_name, turbulent_length_scale)
                        applied = True
                        break
                    except Exception as e:
                        warnings.append(f"{attr_name} 写入失败: {e}")
            if not applied:
                warnings.append("当前 Fluent API 未暴露全局湍流长度尺度字段，已仅保存为后续边界条件默认值")

        return _ok(append_warnings(ok_message(
            f"物理模型已配置：湍流={viscous_model}，"
            f"能量方程={'开启' if energy_on else '关闭'}，"
            f"湍流强度={turbulence_intensity * 100:.1f}%",
            viscous_model=viscous_model,
            energy_on=energy_on,
            turbulence_intensity=turbulence_intensity,
            turbulent_length_scale=turbulent_length_scale,
        ), warnings))
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
    turbulence_intensity: float | None = None,
    hydraulic_diameter: float | None = None,
) -> dict:
    """
    设定指定边界的边界条件。

    Args:
        boundary_name: 边界名称（与网格中定义一致，如 "inlet"、"outlet"、"wall"）
        bc_type: 边界类型，"velocity-inlet"、"pressure-inlet"、"pressure-outlet"、"wall"
        velocity_magnitude: 速度大小（m/s），velocity-inlet 必填
        pressure_value: 压力值（Pa），pressure-inlet/pressure-outlet 使用
        temperature: 温度（K），开启能量方程时使用
        turbulence_intensity: 湍流强度（0~1），默认 0.05（5%）
        hydraulic_diameter: 水力直径（m），用于湍流长度尺度估算
    """
    try:
        session = _session()
        bcs = session.setup.boundary_conditions
        supported_bc_types = {"velocity-inlet", "pressure-inlet", "pressure-outlet", "wall"}
        effective_turbulence_intensity = (
            turbulence_intensity
            if turbulence_intensity is not None
            else _fluent_runtime_config.get("turbulence_intensity", 0.05)
        )

        if bc_type not in supported_bc_types:
            return _err(
                f"当前工具仅支持 {sorted(supported_bc_types)}，"
                f"不支持 '{bc_type}' 的自动配置"
            )

        if bc_type == "velocity-inlet":
            if velocity_magnitude is None:
                return _err("velocity-inlet 必须提供 velocity_magnitude")
            bc = bcs.velocity_inlet[boundary_name]
            if velocity_magnitude is not None:
                bc.momentum.velocity.value = velocity_magnitude
            bc.turbulence.turbulent_intensity = effective_turbulence_intensity
            if hydraulic_diameter is not None:
                bc.turbulence.hydraulic_diameter = hydraulic_diameter
            elif _fluent_runtime_config.get("turbulent_length_scale") is not None:
                # 若调用方未传水力直径，尝试使用 setup_fluid_models 记录的长度尺度默认值
                for attr_name in ("turbulent_length_scale", "length_scale"):
                    if hasattr(bc.turbulence, attr_name):
                        setattr(bc.turbulence, attr_name, _fluent_runtime_config["turbulent_length_scale"])
                        break
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

        return _ok(ok_message("，".join(info_parts), boundary_name=boundary_name, bc_type=bc_type))
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

        # 保存并尽量下发默认迭代步，便于后续 run_fluent_simulation 复用
        _fluent_runtime_config["max_iterations"] = max_iterations
        run_calc = getattr(session.solution, "run_calculation", None)
        if run_calc is not None and hasattr(run_calc, "iter_count"):
            run_calc.iter_count = max_iterations

        return _ok(ok_message(
            f"求解器已配置：算法={scheme}，收敛标准={convergence_absolute}，"
            f"最大迭代={max_iterations}",
            scheme=scheme,
            convergence_absolute=convergence_absolute,
            max_iterations=max_iterations,
        ))
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

        return _ok(ok_message(f"流场初始化完成（方法={method}）", method=method))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_fluent_simulation - 执行迭代计算
# ---------------------------------------------------------------------------

def run_fluent_simulation(
    iterations: int | None = 300,
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
        warnings: list[str] = []
        effective_iterations = (
            iterations
            if iterations is not None
            else int(_fluent_runtime_config.get("max_iterations", 300))
        )
        run_calc.iter_count = effective_iterations

        interval_applied = False
        for attr_name in ("report_interval", "residual_report_interval"):
            if hasattr(run_calc, attr_name):
                setattr(run_calc, attr_name, report_interval)
                interval_applied = True
                break
        if not interval_applied:
            warnings.append("当前 Fluent API 未暴露 report_interval 字段，已忽略该参数")

        run_calc.iterate(iter_count=effective_iterations)

        return _ok(append_warnings(
            ok_message(
                f"流体仿真计算完成（迭代 {effective_iterations} 步）",
                iterations=effective_iterations,
                report_interval=report_interval,
            ),
            warnings,
        ))
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
            return _ok(ok_message(
                f"Case+Data 文件已保存至: {output_path[:-4]}.cas.gz/.dat.gz",
                output_path=output_path,
                export_format=export_format,
            ))

        # CSV 导出：通过 report 导出面数据
        if not output_path.endswith(".csv"):
            output_path = output_path + ".csv"

        ensure_parent_dir(output_path)

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

        return _ok(ok_message(
            f"结果已导出至: {output_path}（{len(rows)} 个面，{len(quantities)} 个物理量）",
            output_path=output_path,
            surfaces=surfaces,
            quantities=quantities,
            export_format=export_format,
        ))
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
                       会自动开启能量方程）、"boussinesq"（Boussinesq 近似，自然对流用）
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
            # ideal-gas 依赖能量方程，自动开启
            session.setup.models.energy.enabled = True
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

        return _ok(ok_message("，".join(info_parts), material_name=material_name, density_model=density_model))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：launch_fluent_meshing - 启动 Fluent Meshing 模式（网格划分）
# ---------------------------------------------------------------------------

def launch_fluent_meshing(
    precision: str = "double",
    processors: int = 4,
    cwd: str | None = None,
) -> dict:
    """
    启动 Fluent Meshing 模式，用于 Watertight Geometry 或 Fault-tolerant 工作流网格划分。
    与 connect_fluent（solver 模式）互相独立，网格完成后应调用 close_fluent_meshing。

    参考工作流：geometry-mesh-fluent/wf_gmf_02_fluent_meshing.py

    Args:
        precision: "double"（推荐）或 "single"
        processors: 并行进程数
        cwd: 工作目录，网格文件将写入此目录；None 则使用当前目录
    """
    global _fluent_session
    try:
        import ansys.fluent.core as pyfluent

        launch_kwargs: dict = dict(
            precision=precision,
            processor_count=processors,
            mode="meshing",
            ui_mode="no_gui_or_graphics",
        )
        if cwd is not None:
            launch_kwargs["cwd"] = cwd

        _fluent_session = pyfluent.launch_fluent(**launch_kwargs)
        return _ok(ok_message(
            f"已启动 Fluent Meshing（{precision} 精度，{processors} 进程）",
            precision=precision,
            processors=processors,
            mode="meshing",
            cwd=cwd,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_watertight_meshing_workflow - Watertight Geometry 网格工作流
# ---------------------------------------------------------------------------

def run_watertight_meshing_workflow(
    geometry_file: str,
    output_mesh_file: str,
    surface_min_size: float = 2.0,
    surface_max_size: float = 1000.0,
    volume_fill_type: str = "poly-hexcore",
    num_boundary_layers: int = 12,
    hex_max_cell_length: float = 512.0,
) -> dict:
    """
    在 Fluent Meshing 模式下执行完整的 Watertight Geometry 网格工作流：
    导入几何 → 生成曲面网格 → 描述几何 → 更新边界/区域 → 添加边界层 → 生成体网格 → 写出网格。

    参考工作流：geometry-mesh-fluent/wf_gmf_02_fluent_meshing.py

    Args:
        geometry_file: 几何文件路径（PMDB、FMD 等）
        output_mesh_file: 输出网格文件路径（.msh.h5）
        surface_min_size: 曲面网格最小尺寸
        surface_max_size: 曲面网格最大尺寸
        volume_fill_type: 体网格填充类型，"poly-hexcore"（推荐）或 "tetrahedral"
        num_boundary_layers: 边界层层数
        hex_max_cell_length: poly-hexcore 最大六面体单元尺寸
    """
    try:
        session = _session()
        wf = session.workflow

        # 初始化 Watertight Geometry 工作流
        wf.InitializeWorkflow(WorkflowType="Watertight Geometry")

        # 导入几何
        geo_import = wf.TaskObject["Import Geometry"]
        geo_import.Arguments.set_state({"FileName": geometry_file})
        geo_import.Execute()

        # 生成曲面网格
        surface_mesh_gen = wf.TaskObject["Generate the Surface Mesh"]
        surface_mesh_gen.Arguments.set_state({
            "CFDSurfaceMeshControls": {
                "MinSize": surface_min_size,
                "MaxSize": surface_max_size,
            }
        })
        surface_mesh_gen.Execute()

        # 描述几何（流体域，无空洞）
        describe_geo = wf.TaskObject["Describe Geometry"]
        describe_geo.UpdateChildTasks(SetupTypeChanged=False)
        describe_geo.Arguments.set_state({
            "SetupType": "The geometry consists of only fluid regions with no voids"
        })
        describe_geo.UpdateChildTasks(SetupTypeChanged=True)
        describe_geo.Execute()

        # 更新边界和区域
        wf.TaskObject["Update Boundaries"].Execute()
        wf.TaskObject["Update Regions"].Execute()

        # 添加边界层
        add_bl = wf.TaskObject["Add Boundary Layers"]
        add_bl.Arguments.set_state({"NumberOfLayers": num_boundary_layers})
        add_bl.AddChildAndUpdate()

        # 生成体网格
        vol_mesh_gen = wf.TaskObject["Generate the Volume Mesh"]
        vol_mesh_gen.Arguments.set_state({
            "VolumeFill": volume_fill_type,
            "VolumeFillControls": {"HexMaxCellLength": hex_max_cell_length},
            "VolumeMeshPreferences": {
                "CheckSelfProximity": "yes",
                "ShowVolumeMeshPreferences": True,
            },
        })
        vol_mesh_gen.Execute()

        # 检查并写出网格
        session.tui.mesh.check_mesh()
        session.tui.file.write_mesh(output_mesh_file)

        return _ok(ok_message(
            f"Watertight 网格工作流完成，网格已写入：{output_mesh_file}",
            geometry_file=geometry_file,
            output_mesh_file=output_mesh_file,
            volume_fill_type=volume_fill_type,
            num_boundary_layers=num_boundary_layers,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_named_expression - 创建 Fluent 命名表达式
# ---------------------------------------------------------------------------

def create_named_expression(
    name: str,
    definition: str,
    is_input_parameter: bool = False,
) -> dict:
    """
    在 Fluent 中创建命名表达式（Named Expression），可在边界条件中引用。
    适用于参数化仿真（如 CHT 多工况排气歧管分析）。

    参考工作流：fluent-mechanical/wf_fm_01_fluent.py

    Args:
        name: 表达式名称（英文，无空格）
        definition: 表达式定义字符串，例如 "1023.15 [K]" 或
                    "abs((0.1559 [kg/s] *log(in_temperature/(1 [K^1])))-0.9759 [kg/s])"
        is_input_parameter: True 则将此表达式标记为输入参数（可在参数研究中扫描）
    """
    try:
        session = _session()
        named_exprs = session.settings.setup.named_expressions

        # 创建并定义表达式
        named_exprs.create(name)
        named_exprs[name].definition = definition
        if is_input_parameter:
            named_exprs[name].input_parameter = True

        return _ok(ok_message(
            f"已创建命名表达式 '{name}' = {definition[:80]}{'…' if len(definition) > 80 else ''}",
            name=name,
            definition=definition,
            is_input_parameter=is_input_parameter,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：assign_cell_zone_material - 为流体/固体区域指定材料（版本自适应）
# ---------------------------------------------------------------------------

def assign_cell_zone_material(
    zone_name: str,
    material_name: str,
    zone_type: str = "fluid",
) -> dict:
    """
    为 Fluent 中的流体或固体 Cell Zone 指定材料，
    自动适配 Fluent 2024 R2 及之前/之后的 API 变化。

    参考工作流：fluent-mechanical/wf_fm_01_fluent.py

    Args:
        zone_name: Cell Zone 名称，支持通配符（如 "*fluid*"）
        material_name: 材料名称（已在 Fluent 材料库中存在）
        zone_type: "fluid" 或 "solid"
    """
    try:
        import ansys.fluent.core as pyfluent
        session = _session()
        czc = session.settings.setup.cell_zone_conditions
        fluent_ver = session.get_fluent_version()
        v242 = pyfluent.FluentVersion.v242

        if zone_type == "fluid":
            zone_obj = czc.fluid[zone_name]
            if fluent_ver < v242:
                zone_obj.material = material_name
            else:
                zone_obj.general.material = material_name
        elif zone_type == "solid":
            zone_obj = czc.solid[zone_name]
            if fluent_ver < v242:
                zone_obj.material = material_name
            else:
                zone_obj.general.material = material_name
        else:
            return _err(f"zone_type 仅支持 'fluid' 或 'solid'，收到：{zone_type}")

        return _ok(ok_message(
            f"已为 {zone_type} 区域 '{zone_name}' 指定材料 '{material_name}'",
            zone_name=zone_name,
            material_name=material_name,
            zone_type=zone_type,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：update_named_expression - 更新命名表达式值（多工况参数化）
# ---------------------------------------------------------------------------

def update_named_expression(name: str, new_definition: str) -> dict:
    """
    更新已有命名表达式的定义值，用于多工况参数化仿真循环。

    参考工作流：fluent-mechanical/wf_fm_01_fluent.py（温度多工况循环）

    Args:
        name: 已存在的表达式名称
        new_definition: 新的表达式定义字符串，例如 "683.15 [K]"
    """
    try:
        session = _session()
        session.settings.setup.named_expressions[name].definition = new_definition
        return _ok(ok_message(
            f"已将表达式 '{name}' 更新为：{new_definition}",
            name=name,
            new_definition=new_definition,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_surface_data_ascii - 导出边界面数据到 CSV（CHT 工作流）
# ---------------------------------------------------------------------------

def export_surface_data_ascii(
    output_file: str,
    surface_names: list[str],
    quantities: list[str] | None = None,
    location: str = "node",
    delimiter: str = "comma",
) -> dict:
    """
    将指定边界面的仿真数据导出为 ASCII/CSV 文件，供 Mechanical 热力耦合映射使用。
    适用于 CHT 工作流：导出 HTC（对流换热系数）和温度到 Mechanical。

    参考工作流：fluent-mechanical/wf_fm_01_fluent.py（export_ascii）

    Args:
        output_file: 输出文件名（含扩展名，如 "htc_temp_mapping.csv"）
        surface_names: 要导出的边界面名称列表（如 ["interface_solid"]）
        quantities: 要导出的物理量列表；
                    None 则默认导出 ["temperature", "heat-transfer-coef-wall"]
        location: 数据位置，"node"（节点）或 "cell"（单元中心）
        delimiter: 分隔符，"comma"（逗号）或 "tab"（制表符）
    """
    try:
        session = _session()
        if quantities is None:
            quantities = ["temperature", "heat-transfer-coef-wall"]

        session.settings.file.export.ascii(
            file_name=output_file,
            surface_name_list=surface_names,
            delimiter=delimiter,
            cell_func_domain=quantities,
            location=location,
        )

        return _ok(ok_message(
            f"边界面数据已导出至：{output_file}（面={surface_names}，量={quantities}）",
            output_file=output_file,
            surface_names=surface_names,
            quantities=quantities,
            location=location,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_multi_condition_simulation - 多工况批量仿真
# ---------------------------------------------------------------------------

def run_multi_condition_simulation(
    parameter_name: str,
    condition_list: list[dict],
    output_dir: str = ".",
    iterations_per_case: int = 200,
) -> dict:
    """
    批量运行多个工况的 Fluent 仿真，每个工况更新一个命名表达式参数后迭代求解，
    并将结果文件保存至指定目录。

    参考工作流：fluent-mechanical/wf_fm_01_fluent.py（temperature_values 多工况循环）

    Args:
        parameter_name: 要在各工况中更新的命名表达式名称（如 "in_temperature"）
        condition_list: 工况列表，每项为 {"label": str, "value": str} 格式，
                        例如 [{"label": "HIGH_TEMP", "value": "1023.15 [K]"}, ...]
        output_dir: 结果文件保存目录
        iterations_per_case: 每个工况的迭代步数
    """
    try:
        import os
        from tools.utils import ensure_parent_dir
        session = _session()
        results = []

        for cond in condition_list:
            label = cond["label"]
            value = cond["value"]

            # 更新参数
            session.settings.setup.named_expressions[parameter_name].definition = value

            # 混合初始化 + 迭代
            session.solution.initialization.hybrid_initialize()
            session.solution.run_calculation.iterate(iter_count=iterations_per_case)

            # 保存 Case+Data
            case_name = os.path.join(output_dir, f"results_{label}.cas.h5")
            ensure_parent_dir(case_name)
            session.settings.file.write_case_data(file_name=case_name)

            results.append({
                "label": label,
                "parameter_value": value,
                "case_file": case_name,
                "iterations": iterations_per_case,
            })

        return _ok(ok_message(
            f"多工况仿真完成：{len(results)} 个工况，参数='{parameter_name}'",
            parameter_name=parameter_name,
            conditions=results,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：close_fluent - 退出 Fluent 会话
# ---------------------------------------------------------------------------

def close_fluent() -> dict:
    """
    退出当前 Fluent 会话（solver 或 meshing 模式），释放进程资源。
    每次完成仿真后应调用此函数。
    """
    global _fluent_session
    try:
        if _fluent_session is not None:
            _fluent_session.exit()
            _fluent_session = None
        return _ok(ok_message("Fluent 会话已退出", closed=True))
    except Exception as e:
        return _err(str(e))
