"""
Icepak 热分析工具：通过 PyAEDT 驱动 Ansys Icepak 进行电机热仿真。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, assign_power_sources, ok_message

_icepak_app = None  # 全局 Icepak 实例


def _app():
    if _icepak_app is None:
        raise RuntimeError("未连接到 Icepak，请先调用 connect_icepak。")
    return _icepak_app


# ---------------------------------------------------------------------------
# 工具：connect_icepak - 连接 Icepak
# ---------------------------------------------------------------------------

def connect_icepak(version: str | None = None, non_graphical: bool = False) -> dict:
    """连接到 AEDT Icepak 实例。

    Args:
        version: AEDT 版本号，如 "2024.1"、"2025.1"；不传则自动检测当前运行版本
        non_graphical: 是否以无界面批处理模式运行
    """
    global _icepak_app
    try:
        from ansys.aedt.core import Icepak
        kwargs = {"non_graphical": non_graphical, "new_desktop": False}
        if version is not None:
            kwargs["version"] = version
        _icepak_app = Icepak(**kwargs)
        version_desc = version if version else "（自动检测）"
        return _ok(ok_message(f"已连接到 Icepak {version_desc}", version=version))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_motor_thermal - 设置电机热分析模型
# ---------------------------------------------------------------------------

def setup_motor_thermal(
    copper_loss_W: float,
    iron_loss_W: float,
    ambient_temp_C: float = 25.0,
    cooling_type: str = "natural_convection",
) -> dict:
    """
    在 Icepak 中设置电机热耗散边界条件。

    Args:
        copper_loss_W: 绕组铜耗（W）
        iron_loss_W: 铁芯铁耗（W）
        ambient_temp_C: 环境温度（°C）
        cooling_type: 冷却方式，'natural_convection' 或 'forced_convection' 或 'water_jacket'
    """
    try:
        app = _app()
        # 设置环境温度
        app.modeler.set_working_coordinate_system("Global")

        # 为绕组和铁芯分配热源
        assignment = assign_power_sources(app, {
            "Winding": copper_loss_W,
            "Stator": iron_loss_W * 0.9,
            "Rotor": iron_loss_W * 0.1,
        })
        assigned_sources = [item.split("=", 1)[0] for item in assignment["assigned"]]
        missing_objects = assignment["missing"]
        source_errors = assignment["errors"]

        if not assigned_sources:
            details = []
            if missing_objects:
                details.append(f"缺少对象: {', '.join(missing_objects)}")
            if source_errors:
                details.append(f"热源分配失败: {'; '.join(source_errors)}")
            return _err("未能成功分配任何热源。" + (" " + " | ".join(details) if details else ""))

        # 设置对流冷却边界
        if cooling_type == "natural_convection":
            app.assign_free_opening(
                ["Region"],
                temperature=f"{ambient_temp_C}cel",
            )
        elif cooling_type in ("forced_convection", "water_jacket"):
            app.assign_openings(
                ["Region"],
                boundary_type="Opening",
                temperature=f"{ambient_temp_C}cel",
            )

        msg = (
            f"热分析边界已设置：铜耗={copper_loss_W}W，铁耗={iron_loss_W}W，"
            f"冷却={cooling_type}，热源对象={', '.join(assigned_sources)}"
        )
        if missing_objects:
            msg += f"；未找到对象={', '.join(missing_objects)}"
        if source_errors:
            msg += f"；部分热源分配失败={'; '.join(source_errors)}"
        return _ok(msg)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_thermal_simulation - 运行热仿真
# ---------------------------------------------------------------------------

def run_thermal_simulation(setup_name: str = "SetupThermal") -> dict:
    """运行 Icepak 稳态热仿真。"""
    try:
        app = _app()
        # 若 setup 已存在则直接使用，避免重复创建报错
        existing_names = [s.name for s in app.setups]
        if setup_name not in existing_names:
            setup = app.create_setup(setup_name)
            setup.props["Convergence Criteria - Max Iterations"] = 100
            setup.update()
        app.analyze_setup(setup_name)
        return _ok(ok_message(f"热仿真 '{setup_name}' 完成", setup_name=setup_name))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_temperature_results - 获取温度结果
# ---------------------------------------------------------------------------

def get_temperature_results(object_names: list[str] | None = None) -> dict:
    """
    获取各部件最高温度和平均温度。

    Args:
        object_names: 要查询的几何体名称列表，None 则查询所有
    """
    try:
        app = _app()
        if object_names is None:
            object_names = ["Winding", "Stator", "Rotor", "Magnet_1"]

        results = {}
        for name in object_names:
            try:
                max_temp = app.post.get_scalar_field_value(
                    "Temperature",
                    "Maximum",
                    object_name=name,
                )
                avg_temp = app.post.get_scalar_field_value(
                    "Temperature",
                    "Mean",
                    object_name=name,
                )
                results[name] = {
                    "max_temp_C": round(max_temp, 2) if max_temp else None,
                    "avg_temp_C": round(avg_temp, 2) if avg_temp else None,
                }
            except Exception:
                results[name] = {"error": "未找到该对象温度数据"}

        return _ok(results)
    except Exception as e:
        return _err(str(e))
