"""
网格控制工具：通过 PyAEDT 配置 Maxwell 2D/3D 网格操作。
支持长度细化、集肤深度细化、曲面近似及网格统计查询。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err


def _app():
    """复用 maxwell_tools 中的全局 AEDT app 实例。"""
    from tools import maxwell_tools
    if maxwell_tools._aedt_app is None:
        raise RuntimeError("未连接到 AEDT，请先调用 connect_aedt。")
    return maxwell_tools._aedt_app


# ---------------------------------------------------------------------------
# 工具：setup_length_mesh - 长度细化
# ---------------------------------------------------------------------------

def setup_length_mesh(
    object_names: list[str],
    max_element_length: float,
    max_elements: int | None = None,
    operation_name: str = "LengthBased",
) -> dict:
    """
    对指定几何体分配基于长度的网格细化操作。

    Args:
        object_names: 要细化的几何体名称列表（如 ["Stator", "Rotor"]）
        max_element_length: 最大单元边长（mm），值越小网格越密
        max_elements: 最大单元数上限，None 表示不限制
        operation_name: 网格操作名称（相同名称会覆盖已有操作）
    """
    try:
        app = _app()
        app.mesh.assign_length_mesh(
            assignment=object_names,
            maxlength=max_element_length,
            maxel=max_elements,
            meshop_name=operation_name,
        )
        detail = f"最大边长={max_element_length}mm"
        if max_elements:
            detail += f"，最多 {max_elements} 个单元"
        return _ok(f"长度网格操作 '{operation_name}' 已添加：{object_names}，{detail}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_skin_depth_mesh - 集肤深度细化
# ---------------------------------------------------------------------------

def setup_skin_depth_mesh(
    object_names: list[str],
    skin_depth_mm: float,
    max_triangle_length_mm: float,
    num_layers: int = 2,
    operation_name: str = "SkinDepth",
) -> dict:
    """
    为导体或导磁体表面分配集肤深度细化操作（高频、涡流仿真必备）。

    集肤深度参考公式：δ = √(2 / (ω·μ·σ))，单位 m；
    通常铜导体在 1kHz 时 δ ≈ 2.1mm，在 10kHz 时 δ ≈ 0.66mm。

    Args:
        object_names: 几何体名称列表（导体绕组、永磁体、铁心等）
        skin_depth_mm: 集肤深度（mm）
        max_triangle_length_mm: 表面三角剖分最大边长（mm），
                                建议取 skin_depth_mm 的 2~5 倍
        num_layers: 集肤深度内的细化层数，默认 2（精度与速度平衡）
        operation_name: 网格操作名称
    """
    try:
        app = _app()
        app.mesh.assign_skin_depth(
            assignment=object_names,
            skin_depth=f"{skin_depth_mm}mm",
            triangulation_max_length=f"{max_triangle_length_mm}mm",
            num_layers=num_layers,
            meshop_name=operation_name,
        )
        return _ok(
            f"集肤深度网格操作 '{operation_name}' 已添加：{object_names}，"
            f"δ={skin_depth_mm}mm，层数={num_layers}"
        )
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_surface_mesh - 曲面近似
# ---------------------------------------------------------------------------

def setup_surface_mesh(
    object_names: list[str],
    surface_quality: int = 8,
    operation_name: str = "SurfaceApprox",
) -> dict:
    """
    为圆弧/曲面几何（气隙、磁极弧面等）分配曲面近似网格操作，
    提升圆形轮廓的几何精度。

    Args:
        object_names: 几何体名称列表（AirGap、Magnet_* 等圆弧对象）
        surface_quality: 曲面质量等级 1（粗）~10（精），默认 8
        operation_name: 网格操作名称
    """
    try:
        app = _app()
        quality = max(1, min(10, surface_quality))
        app.mesh.assign_surface_mesh(
            assignment=object_names,
            surface_mesh_quality=quality,
            meshop_name=operation_name,
        )
        return _ok(
            f"曲面近似网格操作 '{operation_name}' 已添加：{object_names}，质量等级={quality}"
        )
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_mesh_stats - 网格统计
# ---------------------------------------------------------------------------

def get_mesh_stats(setup_name: str = "Setup1") -> dict:
    """
    获取指定求解设置的网格统计信息（单元数、节点数等）。
    需在至少一次自适应网格剖分（或完整求解）之后调用。

    Args:
        setup_name: 求解设置名称，默认 "Setup1"
    """
    try:
        app = _app()
        stats_raw = app.mesh.stats(setup_name)
        if isinstance(stats_raw, dict):
            stats = stats_raw
        else:
            stats = {"info": str(stats_raw)}
        return _ok(stats)
    except Exception as e:
        return _err(str(e))
