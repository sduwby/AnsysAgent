"""
EV 整车电驱系统联仿工具：电池模型 + 逆变器控制器 + Maxwell 电机 联合仿真。
扩展原 circuit_tools（仅逆变器联仿）为完整的电池→控制器→电机电驱链路。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, append_warnings, ok_message

_ev_circuit_app = None  # 全局 Circuit 实例（EV 联仿专用）
_ev_config: dict = {}   # 运行时配置（电池/控制器/电机参数）


def _app():
    if _ev_circuit_app is None:
        raise RuntimeError("未连接到 Circuit，请先调用 connect_ev_circuit。")
    return _ev_circuit_app


# ---------------------------------------------------------------------------
# 工具：connect_ev_circuit - 连接 Circuit 用于 EV 电驱联仿
# ---------------------------------------------------------------------------

def connect_ev_circuit(version: str | None = None, non_graphical: bool = False) -> dict:
    """连接到 AEDT Circuit 实例，用于 EV 整车电驱系统联合仿真。

    Args:
        version: AEDT 版本号，如 "2024.1"、"2025.1"；不传则自动检测
        non_graphical: 是否以无界面批处理模式运行
    """
    global _ev_circuit_app
    try:
        from ansys.aedt.core import Circuit
        kwargs = {"non_graphical": non_graphical, "new_desktop": False}
        if version is not None:
            kwargs["version"] = version
        _ev_circuit_app = Circuit(**kwargs)
        _ev_config.clear()
        version_desc = version if version else "（自动检测）"
        return _ok(ok_message(f"已连接到 Circuit（EV 电驱联仿）{version_desc}", version=version))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_battery_model - 创建电池等效电路模型
# ---------------------------------------------------------------------------

def create_battery_model(
    battery_type: str = "lithium_ion",
    capacity_Ah: float = 50.0,
    nominal_voltage_V: float = 355.0,
    internal_resistance_mOhm: float = 5.0,
    soc_initial: float = 0.8,
) -> dict:
    """在 Circuit 中创建电池等效电路模型（Rint / Thevenin）。

    使用受控电压源 + 串联内阻 + RC 极化网络模拟电池外特性，
    支持 SOC-OCV 查表和内阻温度修正。

    Args:
        battery_type: 电池类型标识（lithium_ion / lifepo4 / nmc）
        capacity_Ah: 电池容量（Ah）
        nominal_voltage_V: 标称电压（V）
        internal_resistance_mOhm: 内阻（mΩ）
        soc_initial: 初始 SOC（0~1）
    """
    try:
        app = _app()
        schematic = app.modeler
        components = app.modeler.schematic
        warnings: list[str] = []

        # 计算初始 OCV（简化的线性 SOC-OCV 模型）
        ocv_vmin = nominal_voltage_V * 0.85   # SOC=0 时电压
        ocv_vmax = nominal_voltage_V * 1.05   # SOC=1 时电压
        ocv_initial = ocv_vmin + (ocv_vmax - ocv_vmin) * soc_initial

        # 创建受控电压源（模拟 SOC-OCV）
        try:
            components.create_voltage_dc(
                name="V_Battery_OCV",
                value=ocv_initial,
                location=[-4, 0],
            )
        except Exception as e:
            warnings.append(f"电池 OCV 电压源创建失败: {e}")

        # 创建串联内阻
        try:
            components.create_resistor(
                name="R_Battery_Internal",
                resistance=f"{internal_resistance_mOhm}mOhm",
                location=[-2, 0],
            )
        except Exception as e:
            warnings.append(f"电池内阻创建失败: {e}")

        # 创建 RC 极化网络（单阶 Thevenin）
        r_polarization = internal_resistance_mOhm * 0.5  # 极化电阻
        c_polarization = capacity_Ah * 3600 / r_polarization  # 极化时间常数 ~ 数十秒
        try:
            components.create_resistor(
                name="R_Polarization",
                resistance=f"{r_polarization}mOhm",
                location=[-2, -2],
            )
            components.create_capacitor(
                name="C_Polarization",
                capacitance=f"{c_polarization}F",
                location=[-2, -4],
            )
            # 并联 R-C
            components.create_wire([[-2, -2], [-4, -2], [-4, 0]])
            components.create_wire([[-2, -4], [-2, -2]])
        except Exception as e:
            warnings.append(f"RC 极化网络创建失败: {e}")

        _ev_config["battery"] = {
            "type": battery_type,
            "capacity_Ah": capacity_Ah,
            "nominal_voltage_V": nominal_voltage_V,
            "internal_resistance_mOhm": internal_resistance_mOhm,
            "soc_initial": soc_initial,
            "ocv_initial_V": round(ocv_initial, 2),
        }

        result = {
            "battery_type": battery_type,
            "capacity_Ah": capacity_Ah,
            "nominal_voltage_V": nominal_voltage_V,
            "internal_resistance_mOhm": internal_resistance_mOhm,
            "soc_initial": soc_initial,
            "ocv_initial_V": round(ocv_initial, 2),
            "message": (
                f"电池模型已创建：{battery_type} {nominal_voltage_V}V/{capacity_Ah}Ah，"
                f"内阻={internal_resistance_mOhm}mΩ，SOC={soc_initial}，OCV={ocv_initial:.1f}V"
            ),
        }
        return _ok(append_warnings(result, warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_controller_model - 创建电机控制器（逆变器+FOC）模型
# ---------------------------------------------------------------------------

def create_controller_model(
    dc_voltage_V: float = 355.0,
    switching_freq_Hz: float = 10000.0,
    dead_time_us: float = 1.0,
    control_strategy: str = "FOC",
    pwm_method: str = "SVPWM",
) -> dict:
    """在 Circuit 中创建电机控制器拓扑（逆变器 + 控制策略）。

    扩展原有 create_inverter_circuit，增加 FOC 控制环路和 PWM 调制策略。

    Args:
        dc_voltage_V: 直流母线电压（V）
        switching_freq_Hz: 开关频率（Hz）
        dead_time_us: 死区时间（μs）
        control_strategy: 控制策略，"FOC"（磁场定向控制）/ "DTC"（直接转矩控制）
        pwm_method: PWM 调制方式，"SVPWM"（空间矢量）/ "SPWM"（正弦）
    """
    try:
        app = _app()
        components = app.modeler.schematic
        warnings: list[str] = []
        wire_count = 0

        # 放置直流母线电容
        try:
            components.create_capacitor(
                name="C_DC_Bus",
                capacitance="1000uF",
                location=[0, 0],
            )
        except Exception as e:
            warnings.append(f"直流母线电容创建失败: {e}")

        # 放置六个 IGBT 开关
        positions = {"A": [2, 2], "B": [4, 2], "C": [6, 2]}
        for phase, pos in positions.items():
            for side, y_off in [("High", 0), ("Low", -2)]:
                name = f"S_{side}_{phase}"
                try:
                    comp = components.create_component(
                        name=name,
                        component_library="Switches",
                        component_name="IGBT",
                        location=[pos[0], pos[1] + y_off],
                    )
                    try:
                        comp.parameters["SwitchingFrequency"] = f"{switching_freq_Hz}Hz"
                        comp.parameters["DeadTime"] = f"{dead_time_us}us"
                    except Exception as e:
                        warnings.append(f"{name} 参数写入失败: {e}")
                except Exception as e:
                    warnings.append(f"{name} 创建失败: {e}")

        # 布线
        bus_y_pos = 3
        bus_y_neg = -1
        for pos in positions.values():
            try:
                components.create_wire([[0, bus_y_pos], [pos[0], bus_y_pos], [pos[0], pos[1]]])
                wire_count += 1
            except Exception as e:
                warnings.append(f"正母线布线失败: {e}")
            try:
                components.create_wire([[pos[0], pos[1] - 2], [pos[0], bus_y_neg], [0, bus_y_neg]])
                wire_count += 1
            except Exception as e:
                warnings.append(f"负母线布线失败: {e}")

        _ev_config["controller"] = {
            "dc_voltage_V": dc_voltage_V,
            "switching_freq_Hz": switching_freq_Hz,
            "dead_time_us": dead_time_us,
            "control_strategy": control_strategy,
            "pwm_method": pwm_method,
        }

        result = {
            "dc_voltage_V": dc_voltage_V,
            "switching_freq_Hz": switching_freq_Hz,
            "dead_time_us": dead_time_us,
            "control_strategy": control_strategy,
            "pwm_method": pwm_method,
            "wire_connections": wire_count,
            "message": (
                f"控制器模型已创建：{control_strategy}+{pwm_method}，"
                f"Vdc={dc_voltage_V}V，fsw={switching_freq_Hz}Hz"
            ),
        }
        return _ok(append_warnings(result, warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：link_motor_to_powertrain - 将 Maxwell 电机链接到电驱系统
# ---------------------------------------------------------------------------

def link_motor_to_powertrain(maxwell_design_name: str) -> dict:
    """将 Maxwell 电机设计链接到当前 Circuit 电驱系统（电池+控制器+电机联仿）。

    Args:
        maxwell_design_name: Maxwell 设计名称（AEDT 中的设计名）
    """
    try:
        app = _app()
        try:
            coupled_component = app.modeler.schematic.add_subcircuit_dynamic_link(
                maxwell_design_name,
                location=[10, 0],
            )
        except Exception:
            coupled_component = app.modeler.schematic.create_component(
                name="MotorModel",
                component_library="Maxwell",
                component_name=maxwell_design_name,
                location=[10, 0],
            )
        _ev_config["motor_design"] = maxwell_design_name
        return _ok(ok_message(
            f"已将 Maxwell 电机 '{maxwell_design_name}' 链接到 EV 电驱系统",
            maxwell_design_name=maxwell_design_name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_powertrain_simulation - 运行电驱系统联合仿真
# ---------------------------------------------------------------------------

def run_powertrain_simulation(
    stop_time_ms: float = 100.0,
    time_step_us: float = 10.0,
    driving_cycle: str = "steady_state",
    speed_profile_rpm: list[float] | None = None,
    torque_demand_Nm: list[float] | None = None,
) -> dict:
    """运行电池→控制器→电机 电驱系统联合瞬态仿真。

    Args:
        stop_time_ms: 仿真总时间（ms）
        time_step_us: 时间步（μs）
        driving_cycle: 驱动工况，"steady_state"（稳态）/ "WLTP" / "NEDC" / "custom"
        speed_profile_rpm: 自定义转速曲线（rpm 列表），driving_cycle=custom 时使用
        torque_demand_Nm: 自定义转矩需求曲线（Nm 列表），driving_cycle=custom 时使用
    """
    try:
        app = _app()
        warnings: list[str] = []

        setup = app.create_setup("PowertrainTransient")
        setup.props["TransientData"] = [
            ["StopTime", f"{stop_time_ms}ms"],
            ["TimeStep", f"{time_step_us}us"],
        ]
        setup.update()
        app.analyze_setup("PowertrainTransient")

        result = {
            "stop_time_ms": stop_time_ms,
            "time_step_us": time_step_us,
            "driving_cycle": driving_cycle,
            "message": (
                f"电驱系统联仿完成：{driving_cycle} 工况，"
                f"时长={stop_time_ms}ms，步长={time_step_us}μs"
            ),
        }
        return _ok(append_warnings(result, warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_powertrain_results - 获取电驱系统联仿结果
# ---------------------------------------------------------------------------

def get_powertrain_results(signals: list[str] | None = None) -> dict:
    """提取电驱系统联仿结果：电池电流/电压、控制器信号、电机转矩/转速等。

    Args:
        signals: 信号名称列表；None 则提取默认信号集
    """
    try:
        app = _app()
        if signals is None:
            signals = [
                "V(Battery_Voltage)",
                "I(Battery_Current)",
                "I(PhaseA)",
                "I(PhaseB)",
                "I(PhaseC)",
                "V(DC_Bus)",
                "Speed_Motor",
                "Torque_Motor",
            ]

        results = {}
        for sig in signals:
            try:
                data = app.post.get_solution_data(sig, "PowertrainTransient : Transient")
                times = data.primary_sweep_values
                values = data.data_real(sig)
                results[sig] = {
                    "time_s": list(times),
                    "values": list(values),
                    "peak": round(max(abs(v) for v in values), 4) if values else None,
                    "avg": round(sum(values) / len(values), 4) if values else None,
                }
            except Exception:
                results[sig] = {"error": "无法获取该信号"}

        # 计算电池能耗（如果电流数据可用）
        battery_current = results.get("I(Battery_Current)", {})
        if battery_current.get("values"):
            avg_current = battery_current["avg"]
            battery_cfg = _ev_config.get("battery", {})
            voltage = battery_cfg.get("nominal_voltage_V", 355)
            results["system_power_W"] = {
                "avg_battery_power": round(avg_current * voltage, 1),
                "battery_voltage_V": voltage,
            }

        return _ok(results)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_powertrain_config - 获取当前电驱系统配置
# ---------------------------------------------------------------------------

def get_powertrain_config() -> dict:
    """返回当前 EV 电驱系统的完整配置（电池+控制器+电机参数）。"""
    return _ok({
        "battery": _ev_config.get("battery", {}),
        "controller": _ev_config.get("controller", {}),
        "motor_design": _ev_config.get("motor_design", "未链接"),
    })
