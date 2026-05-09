"""
PyAnsys Geometry 工具：通过 ansys-geometry-core 驱动 Ansys Geometry Service。
支持完整建模工作流：启动 Modeler、创建设计、Sketch 草图操作、实体拉伸、
命名选择创建、文件导出（FMD / PMDB / SCDOCX）及会话关闭。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。

参考工作流：
  - pyansys-workflows/geometry-mesh/wf_gm_01_geometry.py
  - pyansys-workflows/geometry-mechanical-dpf/wf_gmd_01_geometry.py
  - pyansys-workflows/geometry-mesh-fluent/wf_gmf_01_geometry.py
"""

from __future__ import annotations

from tools.utils import _ok, _err, ok_message

_modeler = None       # 全局 Modeler 实例
_active_design = None  # 当前激活的 Design 实例


def _get_modeler():
    if _modeler is None:
        raise RuntimeError("未连接到 Geometry Modeler，请先调用 connect_geometry_modeler。")
    return _modeler


def _get_design():
    if _active_design is None:
        raise RuntimeError("尚未创建几何设计，请先调用 create_geometry_design。")
    return _active_design


# ---------------------------------------------------------------------------
# 工具：connect_geometry_modeler - 启动 Geometry Modeler
# ---------------------------------------------------------------------------

