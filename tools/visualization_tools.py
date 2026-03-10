"""
可视化工具：通过 PyAEDT 在 Maxwell 中创建场量云图并导出图像。
支持磁通密度、损耗密度、温度场等物理量的彩色云图生成和 PNG 导出。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import os

from tools.utils import _ok, _err


def _app():
    """复用 maxwell_tools 中的全局 AEDT app 实例。"""
    from tools import maxwell_tools
    if maxwell_tools._aedt_app is None:
        raise RuntimeError("未连接到 AEDT，请先调用 connect_aedt。")
    return maxwell_tools._aedt_app


# 支持的场量及其说明（Maxwell 2D/3D 常用）
_FIELD_QUANTITIES = {
    "B": "磁通密度幅值（T）",
    "Bx": "磁通密度 X 分量",
    "By": "磁通密度 Y 分量",
    "H": "磁场强度幅值（A/m）",
    "J": "电流密度幅值（A/m²）",
    "CoreLoss": "铁耗密度（W/m³）",
    "OhmicLoss": "铜耗功率密度（W/m³）",
    "Temperature": "温度（°C，需先运行热仿真）",
    "StressX": "应力 X 分量（Pa）",
    "StressY": "应力 Y 分量（Pa）",
}


# ---------------------------------------------------------------------------
# 工具：create_field_plot - 在 AEDT 中创建场量云图
# ---------------------------------------------------------------------------

def create_field_plot(
    quantity: str = "B",
    plot_name: str = "",
    setup_name: str = "Setup1",
    sweep_name: str = "LastAdaptive",
    object_names: list[str] | None = None,
    plot_on_surface: bool = True,
) -> dict:
    """
    在 AEDT 后处理中创建场量彩色云图（用于可视化和报告导出）。

    Args:
        quantity: 场量名称，支持 "B"（磁通密度）、"H"（磁场强度）、
                  "J"（电流密度）、"CoreLoss"（铁耗密度）、"OhmicLoss"（铜耗密度）、
                  "Temperature"（温度，需热仿真数据）
        plot_name: 云图名称；留空则自动命名为 "{quantity}_Field_Plot"
        setup_name: 求解设置名称，默认 "Setup1"
        sweep_name: 扫描步名称，默认 "LastAdaptive"
        object_names: 要显示云图的几何体列表；None 则在所有几何体上绘制
        plot_on_surface: True 为表面云图，False 为体积云图（仅适用于 3D）
    """
    try:
        app = _app()
        plot_name = plot_name or f"{quantity}_Field_Plot"
        setup_sweep = f"{setup_name} : {sweep_name}"

        if object_names is None:
            # 获取所有非背景几何体
            try:
                object_names = [
                    obj.name for obj in app.modeler.objects.values()
                    if obj.name.lower() not in ("region", "background", "")
                ]
            except Exception:
                object_names = []

        if not object_names:
            return _err("未找到可绘制云图的几何体，请确认几何模型已建立")

        # 创建场图
        if plot_on_surface:
            plot = app.post.create_fieldplot_surface(
                objlist=object_names,
                quantityname=quantity,
                setup_name=setup_sweep,
                plot_name=plot_name,
            )
        else:
            plot = app.post.create_fieldplot_volume(
                objlist=object_names,
                quantityname=quantity,
                setup_name=setup_sweep,
                plot_name=plot_name,
            )

        qty_desc = _FIELD_QUANTITIES.get(quantity, quantity)
        return _ok({
            "plot_name": plot_name,
            "quantity": quantity,
            "quantity_description": qty_desc,
            "objects": object_names,
            "type": "surface" if plot_on_surface else "volume",
            "message": f"场量云图 '{plot_name}' 已创建（{qty_desc}，{len(object_names)} 个对象）",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_field_image - 将场量云图导出为 PNG 图像
# ---------------------------------------------------------------------------

def export_field_image(
    plot_name: str,
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    orientation: str = "",
) -> dict:
    """
    将 AEDT 中已有的场量云图导出为 PNG 图像文件。

    Args:
        plot_name: 要导出的云图名称（由 create_field_plot 创建）
        output_path: 输出图像文件路径（.png）；自动创建父目录
        width: 图像宽度（像素），默认 1920
        height: 图像高度（像素），默认 1080
        orientation: 视角方向，如 "XY"、"XZ"、"ISO"；留空为当前视角
    """
    try:
        app = _app()
        if not output_path.lower().endswith(".png"):
            output_path += ".png"

        parent_dir = os.path.dirname(os.path.abspath(output_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        # 设置视角（若指定）
        if orientation:
            try:
                app.post.oModule.FitAll()
                orient_map = {
                    "XY": [0, 0, 1, 0],
                    "XZ": [0, 1, 0, 0],
                    "YZ": [1, 0, 0, 0],
                    "ISO": [1, 1, 1, 0],
                }
                if orientation.upper() in orient_map:
                    app.post.SetActiveVariation(
                        "Orient", orient_map[orientation.upper()]
                    )
            except Exception:
                pass

        # 导出图像
        app.post.export_field_image_to_file(
            plot_name=plot_name,
            file_path=output_path,
            width=width,
            height=height,
        )

        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        return _ok({
            "output_path": output_path,
            "width": width,
            "height": height,
            "file_size_kb": round(file_size / 1024, 1),
            "message": f"云图 '{plot_name}' 已导出至 {output_path}（{width}×{height}px）",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：list_field_plots - 列出所有已有云图
# ---------------------------------------------------------------------------

def list_field_plots() -> dict:
    """
    列出当前设计中所有已创建的场量云图名称，便于管理和导出。
    """
    try:
        app = _app()
        plots = app.post.field_plots
        plot_info = []
        for name, plot in plots.items():
            plot_info.append({
                "name": name,
                "quantity": getattr(plot, "quantityname", "unknown"),
            })
        return _ok({
            "count": len(plot_info),
            "plots": plot_info,
        })
    except Exception as e:
        return _err(str(e))
