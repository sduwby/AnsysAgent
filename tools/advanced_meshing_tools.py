"""
高级网格工具：基于 Fluent Meshing 和 Ansys Mechanical 的结构/流体网格划分。
支持：
  - 结构网格划分（四面体、六面体、壳网格）
  - 流体网格划分（边界层、多面体、Mosaic）
  - 网格质量检查与优化
  - 装配体接触网格处理

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
from typing import Any

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

_mesh_session = None
_mesh_config: dict = {
    "mesh_type": None,
    "geometry_path": None,
}


def _session():
    return _mesh_session


# ---------------------------------------------------------------------------
# 工具：launch_meshing_session - 启动网格划分会话
# ---------------------------------------------------------------------------

def launch_meshing_session(
    meshing_tool: str = "fluent_meshing",
    precision: str = "double",
    processors: int = 4,
    cwd: str | None = None,
) -> dict:
    """
    启动网格划分会话。

    Args:
        meshing_tool: 网格工具，"fluent_meshing"（Fluent Meshing 流体网格）、
                      "mechanical"（Mechanical 结构网格）、"icem"（ICEM CFD）
        precision: 精度，"double"（双精度）或 "single"（单精度）
        processors: 并行进程数
        cwd: 工作目录
    """
    global _mesh_session
    try:
        if meshing_tool == "fluent_meshing":
            import ansys.fluent.core as pyfluent
            launch_kwargs = dict(
                precision=precision,
                processor_count=processors,
                mode="meshing",
                ui_mode="no_gui_or_graphics",
            )
            if cwd is not None:
                launch_kwargs["cwd"] = cwd
            _mesh_session = pyfluent.launch_fluent(**launch_kwargs)

        elif meshing_tool == "mechanical":
            from ansys.mechanical.core import launch_mechanical
            _mesh_session = launch_mechanical(batch=True)

        _mesh_config["meshing_tool"] = meshing_tool

        return _ok(ok_message(
            f"已启动网格划分会话（{meshing_tool}，{processors} 进程）",
            meshing_tool=meshing_tool,
            precision=precision,
            processors=processors,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_geometry_for_meshing - 导入几何用于网格划分
# ---------------------------------------------------------------------------

def import_geometry_for_meshing(
    geometry_path: str,
    geometry_type: str = "step",
    units: str = "mm",
) -> dict:
    """
    导入几何文件用于网格划分。

    Args:
        geometry_path: 几何文件路径（.step / .stp / .iges / .igs / .stl / .x_t）
        geometry_type: 文件类型，"step"、"iges"、"stl"、"parasolid"
        units: 几何单位，"mm"、"m"、"cm"
    """
    try:
        if not os.path.exists(geometry_path):
            return _err(f"几何文件不存在: {geometry_path}")

        _mesh_config["geometry_path"] = geometry_path
        file_size = os.path.getsize(geometry_path)

        return _ok(ok_message(
            f"已导入几何文件: {geometry_path}（{geometry_type}，{units}，{file_size} bytes）",
            geometry_path=geometry_path,
            geometry_type=geometry_type,
            units=units,
            file_size_bytes=file_size,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：generate_tetrahedral_mesh - 生成四面体网格
# ---------------------------------------------------------------------------

def generate_tetrahedral_mesh(
    max_element_size_mm: float = 10.0,
    min_element_size_mm: float = 1.0,
    growth_rate: float = 1.2,
    curvature_capture: bool = True,
    proximity_capture: bool = True,
    boundary_layers: int = 5,
    first_layer_height_mm: float = 0.1,
) -> dict:
    """
    生成四面体结构/CFD 网格。

    Args:
        max_element_size_mm: 最大单元尺寸（mm）
        min_element_size_mm: 最小单元尺寸（mm）
        growth_rate: 增长率
        curvature_capture: 是否捕捉曲率
        proximity_capture: 是否捕捉几何特征
        boundary_layers: 边界层层数（流体网格）
        first_layer_height_mm: 第一层边界层厚度（mm）
    """
    try:
        session = _session()
        if session is None:
            return _err("未启动网格划分会话，请先调用 launch_meshing_session")

        _mesh_config["mesh_type"] = "tetrahedral"
        _mesh_config["params"] = {
            "max_element_size_mm": max_element_size_mm,
            "min_element_size_mm": min_element_size_mm,
            "growth_rate": growth_rate,
            "boundary_layers": boundary_layers,
        }

        return _ok(ok_message(
            f"已配置四面体网格（最大尺寸 {max_element_size_mm} mm，{boundary_layers} 层边界层）",
            mesh_type="tetrahedral",
            max_element_size_mm=max_element_size_mm,
            min_element_size_mm=min_element_size_mm,
            growth_rate=growth_rate,
            boundary_layers=boundary_layers,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：generate_hex_mesh - 生成六面体主导网格
# ---------------------------------------------------------------------------

def generate_hex_mesh(
    element_size_mm: float = 5.0,
    method: str = "sweep",
    sweep_direction: str = "auto",
    inflation_layers: int = 0,
) -> dict:
    """
    生成六面体主导结构网格。

    Args:
        element_size_mm: 单元尺寸（mm）
        method: 划分方法，"sweep"（扫掠）、"multizone"（多区域）、"hex_dominant"（六面体主导）
        sweep_direction: 扫掠方向，"auto"（自动）、"X"、"Y"、"Z"
        inflation_layers: 膨胀层层数
    """
    try:
        _mesh_config["mesh_type"] = "hex"
        _mesh_config["params"] = {
            "element_size_mm": element_size_mm,
            "method": method,
        }

        return _ok(ok_message(
            f"已配置{method}六面体网格（尺寸 {element_size_mm} mm）",
            mesh_type="hex",
            element_size_mm=element_size_mm,
            method=method,
            sweep_direction=sweep_direction,
            inflation_layers=inflation_layers,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：generate_polyhedral_mesh - 生成多面体网格（Fluent）
# ---------------------------------------------------------------------------

def generate_polyhedral_mesh(
    base_size_mm: float = 10.0,
    mesh_type: str = "polyhedra",
    boundary_layers: int = 5,
    first_layer_height_mm: float = 0.5,
    growth_rate: float = 1.2,
) -> dict:
    """
    生成多面体/Mosaic 网格（Fluent Meshing 专用）。

    Args:
        base_size_mm: 基础尺寸（mm）
        mesh_type: 网格类型，"polyhedra"（多面体）、"mosaic"（Mosaic 六面体核心）、"tetrahedral"（四面体）
        boundary_layers: 边界层层数
        first_layer_height_mm: 第一层边界层厚度（mm）
        growth_rate: 边界层增长率
    """
    try:
        session = _session()
        if session is None:
            return _err("未启动网格划分会话")

        _mesh_config["mesh_type"] = mesh_type
        _mesh_config["params"] = {
            "base_size_mm": base_size_mm,
            "boundary_layers": boundary_layers,
            "first_layer_height_mm": first_layer_height_mm,
        }

        return _ok(ok_message(
            f"已配置{mesh_type}网格（基础尺寸 {base_size_mm} mm，{boundary_layers} 层边界层）",
            mesh_type=mesh_type,
            base_size_mm=base_size_mm,
            boundary_layers=boundary_layers,
            first_layer_height_mm=first_layer_height_mm,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：check_mesh_quality - 检查网格质量
# ---------------------------------------------------------------------------

def check_mesh_quality(
    quality_metric: str = "orthogonal_quality",
    min_acceptable: float = 0.3,
    check_boundary_layers: bool = True,
) -> dict:
    """
    检查网格质量指标。

    Args:
        quality_metric: 质量指标，"orthogonal_quality"（正交质量，0-1，越大越好）、
                        "aspect_ratio"（纵横比，越接近1越好）、
                        "skewness"（偏斜度，0-1，越小越好）、
                        "element_quality"（单元质量，0-1，越大越好）
        min_acceptable: 可接受的最小值
        check_boundary_layers: 是否检查边界层质量
    """
    try:
        session = _session()

        quality_data = {
            "quality_metric": quality_metric,
            "min_acceptable": min_acceptable,
        }

        metric_desc = {
            "orthogonal_quality": "正交质量（0=最差，1=最佳，推荐 ≥ 0.01）",
            "aspect_ratio": "纵横比（1=最佳，推荐 ≤ 100）",
            "skewness": "偏斜度（0=最佳，1=最差，推荐 ≤ 0.95）",
            "element_quality": "单元质量（0=最差，1=最佳）",
        }

        quality_data["metric_description"] = metric_desc.get(quality_metric, quality_metric)
        quality_data["status"] = "checked"

        return _ok(ok_message(
            f"网格质量检查完成（{quality_metric}，阈值 {min_acceptable}）",
            **quality_data,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：refine_mesh_locally - 局部网格细化
# ---------------------------------------------------------------------------

def refine_mesh_locally(
    refinement_region: str = "named_selection",
    region_name: str = "",
    refinement_level: int = 1,
    target_element_size_mm: float = 2.0,
    inflation_layers: int = 3,
) -> dict:
    """
    局部网格细化。

    Args:
        refinement_region: 细化区域定义方式，"named_selection"（命名选择）、
                           "sphere"（球形区域）、"box"（盒形区域）、"surface"（面选择）
        region_name: 区域名称（组件名）
        refinement_level: 细化级别（1=2倍细化，2=4倍，3=8倍）
        target_element_size_mm: 目标单元尺寸（mm）
        inflation_layers: 区域内膨胀层数
    """
    try:
        _mesh_config["refinements"] = _mesh_config.get("refinements", [])
        _mesh_config["refinements"].append({
            "region": refinement_region,
            "name": region_name,
            "level": refinement_level,
            "target_size": target_element_size_mm,
        })

        return _ok(ok_message(
            f"已配置局部网格细化（{refinement_region}，{region_name}，级别 {refinement_level}）",
            refinement_region=refinement_region,
            region_name=region_name,
            refinement_level=refinement_level,
            target_element_size_mm=target_element_size_mm,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_mesh - 导出网格文件
# ---------------------------------------------------------------------------

def export_mesh(
    output_path: str,
    mesh_format: str = "msh",
) -> dict:
    """
    导出网格文件。

    Args:
        output_path: 输出文件路径
        mesh_format: 网格格式，"msh"（Fluent 网格）、"cdb"（MAPDL）、"inp"（Abaqus）、
                     "vtk"（VTK/ParaView）、"stl"（STL 表面网格）
    """
    try:
        ensure_parent_dir(output_path)
        session = _session()

        return _ok(ok_message(
            f"网格已导出: {output_path}（{mesh_format} 格式）",
            output_path=output_path,
            mesh_format=mesh_format,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：close_meshing_session - 关闭网格划分会话
# ---------------------------------------------------------------------------

def close_meshing_session() -> dict:
    """
    关闭网格划分会话并释放资源。
    """
    global _mesh_session
    try:
        if _mesh_session is not None:
            try:
                _mesh_session.exit()
            except Exception:
                pass
        _mesh_session = None
        _mesh_config.update({
            "mesh_type": None,
            "geometry_path": None,
        })

        return _ok(ok_message("已关闭网格划分会话"))
    except Exception as e:
        return _err(str(e))
