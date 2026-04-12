"""
RMXprt 快速电机初设计工具：通过 PyAEDT 驱动 Ansys RMXprt 进行解析法电机设计，
快速完成初始参数估算后导出到 Maxwell 进行精确 FEM 仿真。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, append_warnings, ok_message

_rmxprt_app = None  # 全局 RMXprt 实例

# RMXprt 电机类型映射（用户友好名 → PyAEDT 0.25.x solution_type 代码）
# 代码来源：DesignType.RMXPRT.solution_types（PyAEDT 0.25.1 实测）
_MOTOR_TYPE_MAP = {
    "PMSM":  "TPSM",   # Three-Phase Permanent-Magnet Synchronous Motor
    "BLDC":  "BLDC",   # Brushless DC Motor
    "IM":    "TPIM",   # Three-Phase Induction Motor
    "SRM":   "SRM",    # Switched Reluctance Motor
    "PMDC":  "PMDC",   # Permanent-Magnet DC Motor
    "SYN":   "TPSM",   # Three-Phase Synchronous (same code as PMSM)
    "SYNRM": "LSSM",   # Line-Start Synchronous / SynRM
    "SPIM":  "SPIM",   # Single-Phase Induction Motor
    "GRM":   "GRM",    # Generic Rotating Machine
}


def _app():
    if _rmxprt_app is None:
        raise RuntimeError("未连接到 RMXprt，请先调用 connect_rmxprt。")
    return _rmxprt_app


# ---------------------------------------------------------------------------
# 工具：connect_rmxprt - 连接 RMXprt
# ---------------------------------------------------------------------------

def connect_rmxprt(
    version: str | None = None,
    non_graphical: bool = False,
    motor_type: str | None = None,
) -> dict:
    """
    连接到 Ansys RMXprt（解析法电机设计模块）。

    Args:
        version: AEDT 版本号，如 "2024.1"、"2025.1"；不传则自动检测当前运行版本
        non_graphical: 是否以无界面批处理模式运行
        motor_type: 电机类型，用于设置设计的 solution_type。
            可选值：
              "PMSM"  — 三相永磁同步电机（最常用，PMSM/IPM/SPM）
              "BLDC"  — 无刷直流电机
              "IM"    — 三相感应电机
              "SRM"   — 开关磁阻电机
              "PMDC"  — 永磁直流电机
              "SYN"   — 三相同步电机
              "SYNRM" — 线启动同步磁阻电机
              "GRM"   — 通用旋转电机（默认，不指定时使用此类型）
            不传或传 None 则使用 AEDT 默认（GRM，通用旋转电机）。
    """
    global _rmxprt_app
    try:
        from ansys.aedt.core import Rmxprt
        kwargs = {"non_graphical": non_graphical, "new_desktop": False}
        if version is not None:
            kwargs["version"] = version
        # 将电机类型映射为 PyAEDT 0.25.x solution_type 代码
        solution_type = None
        if motor_type is not None:
            solution_type = _MOTOR_TYPE_MAP.get(motor_type.upper(), motor_type)
            kwargs["solution_type"] = solution_type
        _rmxprt_app = Rmxprt(**kwargs)
        version_desc = version if version else "（自动检测）"
        motor_desc = f"，电机类型={motor_type}({solution_type})" if motor_type else ""
        return _ok(ok_message(
            f"已连接到 RMXprt {version_desc}{motor_desc}",
            version=version,
            motor_type=motor_type,
            solution_type=solution_type,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_motor_from_template - 使用 RMXprt 模板快速建立电机设计
# ---------------------------------------------------------------------------

def create_motor_from_template(
    motor_type: str = "PMSM",
    stator_outer_diameter: float = 130.0,
    stator_inner_diameter: float = 80.0,
    rotor_outer_diameter: float = 78.4,
    shaft_diameter: float = 20.0,
    stack_length: float = 60.0,
    num_poles: int = 8,
    num_slots: int = 48,
    rated_speed: float = 3000.0,
    rated_voltage: float = 220.0,
    rated_power: float = 1500.0,
    design_name: str = "RMXprt_Motor",
) -> dict:
    """
    在 RMXprt 中使用解析法模板快速建立电机初始设计，获取性能预估值。

    Args:
        motor_type: 电机类型，"PMSM"（永磁同步）、"BLDC"（无刷直流）、
                    "IM"（三相感应）、"SRM"（开关磁阻）、"SYN"（同步）
        stator_outer_diameter: 定子外径（mm）
        stator_inner_diameter: 定子内径（mm）
        rotor_outer_diameter: 转子外径（mm）
        shaft_diameter: 轴径（mm）
        stack_length: 铁芯轴向长度（mm）
        num_poles: 极数
        num_slots: 定子槽数
        rated_speed: 额定转速（rpm）
        rated_voltage: 额定线电压有效值（V）
        rated_power: 额定功率（W）
        design_name: 设计名称
    """
    try:
        warnings: list[str] = []
        app = _app()

        if stator_inner_diameter >= stator_outer_diameter:
            return _err("定子内径必须小于定子外径")
        if rotor_outer_diameter >= stator_inner_diameter:
            return _err("转子外径必须小于定子内径")
        if shaft_diameter >= rotor_outer_diameter:
            return _err("轴径必须小于转子外径")
        if stack_length <= 0:
            return _err("铁芯轴向长度必须为正值")
        if num_poles <= 0 or num_slots <= 0:
            return _err("极数和槽数必须为正整数")

        # 重命名当前活动设计（solution_type 已在 connect_rmxprt 时由 Rmxprt() 构造函数正确设置）
        # 不调用 insert_design() —— 其会额外新建一个 Generic Rotating Machine 设计
        try:
            app.rename_design(design_name)
        except Exception as e:
            warnings.append(f"设计重命名失败，将使用当前设计名: {e}")

        def _set_prop(component_path: str, prop_name: str, value: str) -> bool:
            """使用 PyAEDT OO API 写入 RMXprt 组件属性，失败时回退到 ChangeProperty。"""
            try:
                return app.set_oo_property_value(app.odesign, component_path, prop_name, value)
            except Exception:
                pass
            # 回退：使用 odesign.ChangeProperty（路径用 "/" 而非 "\\"）
            prop_server = component_path.replace("\\", "/")
            try:
                app.odesign.ChangeProperty([
                    "NAME:AllTabs",
                    ["NAME:DefinitionTab",
                     ["NAME:PropServers", prop_server],
                     ["NAME:ChangedProps",
                      [f"NAME:{prop_name}", "Value:=", value]]
                     ]
                ])
                return True
            except Exception:
                return False

        # ── 定子铁芯几何 ──────────────────────────────────────────────
        applied = 0
        failed: list[str] = []

        props_to_set = [
            ("Stator\\Core", "OuterDiameter", f"{stator_outer_diameter}mm"),
            ("Stator\\Core", "InnerDiameter", f"{stator_inner_diameter}mm"),
            ("Stator\\Core", "Length",         f"{stack_length}mm"),
            ("Rotor\\Core",  "OuterDiameter", f"{rotor_outer_diameter}mm"),
            ("Rotor\\Core",  "InnerDiameter", f"{shaft_diameter}mm"),
            ("Rotor\\Core",  "Length",         f"{stack_length}mm"),
        ]
        for path, name, val in props_to_set:
            if _set_prop(path, name, val):
                applied += 1
            else:
                failed.append(f"{path}/{name}")

        # ── 极数 / 槽数（尝试多个可能路径）────────────────────────────
        for poles_path in ["Stator\\Winding", "General", ""]:
            if _set_prop(poles_path, "Poles", str(num_poles)):
                applied += 1
                break
        else:
            failed.append("Poles")

        for slots_path in ["Stator\\Winding", "Stator\\Core", "General", ""]:
            if _set_prop(slots_path, "Slots", str(num_slots)):
                applied += 1
                break
        else:
            failed.append("Slots")

        # ── 额定工况（尝试多个可能路径）────────────────────────────────
        rated_settings_applied = False
        rated_params = [
            ("RatedSpeed",   f"{rated_speed}rpm"),
            ("RatedVoltage", f"{rated_voltage}V"),
            ("RatedOutput",  f"{rated_power}W"),
        ]
        for rated_name, rated_val in rated_params:
            for rated_path in ["General", "Machine", ""]:
                if _set_prop(rated_path, rated_name, rated_val):
                    rated_settings_applied = True
                    break

        if applied == 0:
            return _err(
                "RMXprt 模板已创建，但关键几何/极槽参数均未成功写入；"
                "已拒绝继续使用默认模板参数伪装成用户指定设计。"
            )

        if failed:
            warnings.append(f"部分设计参数未写入成功: {', '.join(failed)}")
        if not rated_settings_applied:
            warnings.append("额定工况未成功写入，请在 RMXprt 中复核额定转速/电压/功率")

        return _ok(append_warnings({
            "design_name": design_name,
            "motor_type": motor_type,
            "applied_params": applied,
            "failed_params": failed,
            "message": (
                f"RMXprt 设计 '{design_name}' 已创建（{motor_type}）。"
                "请运行仿真设置后调用 export_to_maxwell 导出精确 FEM 模型。"
            ),
        }, warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_rmxprt_analysis - 运行 RMXprt 解析仿真
# ---------------------------------------------------------------------------

def run_rmxprt_analysis(setup_name: str = "Setup1") -> dict:
    """
    运行 RMXprt 解析法仿真，获取电机快速性能预估（效率、转矩、磁链等）。

    Args:
        setup_name: 求解设置名称，默认 "Setup1"（首次运行会自动创建）
    """
    try:
        app = _app()
        # 创建默认求解设置（若不存在）
        try:
            app.create_setup(setup_name)
        except Exception:
            pass
        app.analyze_setup(setup_name)

        # 提取关键性能指标
        results = {}
        expressions = [
            "Efficiency", "TorqueRMS", "OutputPower", "InputPower",
            "FluxLinkage_A", "d-axis_Inductance", "q-axis_Inductance",
        ]
        try:
            sol_data = app.post.get_solution_data(
                expressions=expressions,
                setup_sweep_name=f"{setup_name} : LastAdaptive",
            )
            for expr in expressions:
                try:
                    vals = sol_data.data_real(expr)
                    results[expr] = round(vals[-1], 4) if vals else None
                except Exception:
                    results[expr] = None
        except Exception:
            results["note"] = "解析结果提取失败，请在 AEDT 界面中查看"

        return _ok(results)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_to_maxwell - 将 RMXprt 设计导出到 Maxwell
# ---------------------------------------------------------------------------

def export_to_maxwell(
    setup_name: str = "Setup1",
    is_2d: bool = True,
    maxwell_design_name: str = "",
) -> dict:
    """
    将 RMXprt 初始设计导出为 Maxwell 2D/3D 精确仿真模型（自动建立几何和激励）。

    Args:
        setup_name: RMXprt 求解设置名称，默认 "Setup1"
        is_2d: True 导出 Maxwell 2D（速度快，推荐初步分析），
               False 导出 Maxwell 3D（含端部效应，精度更高）
        maxwell_design_name: Maxwell 中的设计名称；留空则自动命名
    """
    try:
        app = _app()
        # create_maxwell_design 会在同一项目中新建 Maxwell 2D/3D 设计
        maxwell_design = app.create_maxwell_design(
            setup_name=setup_name,
            maxwell_2d=is_2d,
        )
        design_name = maxwell_design_name or (
            getattr(maxwell_design, "design_name", "") or
            f"Maxwell_{'2D' if is_2d else '3D'}_Motor"
        )
        return _ok({
            "maxwell_design_name": design_name,
            "dimension": "2D" if is_2d else "3D",
            "message": (
                f"RMXprt 已导出到 Maxwell {'2D' if is_2d else '3D'}（设计='{design_name}'）。"
                "请切换到该设计后继续使用 Maxwell 工具进行精确仿真。"
            ),
        })
    except Exception as e:
        return _err(str(e))
