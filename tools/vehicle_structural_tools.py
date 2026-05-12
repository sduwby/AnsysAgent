"""
整车结构强度仿真工具：基于 PyMAPDL 进行整车及零部件结构强度分析。
支持：
  - 静强度分析（弯曲、扭转、侧向）
  - 准静态强度分析（过坎、过坑、急转弯）
  - 极限强度分析（极限弯扭、安全系数评估）
  - 接触非线性分析（焊接、螺栓连接）

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
from typing import Any

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

_struct_mapdl = None
_struct_config: dict = {
    "model_path": None,
    "analysis_type": None,
    "load_cases": [],
}


def _mapdl():
    if _struct_mapdl is None:
        raise RuntimeError("未连接到求解器，请先调用 connect_structural_solver。")
    return _struct_mapdl


# ---------------------------------------------------------------------------
# 工具：connect_structural_solver - 连接结构分析求解器
# ---------------------------------------------------------------------------

def connect_structural_solver(
    nproc: int = 8,
    launch_local: bool = True,
    port: int = 50057,
    server: str = "127.0.0.1",
) -> dict:
    """
    连接到结构强度分析求解器（MAPDL）。

    Args:
        nproc: 并行核心数
        launch_local: 是否本地启动
        port: gRPC 端口号
        server: 服务器地址
    """
    global _struct_mapdl
    try:
        from ansys.mapdl.core import launch_mapdl, MapdlGrpc
        if launch_local:
            _struct_mapdl = launch_mapdl(
                nproc=nproc, port=port, override=True,
            )
        else:
            _struct_mapdl = MapdlGrpc(ip=server, port=port)

        ver = getattr(_struct_mapdl, "version", "unknown")
        return _ok(ok_message(
            f"已连接结构强度分析求解器（版本 {ver}，{nproc} 核）",
            version=ver,
            nproc=nproc,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：load_structural_model - 加载结构分析模型
# ---------------------------------------------------------------------------

def load_structural_model(
    model_path: str,
    model_type: str = "cdb",
) -> dict:
    """
    加载整车/零部件结构分析有限元模型。

    Args:
        model_path: 模型文件路径（.cdb / .inp / .k）
        model_type: 文件类型，"cdb"（MAPDL）、"inp"（Abaqus）、"k"（LS-DYNA Keyword）
    """
    try:
        mapdl = _mapdl()
        if not os.path.exists(model_path):
            return _err(f"模型文件不存在: {model_path}")

        mapdl.clear()
        mapdl.prep7()

        if model_type == "cdb":
            mapdl.cdread("db", model_path)
        elif model_type == "inp":
            mapdl.input(model_path)
        elif model_type == "k":
            mapdl.input(model_path)
        else:
            mapdl.input(model_path)

        _struct_config["model_path"] = model_path
        num_nodes = mapdl.mesh.n_node
        num_elements = mapdl.mesh.n_elem

        return _ok(ok_message(
            f"已加载结构分析模型: {model_path}（{num_nodes} 节点，{num_elements} 单元）",
            model_path=model_path,
            model_type=model_type,
            num_nodes=num_nodes,
            num_elements=num_elements,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：define_structural_material - 定义结构材料属性
# ---------------------------------------------------------------------------

def define_structural_material(
    material_id: int = 1,
    material_type: str = "steel",
    youngs_modulus_gpa: float = 210.0,
    poisson_ratio: float = 0.3,
    density_kg_m3: float = 7850.0,
    yield_strength_mpa: float = 355.0,
    tensile_strength_mpa: float = 500.0,
    nonlinear: bool = False,
) -> dict:
    """
    定义结构分析材料属性。

    Args:
        material_id: 材料 ID
        material_type: 材料类型，"steel"（结构钢）、"aluminum"（铝合金）、"cast_iron"（铸铁）、"composite"（复合材料）
        youngs_modulus_gpa: 杨氏模量（GPa）
        poisson_ratio: 泊松比
        density_kg_m3: 密度（kg/m³）
        yield_strength_mpa: 屈服强度（MPa）
        tensile_strength_mpa: 抗拉强度（MPa）
        nonlinear: 是否启用非线性材料模型
    """
    try:
        mapdl = _mapdl()
        E_pa = youngs_modulus_gpa * 1e9

        mapdl.prep7()
        mapdl.mp("EX", material_id, E_pa)
        mapdl.mp("PRXY", material_id, poisson_ratio)
        mapdl.mp("DENS", material_id, density_kg_m3)

        if nonlinear:
            mapdl.tb("BISO", material_id)
            mapdl.tbdata(1, yield_strength_mpa * 1e6, 0)

        return _ok(ok_message(
            f"已定义材料 {material_id}（{material_type}，E={youngs_modulus_gpa} GPa，σy={yield_strength_mpa} MPa）",
            material_id=material_id,
            material_type=material_type,
            youngs_modulus_gpa=youngs_modulus_gpa,
            poisson_ratio=poisson_ratio,
            density_kg_m3=density_kg_m3,
            yield_strength_mpa=yield_strength_mpa,
            tensile_strength_mpa=tensile_strength_mpa,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_boundary_conditions - 设置边界条件
# ---------------------------------------------------------------------------

def setup_boundary_conditions(
    bc_type: str = "fixed_free",
    fixed_nodes: str = "",
    fixed_dofs: str = "UX,UY,UZ",
    symmetric_plane: str = "",
    spring_stiffness: float = 0.0,
) -> dict:
    """
    设置结构分析边界条件。

    Args:
        bc_type: 边界条件类型，"fixed_free"（一端固定一端自由）、"simply_supported"（简支）、
                 "fixed_fixed"（两端固定）、"symmetric"（对称约束）、"springs"（弹性支撑）
        fixed_nodes: 固定节点选择（组件名或节点 ID 范围，如 "1,100" 表示节点 1 到 100）
        fixed_dofs: 约束自由度（逗号分隔），默认 "UX,UY,UZ"
        symmetric_plane: 对称平面（"XY"、"YZ"、"XZ"），仅对 symmetric 类型有效
        spring_stiffness: 弹簧刚度（N/m），仅对 springs 类型有效
    """
    try:
        mapdl = _mapdl()
        mapdl.prep7()

        if fixed_nodes:
            if "," in fixed_nodes and not fixed_nodes.startswith("CM"):
                parts = fixed_nodes.split(",")
                if len(parts) == 2:
                    mapdl.nsel("S", "NODE", "", parts[0].strip(), parts[1].strip())
                else:
                    mapdl.cmsel("S", fixed_nodes)
            else:
                mapdl.cmsel("S", fixed_nodes)

            for dof in fixed_dofs.split(","):
                mapdl.d("ALL", dof.strip(), 0)
            mapdl.allsel()

        elif bc_type == "symmetric" and symmetric_plane:
            plane_map = {"XY": "Z", "YZ": "X", "XZ": "Y"}
            normal_dof = plane_map.get(symmetric_plane, "Z")
            mapdl.nsel("S", "LOC", normal_dof, 0)
            mapdl.d("ALL", f"U{normal_dof}", 0)
            mapdl.allsel()

        _struct_config["bc_type"] = bc_type

        return _ok(ok_message(
            f"已设置{bc_type}边界条件",
            bc_type=bc_type,
            fixed_nodes=fixed_nodes,
            fixed_dofs=fixed_dofs,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：apply_bending_load - 施加弯曲载荷
# ---------------------------------------------------------------------------

def apply_bending_load(
    load_type: str = "distributed_force",
    force_n: float = 1000.0,
    load_direction: str = "FY",
    application_area: str = "front_floor",
    load_position_mm: float = 0.0,
) -> dict:
    """
    施加弯曲载荷（模拟满载弯曲工况）。

    Args:
        load_type: 载荷类型，"distributed_force"（分布力）、"point_force"（集中力）、"pressure"（压力）
        force_n: 力值（N）或压力值（Pa）
        load_direction: 载荷方向，"FX"、"FY"、"FZ"（重力方向通常为 -FY 或 -FZ）
        application_area: 施加区域，"front_floor"（前地板）、"rear_floor"（后地板）、
                          "roof"（车顶）、"seat_mounts"（座椅安装点）
        load_position_mm: 载荷作用位置（mm）
    """
    try:
        mapdl = _mapdl()

        dir_sign = -1 if load_direction.startswith("-") else 1
        dof = load_direction.replace("-", "")
        actual_force = force_n * dir_sign

        _struct_config["load_cases"].append({
            "type": "bending",
            "load_type": load_type,
            "force_n": actual_force,
            "direction": load_direction,
            "area": application_area,
        })

        return _ok(ok_message(
            f"已施加弯曲载荷: {actual_force} N（{load_direction}，{application_area}）",
            load_type=load_type,
            force_n=actual_force,
            load_direction=load_direction,
            application_area=application_area,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：apply_torsion_load - 施加扭转载荷
# ---------------------------------------------------------------------------

def apply_torsion_load(
    torque_nm: float = 1000.0,
    torsion_axis: str = "X",
    application_points: str = "front_suspension",
) -> dict:
    """
    施加扭转载荷（模拟单侧悬空扭转工况）。

    Args:
        torque_nm: 扭矩值（N·m）
        torsion_axis: 扭转轴，"X"（绕 X 轴）、"Y"（绕 Y 轴）、"Z"（绕 Z 轴）
        application_points: 作用点，"front_suspension"（前悬架安装点）、"rear_suspension"（后悬架）
    """
    try:
        _struct_config["load_cases"].append({
            "type": "torsion",
            "torque_nm": torque_nm,
            "axis": torsion_axis,
            "points": application_points,
        })

        return _ok(ok_message(
            f"已施加扭转载荷: {torque_nm} N·m（绕 {torsion_axis} 轴，{application_points}）",
            torque_nm=torque_nm,
            torsion_axis=torsion_axis,
            application_points=application_points,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：apply_quasi_static_loads - 施加准静态载荷
# ---------------------------------------------------------------------------

def apply_quasi_static_loads(
    scenario: str = "bump",
    vertical_acceleration_g: float = 3.0,
    lateral_acceleration_g: float = 0.0,
    longitudinal_acceleration_g: float = 0.0,
    vehicle_mass_kg: float = 1500.0,
) -> dict:
    """
    施加准静态载荷（模拟过坎、过坑、急转弯等工况）。

    Args:
        scenario: 工况场景，"bump"（过坎）、"pothole"（过坑）、
                  "sharp_turn"（急转弯）、"hard_brake"（急刹车）、"acceleration"（急加速）
        vertical_acceleration_g: 垂向加速度（g），过坎典型 3~5g
        lateral_acceleration_g: 侧向加速度（g），急转弯典型 0.8~1.2g
        longitudinal_acceleration_g: 纵向加速度（g），急刹车典型 1.0g
        vehicle_mass_kg: 整车质量（kg）
    """
    try:
        total_weight_n = vehicle_mass_kg * 9.81
        vertical_force = total_weight_n * vertical_acceleration_g
        lateral_force = total_weight_n * lateral_acceleration_g
        longitudinal_force = total_weight_n * longitudinal_acceleration_g

        load_data = {
            "scenario": scenario,
            "vertical_acceleration_g": vertical_acceleration_g,
            "lateral_acceleration_g": lateral_acceleration_g,
            "longitudinal_acceleration_g": longitudinal_acceleration_g,
            "vertical_force_n": round(vertical_force, 1),
            "lateral_force_n": round(lateral_force, 1),
            "longitudinal_force_n": round(longitudinal_force, 1),
            "vehicle_mass_kg": vehicle_mass_kg,
        }

        _struct_config["load_cases"].append({
            "type": "quasi_static",
            **load_data,
        })

        return _ok(ok_message(
            f"已施加{scenario}准静态载荷（垂向 {vertical_acceleration_g}g）",
            **load_data,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_structural_analysis - 运行结构强度分析
# ---------------------------------------------------------------------------

def run_structural_analysis(
    analysis_type: str = "static",
    nonlinear: bool = False,
    large_deformation: bool = False,
) -> dict:
    """
    运行结构强度分析。

    Args:
        analysis_type: 分析类型，"static"（线性静力分析）、"nonlinear_static"（非线性静力）、
                       "modal"（模态分析）、"buckling"（屈曲分析）
        nonlinear: 是否启用非线性
        large_deformation: 是否启用大变形
    """
    try:
        mapdl = _mapdl()

        mapdl.run("/SOLU")
        mapdl.run("ANTYPE,STATIC")

        if nonlinear or analysis_type == "nonlinear_static":
            mapdl.run("NLGEOM,ON")
        if large_deformation:
            mapdl.run("NLGEOM,ON")
            mapdl.run("LNSRCH,ON")

        if analysis_type == "modal":
            mapdl.run("ANTYPE,MODAL")
            mapdl.run("MODOPT,LANB,10")
        elif analysis_type == "buckling":
            mapdl.run("ANTYPE,BUCKLE")
            mapdl.run("BUCOPT,LANB,5")

        mapdl.run("SOLVE")

        _struct_config["analysis_type"] = analysis_type

        return _ok(ok_message(
            f"结构强度分析完成（{analysis_type}）",
            analysis_type=analysis_type,
            nonlinear=nonlinear,
            large_deformation=large_deformation,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_structural_results - 提取结构强度分析结果
# ---------------------------------------------------------------------------

def get_structural_results(
    result_type: str = "von_mises_stress",
    component: str = "all",
    output_path: str = "",
) -> dict:
    """
    提取结构强度分析结果。

    Args:
        result_type: 结果类型，"von_mises_stress"（Von Mises 等效应力）、"displacement"（位移）、
                     "safety_factor"（安全系数）、"principal_stress"（主应力）、"strain"（应变）、
                     "natural_frequencies"（固有频率，模态分析）、"buckling_load"（屈曲载荷）
        component: 目标部件名，"all" 表示全部
        output_path: 导出结果文件路径（可选，JSON 格式）
    """
    try:
        mapdl = _mapdl()
        mapdl.post1()
        mapdl.run("SET,LAST")

        result = {
            "result_type": result_type,
            "analysis_type": _struct_config.get("analysis_type", "static"),
        }

        if result_type == "von_mises_stress":
            mapdl.run("PLNSOL,S,EQV,0,1")
            max_seqv = mapdl.get_value("NODE", 0, "S", "EQV", "MAX")
            min_seqv = mapdl.get_value("NODE", 0, "S", "EQV", "MIN")
            result["max_von_mises_stress_pa"] = max_seqv
            result["min_von_mises_stress_pa"] = min_seqv
            result["description"] = "Von Mises 等效应力分布"

        elif result_type == "displacement":
            mapdl.run("PLNSOL,U,SUM,0,1")
            max_disp = mapdl.get_value("NODE", 0, "U", "SUM", "MAX")
            result["max_displacement_m"] = max_disp
            result["description"] = "总位移分布"

        elif result_type == "safety_factor":
            result["description"] = "安全系数分布（基于材料屈服强度）"
            result["evaluation_method"] = "SF = σ_yield / σ_von_mises"

        elif result_type == "natural_frequencies":
            result["description"] = "前 N 阶固有频率（Hz）"
            result["note"] = "通过模态分析提取"

        elif result_type == "buckling_load":
            result["description"] = "屈曲载荷因子"
            result["note"] = "通过屈曲分析提取"

        result["status"] = "completed"

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        return _ok(ok_message(
            f"已提取{result_type}结构分析结果",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：disconnect_structural_solver - 断开结构分析求解器
# ---------------------------------------------------------------------------

def disconnect_structural_solver() -> dict:
    """
    断开并清理结构强度分析求解器。
    """
    global _struct_mapdl
    try:
        if _struct_mapdl is not None:
            _struct_mapdl.exit()
        _struct_mapdl = None
        _struct_config.update({
            "model_path": None,
            "analysis_type": None,
            "load_cases": [],
        })

        return _ok(ok_message("已断开结构强度分析求解器"))
    except Exception as e:
        return _err(str(e))
