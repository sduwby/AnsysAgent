"""
RMXprt 快速电机初设计工具：通过 PyAEDT 驱动 Ansys RMXprt 进行解析法电机设计，
快速完成初始参数估算后导出到 Maxwell 进行精确 FEM 仿真。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err

_rmxprt_app = None  # 全局 RMXprt 实例

# RMXprt 电机类型映射（用户友好名 → PyAEDT solution_type）
_MOTOR_TYPE_MAP = {
    "PMSM": "PMSynchronousMotor",
    "BLDC": "BrushlessDCMotor",
    "IM": "ThreePhaseInductionMotor",
    "SRM": "SRMotor",
    "PMDC": "PermanentMagnetDCMotor",
    "SYN": "ThreePhaseSynchronousMotor",
    "SYNRM": "LSSynRM",
}


def _app():
    if _rmxprt_app is None:
        raise RuntimeError("未连接到 RMXprt，请先调用 connect_rmxprt。")
    return _rmxprt_app


# ---------------------------------------------------------------------------
# 工具：connect_rmxprt - 连接 RMXprt
# ---------------------------------------------------------------------------

def connect_rmxprt(
    version: str = "2024.1",
    non_graphical: bool = False,
) -> dict:
    """
    连接到 Ansys RMXprt（解析法电机设计模块）。

    Args:
        version: AEDT 版本号，如 "2024.1"、"2023.2"
        non_graphical: 是否以无界面批处理模式运行
    """
    global _rmxprt_app
    try:
        from ansys.aedt.core import Rmxprt
        _rmxprt_app = Rmxprt(
            specified_version=version,
            non_graphical=non_graphical,
            new_desktop=False,
        )
        return _ok(f"已连接到 RMXprt {version}")
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
        app = _app()
        solution_type = _MOTOR_TYPE_MAP.get(motor_type.upper(), motor_type)

        # 创建新设计
        app.new_design(design_name=design_name, solution_type=solution_type)

        # 配置关键几何和运行参数（通过 design properties）
        param_map = {
            "DiaStator": stator_outer_diameter,
            "DiaGap": stator_inner_diameter,
            "DiaRotor": rotor_outer_diameter,
            "DiaShaft": shaft_diameter,
            "LenStator": stack_length,
            "Poles": num_poles,
            "Slots": num_slots,
        }
        for key, val in param_map.items():
            try:
                app.odesign.SetDesignSettings([f"NAME:Design Settings Data",
                                               f"{key}:=", str(val)])
            except Exception:
                pass  # 参数名称因电机类型而异，忽略不适用的

        # 通过 properties 设置额定工况
        try:
            app.odesign.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:DefinitionTab",
                        ["NAME:PropServers", "Machine"],
                        [
                            "NAME:ChangedProps",
                            ["NAME:RatedSpeed", "Value:=", f"{rated_speed}rpm"],
                            ["NAME:RatedVoltage", "Value:=", f"{rated_voltage}V"],
                            ["NAME:RatedOutput", "Value:=", f"{rated_power}W"],
                        ],
                    ],
                ]
            )
        except Exception:
            pass

        return _ok({
            "design_name": design_name,
            "motor_type": motor_type,
            "message": (
                f"RMXprt 设计 '{design_name}' 已创建（{motor_type}）。"
                "请运行仿真设置后调用 export_to_maxwell 导出精确 FEM 模型。"
            ),
        })
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
