"""
Motor-CAD 工具：通过 PyMotorCAD 驱动 Ansys Motor-CAD 进行电机解析法初设计。
覆盖电磁、热网络、NVH 三个分析模块，与 Maxwell FEM 形成"解析初设计 → 精确仿真"工作流。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err

_mcad_app = None  # 全局 Motor-CAD 实例


def _app():
    """返回当前激活的 Motor-CAD 实例，未连接时抛出异常。"""
    if _mcad_app is None:
        raise RuntimeError("未连接到 Motor-CAD，请先调用 connect_motorcad。")
    return _mcad_app


# ---------------------------------------------------------------------------
# 工具：connect_motorcad - 连接 Motor-CAD
# ---------------------------------------------------------------------------

def connect_motorcad(port: int = 0) -> dict:
    """
    连接到运行中的 Motor-CAD 实例（或自动启动新实例）。

    Args:
        port: Motor-CAD RPC 端口号；0 表示自动查找空闲端口（推荐）。
    """
    global _mcad_app
    try:
        import ansys.motorcad.core as mcad
        _mcad_app = mcad.MotorCAD(port=port if port else None, reuse_parallel_instances=False)
        _mcad_app.set_variable("MessageDisplayState", 2)  # 静默模式，减少弹窗
        version = _mcad_app.get_variable("SoftwareVersion")
        return _ok(f"已连接到 Motor-CAD（版本：{version}，端口：{port or '自动'}）")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：set_motorcad_geometry - 设置电机几何参数
# ---------------------------------------------------------------------------

def set_motorcad_geometry(
    stator_outer_diam: float,
    stator_inner_diam: float,
    rotor_outer_diam: float,
    shaft_diam: float,
    stack_length: float,
    num_poles: int,
    num_slots: int,
    motor_type: str = "PMSM",
) -> dict:
    """
    在 Motor-CAD 中设置电机几何参数，适用于 PMSM / BLDC / IM 等类型。

    Args:
        stator_outer_diam: 定子外径（mm）
        stator_inner_diam: 定子内径（mm）
        rotor_outer_diam: 转子外径（mm）
        shaft_diam: 转轴直径（mm）
        stack_length: 轴向叠片长度（mm）
        num_poles: 极数（必须为偶数）
        num_slots: 定子槽数
        motor_type: 电机类型，"PMSM" / "BLDC" / "IM"，影响结构模板选择
    """
    try:
        app = _app()
        # 基本几何参数
        app.set_variable("Stator_Lam_Dia", stator_outer_diam)
        app.set_variable("Stator_Bore", stator_inner_diam)
        app.set_variable("Rotor_Lam_Dia", rotor_outer_diam)
        app.set_variable("Shaft_Dia", shaft_diam)
        app.set_variable("Stator_Lam_Length", stack_length)
        app.set_variable("Pole_Number", num_poles)
        app.set_variable("Slot_Number", num_slots)

        # 根据电机类型切换 Motor-CAD 内置拓扑
        _type_map = {
            "PMSM": "SurfaceInset",   # 表贴/内嵌 PMSM
            "BLDC": "SurfaceInset",
            "IM": "SquirrelCage",
        }
        topology = _type_map.get(motor_type.upper(), "SurfaceInset")
        try:
            app.set_variable("MachineType", topology)
        except Exception:
            pass  # 部分版本字段名不同，忽略

        return _ok({
            "motor_type": motor_type,
            "stator_outer_diam_mm": stator_outer_diam,
            "stator_inner_diam_mm": stator_inner_diam,
            "rotor_outer_diam_mm": rotor_outer_diam,
            "stack_length_mm": stack_length,
            "num_poles": num_poles,
            "num_slots": num_slots,
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_motorcad_em_analysis - 运行电磁解析仿真
# ---------------------------------------------------------------------------

def run_motorcad_em_analysis(
    rated_speed_rpm: float = 3000.0,
    rated_current_A: float = 10.0,
    current_angle_deg: float = 45.0,
) -> dict:
    """
    在 Motor-CAD 中运行电磁（Emag）解析仿真，获取额定工况性能指标。

    Args:
        rated_speed_rpm: 额定转速（rpm）
        rated_current_A: 相电流峰值（A）
        current_angle_deg: 电流角（度），用于电流超前控制优化
    """
    try:
        app = _app()
        app.set_variable("RotationSpeed", rated_speed_rpm)
        app.set_variable("PhaseCurrentAmplitude", rated_current_A)
        app.set_variable("CurrentAngle", current_angle_deg)

        # 运行电磁仿真（Motor-CAD Lab 或 Emag 模块）
        app.do_emag_calculation()

        # 提取关键电磁性能指标
        results = {}
        em_vars = [
            ("Shaft_Torque", "shaft_torque_Nm"),
            ("Efficiency", "efficiency_pct"),
            ("Output_Power", "output_power_W"),
            ("Input_Power", "input_power_W"),
            ("Copper_Loss_Total", "copper_loss_W"),
            ("Iron_Loss_Total", "iron_loss_W"),
            ("BackEMF_Peak", "back_emf_peak_V"),
            ("Torque_Ripple_Factor", "torque_ripple_pct"),
        ]
        for mcad_var, result_key in em_vars:
            try:
                val = app.get_variable(mcad_var)
                results[result_key] = round(float(val), 4) if val is not None else None
            except Exception:
                results[result_key] = None

        return _ok(results)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_motorcad_thermal_analysis - 运行热网络仿真
# ---------------------------------------------------------------------------

def run_motorcad_thermal_analysis(
    cooling_type: str = "TEFC",
    ambient_temp_C: float = 25.0,
    coolant_flow_rate: float = 0.0,
) -> dict:
    """
    在 Motor-CAD 中运行热网络（Thermal）分析，评估各部件温升。

    Args:
        cooling_type: 冷却方式，"TEFC"（自冷）/ "WJ"（水套）/ "OilSpray"（喷油）
        ambient_temp_C: 环境温度（°C）
        coolant_flow_rate: 冷却液流量（L/min），水套冷却时有效
    """
    try:
        app = _app()
        app.set_variable("Ambient_Temperature", ambient_temp_C)

        # 冷却配置
        cooling_map = {"TEFC": 0, "WJ": 1, "OilSpray": 2, "WaterJacket": 1}
        cooling_code = cooling_map.get(cooling_type, 0)
        try:
            app.set_variable("Cooling_Type", cooling_code)
            if coolant_flow_rate > 0:
                app.set_variable("WJ_Fluid_FlowRate", coolant_flow_rate)
        except Exception:
            pass

        app.do_steady_state_calculation()

        # 提取温升结果
        results = {"ambient_temp_C": ambient_temp_C, "cooling_type": cooling_type}
        thermal_vars = [
            ("T_Winding_Average", "winding_avg_temp_C"),
            ("T_Winding_Max", "winding_max_temp_C"),
            ("T_Stator_Average", "stator_avg_temp_C"),
            ("T_Magnet_Average", "magnet_avg_temp_C"),
            ("T_Rotor_Average", "rotor_avg_temp_C"),
            ("T_Bearing_DE", "bearing_de_temp_C"),
        ]
        for mcad_var, result_key in thermal_vars:
            try:
                val = app.get_variable(mcad_var)
                results[result_key] = round(float(val), 2) if val is not None else None
            except Exception:
                results[result_key] = None

        return _ok(results)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_motorcad_nvh_analysis - 运行 NVH 振动噪声分析
# ---------------------------------------------------------------------------

def run_motorcad_nvh_analysis(
    speed_rpm: float = 3000.0,
    freq_max_Hz: float = 5000.0,
) -> dict:
    """
    在 Motor-CAD 中运行 NVH（噪声、振动与声振粗糙度）分析，预测电磁激励力和振动模态。

    Args:
        speed_rpm: 分析转速（rpm）
        freq_max_Hz: 最高分析频率（Hz）
    """
    try:
        app = _app()
        app.set_variable("RotationSpeed", speed_rpm)

        try:
            app.set_variable("NVH_FreqMax", freq_max_Hz)
        except Exception:
            pass

        app.do_emag_calculation()  # NVH 依赖电磁力波数据，需先运行电磁

        results = {"speed_rpm": speed_rpm, "freq_max_Hz": freq_max_Hz}
        nvh_vars = [
            ("RadialForce_Max", "max_radial_force_N_per_m2"),
            ("Cogging_Torque_Peak", "cogging_torque_peak_Nm"),
            ("Torque_Ripple_Factor", "torque_ripple_pct"),
        ]
        for mcad_var, result_key in nvh_vars:
            try:
                val = app.get_variable(mcad_var)
                results[result_key] = round(float(val), 4) if val is not None else None
            except Exception:
                results[result_key] = None

        # 提取主要力波次数
        try:
            dominant_order = app.get_variable("DominantForceOrder")
            results["dominant_force_order"] = int(dominant_order) if dominant_order else None
        except Exception:
            results["dominant_force_order"] = None

        return _ok(results)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_motorcad_performance_map - 获取效率 MAP
# ---------------------------------------------------------------------------

def get_motorcad_performance_map(
    speed_points: int = 10,
    torque_points: int = 10,
    max_speed_rpm: float = 6000.0,
    max_torque_Nm: float = 50.0,
) -> dict:
    """
    在 Motor-CAD Lab 模块中计算电机全工况效率 MAP，返回转速-转矩-效率三维数据表。

    Args:
        speed_points: 转速扫描点数（均匀分布）
        torque_points: 转矩扫描点数（均匀分布）
        max_speed_rpm: 最高转速（rpm）
        max_torque_Nm: 最大转矩（Nm）
    """
    try:
        app = _app()
        # 配置 Lab 扫描范围
        try:
            app.set_variable("MaxSpeed", max_speed_rpm)
            app.set_variable("MaxTorque", max_torque_Nm)
            app.set_variable("SpeedPointCount", speed_points)
            app.set_variable("TorquePointCount", torque_points)
        except Exception:
            pass

        app.calculate_operating_point_graph()  # Lab 效率 MAP 计算

        # 尝试提取效率 MAP 数据
        eff_map = []
        try:
            for i in range(speed_points):
                for j in range(torque_points):
                    speed = app.get_array_variable("SpeedArray", i)
                    torque = app.get_array_variable("TorqueArray", j)
                    eff = app.get_array_variable("EfficiencyArray", i * torque_points + j)
                    if speed is not None and torque is not None and eff is not None:
                        eff_map.append({
                            "speed_rpm": round(float(speed), 1),
                            "torque_Nm": round(float(torque), 2),
                            "efficiency_pct": round(float(eff), 2),
                        })
        except Exception:
            pass  # 若 API 不支持数组提取直接返回空列表

        best = max(eff_map, key=lambda x: x["efficiency_pct"]) if eff_map else None
        return _ok({
            "num_points": len(eff_map),
            "peak_efficiency": best,
            "efficiency_map": eff_map,
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_motorcad_to_maxwell - 将 Motor-CAD 设计导出到 Maxwell FEM
# ---------------------------------------------------------------------------

def export_motorcad_to_maxwell(
    output_dir: str = "",
    is_2d: bool = True,
) -> dict:
    """
    将 Motor-CAD 当前设计导出为 Maxwell 2D/3D FEM 模型，实现"解析初设计 → FEM 精算"工作流。

    Args:
        output_dir: 输出目录路径；为空时使用 Motor-CAD 默认输出目录
        is_2d: True 导出 Maxwell 2D（速度快），False 导出 Maxwell 3D（含端部效应）
    """
    try:
        app = _app()
        dim = "2D" if is_2d else "3D"
        try:
            if is_2d:
                app.create_model(f"Maxwell2D{dim}")
            else:
                app.create_model(f"Maxwell3D{dim}")
        except AttributeError:
            # 旧版 API
            app.do_maxwell_setup()

        return _ok({
            "dimension": dim,
            "output_dir": output_dir or "Motor-CAD 默认目录",
            "message": (
                f"Motor-CAD 设计已导出为 Maxwell {dim} 模型。"
                "请在 AEDT 中打开导出项目，使用 Maxwell 工具继续精确仿真。"
            ),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：disconnect_motorcad - 断开 Motor-CAD 连接
# ---------------------------------------------------------------------------

def disconnect_motorcad() -> dict:
    """断开与 Motor-CAD 的连接，释放许可证。"""
    global _mcad_app
    try:
        if _mcad_app is not None:
            _mcad_app.quit()
            _mcad_app = None
        return _ok("Motor-CAD 连接已断开")
    except Exception as e:
        return _err(str(e))