def connect_geometry_modeler(
    host: str = "localhost",
    port: int = 50051,
    transport_mode: str | None = None,
) -> dict:
    """
    启动或连接到 Ansys Geometry Service 的 Modeler 实例。

    Args:
        host: Geometry Service 主机地址，默认 "localhost"
        port: Geometry Service 端口，默认 50051
        transport_mode: 传输模式，None（自动）、"insecure" 或 "tls"；
                        在容器/CI 环境中通常使用 "insecure"
    """
    global _modeler
    try:
        from ansys.geometry.core import launch_modeler

        kwargs: dict = {}
        if transport_mode is not None:
            kwargs["transport_mode"] = transport_mode

        _modeler = launch_modeler(**kwargs)
        return _ok(ok_message(
            f"已启动 Geometry Modeler（host={host}，port={port}）",
            host=host,
            port=port,
            transport_mode=transport_mode,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_geometry_design - 创建几何设计
# ---------------------------------------------------------------------------

def create_geometry_design(design_name: str = "AnsysAgentDesign") -> dict:
    """
    在当前 Modeler 会话中创建一个新的几何设计（Design）。

    Args:
        design_name: 设计名称，将作为 Ansys Geometry 中的项目名
    """
    global _active_design
    try:
        modeler = _get_modeler()
        _active_design = modeler.create_design(design_name)
        return _ok(ok_message(f"已创建几何设计 '{design_name}'", design_name=design_name))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：set_geometry_units - 设置默认长度单位
# ---------------------------------------------------------------------------

def set_geometry_units(unit: str = "mm") -> dict:
    """
    设置 PyAnsys Geometry 的全局默认长度单位。

    Args:
        unit: 长度单位字符串，常用值："mm"、"cm"、"m"、"in"
    """
    try:
        from ansys.geometry.core.misc import DEFAULT_UNITS, UNITS
        unit_lower = unit.lower()
        unit_map = {
            "mm": "mm", "millimeter": "mm",
            "cm": "cm", "centimeter": "cm",
            "m": "m", "meter": "m",
            "in": "in", "inch": "in",
        }
        resolved = unit_map.get(unit_lower)
        if resolved is None:
            return _err(f"不支持的单位：{unit}，可用：{list(unit_map.keys())}")
        DEFAULT_UNITS.LENGTH = getattr(UNITS, resolved)
        return _ok(ok_message(f"已将默认长度单位设置为 {resolved}", unit=resolved))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_sketch_rectangle - 在草图中绘制矩形轮廓
# ---------------------------------------------------------------------------

def create_sketch_and_extrude(
    profile_type: str = "rectangle",
    width: float = 8.0,
    height: float = 10.0,
    extrude_distance: float = 1.0,
    body_name: str = "Body",
    center_x: float = 0.0,
    center_y: float = 0.0,
    hole_radius: float | None = None,
) -> dict:
    """
    在当前设计中创建草图并拉伸成实体。

    支持的轮廓类型：
    - "rectangle"：矩形（宽×高），可选中心圆孔
    - "circle"：圆形轮廓

    Args:
        profile_type: "rectangle" 或 "circle"
        width: 矩形宽度（当前长度单位），或圆形直径
        height: 矩形高度（当前长度单位）
        extrude_distance: 拉伸距离（当前长度单位）
        body_name: 拉伸后实体名称
        center_x: 草图中心 X 坐标
        center_y: 草图中心 Y 坐标
        hole_radius: 若非 None，在矩形中心添加圆孔（半径，当前单位）
    """
    try:
        from ansys.geometry.core.math import Point2D
        from ansys.geometry.core.misc import Distance
        from ansys.geometry.core.sketch import Sketch

        design = _get_design()
        sketch = Sketch()

        if profile_type == "rectangle":
            sketch.box(
                center=Point2D([center_x, center_y]),
                width=Distance(width),
                height=Distance(height),
            )
            if hole_radius is not None:
                sketch.circle(
                    center=Point2D([center_x, center_y]),
                    radius=Distance(hole_radius),
                )
        elif profile_type == "circle":
            sketch.circle(
                center=Point2D([center_x, center_y]),
                radius=Distance(width / 2),
            )
        else:
            return _err(f"不支持的轮廓类型：{profile_type}，可用：rectangle / circle")

        body = design.extrude_sketch(
            name=body_name,
            sketch=sketch,
            distance=Distance(extrude_distance),
        )
        return _ok(ok_message(
            f"已创建实体 '{body_name}'（{profile_type}，拉伸={extrude_distance}）",
            body_name=body_name,
            profile_type=profile_type,
            extrude_distance=extrude_distance,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_geometry_component - 在设计中添加组件
# ---------------------------------------------------------------------------

def add_geometry_component(component_name: str = "Component") -> dict:
    """
    在当前设计中添加一个子组件（Component），用于组织多体装配。

    Args:
        component_name: 组件名称
    """
    try:
        design = _get_design()
        comp = design.add_component(component_name)
        # 将组件存入设计对象的临时属性，以便后续调用引用
        if not hasattr(design, "_agent_components"):
            design._agent_components = {}
        design._agent_components[component_name] = comp
        return _ok(ok_message(f"已添加组件 '{component_name}'", component_name=component_name))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_named_selection - 创建命名选择
# ---------------------------------------------------------------------------

def create_named_selection(
    selection_name: str,
    body_names: list[str] | None = None,
) -> dict:
    """
    在当前设计中为指定实体创建命名选择（Named Selection）。
    命名选择可在 Mechanical、Fluent 等下游工具中引用。

    Args:
        selection_name: 命名选择名称
        body_names: 要加入此命名选择的实体名称列表；
                    None 则将设计中所有实体全部加入
    """
    try:
        design = _get_design()
        if body_names is None:
            target_bodies = design.bodies
        else:
            all_bodies = {b.name: b for b in design.bodies}
            target_bodies = []
            missing = []
            for name in body_names:
                if name in all_bodies:
                    target_bodies.append(all_bodies[name])
                else:
                    missing.append(name)
            if missing:
                return _err(f"未找到以下实体：{missing}，当前设计包含：{list(all_bodies.keys())}")

        design.create_named_selection(name=selection_name, bodies=target_bodies)
        return _ok(ok_message(
            f"已创建命名选择 '{selection_name}'（{len(target_bodies)} 个实体）",
            selection_name=selection_name,
            body_count=len(target_bodies),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_geometry - 导出几何文件
# ---------------------------------------------------------------------------

def export_geometry(
    output_path: str,
    file_format: str = "pmdb",
) -> dict:
    """
    将当前设计导出为几何文件，供下游仿真工具（Mechanical、Fluent、Prime）使用。

    支持格式：
    - "pmdb"  → Ansys Mechanical 首选格式（.pmdb）
    - "fmd"   → Fluent Meshing 首选格式（.fmd）
    - "scdocx"→ SpaceClaim 原生格式（.scdocx）

    Args:
        output_path: 输出文件的完整路径（含文件名，无需带扩展名）
        file_format: 导出格式，"pmdb"、"fmd" 或 "scdocx"
    """
    try:
        from pathlib import Path
        from ansys.geometry.core.designer import DesignFileFormat

        design = _get_design()
        format_map = {
            "pmdb": DesignFileFormat.PMDB,
            "fmd": DesignFileFormat.FMD,
            "scdocx": DesignFileFormat.SCDOCX,
        }
        fmt_key = file_format.lower()
        if fmt_key not in format_map:
            return _err(f"不支持的格式：{file_format}，可用：{list(format_map.keys())}")

        ext_map = {"pmdb": ".pmdb", "fmd": ".fmd", "scdocx": ".scdocx"}
        if not output_path.endswith(ext_map[fmt_key]):
            output_path = output_path + ext_map[fmt_key]

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # PMDB 用 export_to_pmdb 方法（返回路径），其他用 download
        if fmt_key == "pmdb":
            result_path = design.export_to_pmdb(str(out.parent))
        else:
            result_path = design.download(
                file_location=out,
                format=format_map[fmt_key],
            )

        return _ok(ok_message(
            f"几何文件已导出：{result_path}（格式={file_format}）",
            output_path=str(result_path),
            file_format=file_format,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：plot_geometry - 显示几何图形（需 GUI 环境）
# ---------------------------------------------------------------------------

def plot_geometry() -> dict:
    """
    在当前 Modeler 会话中渲染并显示几何设计（需要可用的图形环境）。
    无 GUI 环境下会返回警告但不会中止工作流。
    """
    try:
        design = _get_design()
        design.plot()
        return _ok(ok_message("几何图形已显示"))
    except Exception as e:
        return _ok(ok_message(f"几何显示跳过（可能无 GUI 环境）：{e}", warning=str(e)))


# ---------------------------------------------------------------------------
# 工具：close_geometry_modeler - 关闭 Geometry Modeler 会话
# ---------------------------------------------------------------------------

def close_geometry_modeler() -> dict:
    """
    关闭当前 Geometry Modeler 会话并释放服务端资源。
    每次完成建模后应调用此函数以避免资源泄漏。
    """
    global _modeler, _active_design
    try:
        if _modeler is not None:
            _modeler.close()
            _modeler = None
            _active_design = None
        return _ok(ok_message("Geometry Modeler 会话已关闭", closed=True))
    except Exception as e:
        return _err(str(e))
