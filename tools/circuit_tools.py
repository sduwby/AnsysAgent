"""
Maxwell Circuit 工具：驱动器电路与电机联合仿真封装。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, append_warnings, ok_message

_circuit_app = None  # 全局 Circuit 实例


def _app():
    if _circuit_app is None:
        raise RuntimeError("未连接到 Maxwell Circuit，请先调用 connect_circuit。")
    return _circuit_app


# ---------------------------------------------------------------------------
# 工具：connect_circuit - 连接 Maxwell Circuit
# ---------------------------------------------------------------------------

def connect_circuit(version: str | None = None, non_graphical: bool = False) -> dict:
    """连接到 AEDT Maxwell Circuit Editor 实例。

    Args:
        version: AEDT 版本号，如 "2024.1"、"2025.1"；不传则自动检测当前运行版本
        non_graphical: 是否以无界面批处理模式运行
    """
    global _circuit_app
    try:
        from ansys.aedt.core import Circuit
        kwargs = {"non_graphical": non_graphical, "new_desktop": False}
        if version is not None:
            kwargs["version"] = version
        _circuit_app = Circuit(**kwargs)
        version_desc = version if version else "（自动检测）"
        return _ok(ok_message(f"已连接到 Maxwell Circuit {version_desc}", version=version))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_inverter_circuit - 创建三相逆变器电路
# ---------------------------------------------------------------------------

def create_inverter_circuit(
    dc_voltage_V: float = 400.0,
    switching_freq_Hz: float = 10000.0,
    dead_time_us: float = 1.0,
) -> dict:
    """
    在 Circuit 中创建三相两电平 IGBT 逆变器拓扑。

    Args:
        dc_voltage_V: 直流母线电压（V）
        switching_freq_Hz: 开关频率（Hz）
        dead_time_us: 死区时间（μs）
    """
    try:
        app = _app()
        schematic = app.modeler
        components = app.modeler.schematic  # NexximComponents instance
        warnings: list[str] = []
        wire_count = 0

        # 放置直流电压源（PyAEDT 0.25.x: create_voltage_dc）
        try:
            components.create_voltage_dc(
                name="V_DC",
                value=dc_voltage_V,
                location=[0, 0],
            )
        except Exception as e:
            warnings.append(f"V_DC 创建失败: {e}")

        # 放置六个 IGBT 开关（使用 create_component，从 Switches 库取 IGBT）
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
                    # 将开关频率与死区时间写入组件属性
                    try:
                        comp.parameters["SwitchingFrequency"] = f"{switching_freq_Hz}Hz"
                        comp.parameters["DeadTime"] = f"{dead_time_us}us"
                    except Exception as e:
                        warnings.append(f"{name} 参数写入失败: {e}")
                except Exception as e:
                    warnings.append(f"{name} 创建失败: {e}")

        # 连接直流正母线：V_DC 正极 → 各上管漏极
        bus_y_pos = 3
        bus_y_neg = -1
        for pos in positions.values():
            try:
                components.create_wire(
                    [[0, bus_y_pos], [pos[0], bus_y_pos], [pos[0], pos[1]]]
                )
                wire_count += 1
            except Exception as e:
                warnings.append(f"正母线布线失败 @ {pos}: {e}")
        # 连接直流负母线：各下管源极 → V_DC 负极
        for pos in positions.values():
            try:
                components.create_wire(
                    [[pos[0], pos[1] - 2], [pos[0], bus_y_neg], [0, bus_y_neg]]
                )
                wire_count += 1
            except Exception as e:
                warnings.append(f"负母线布线失败 @ {pos}: {e}")

        if wire_count == 0:
            return _err("逆变器元件已创建，但所有母线连接均失败，电路不可用")

        result = {
            "dc_voltage_V": dc_voltage_V,
            "switching_freq_Hz": switching_freq_Hz,
            "dead_time_us": dead_time_us,
            "wire_connections": wire_count,
            "message": (
                f"三相逆变器电路已创建：Vdc={dc_voltage_V}V，"
                f"fsw={switching_freq_Hz}Hz，死区={dead_time_us}μs"
            ),
        }
        return _ok(append_warnings(result, warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：link_maxwell_to_circuit - 将 Maxwell 电机链接到 Circuit
# ---------------------------------------------------------------------------

def link_maxwell_to_circuit(maxwell_design_name: str) -> dict:
    """
    将已有的 Maxwell 电机设计动态链接到当前 Circuit 设计（联仿）。

    Args:
        maxwell_design_name: Maxwell 设计名称（AEDT 中的设计名）
    """
    try:
        app = _app()
        # 创建动态链接到 Maxwell 设计的电机模型（PyAEDT 0.25.x: add_subcircuit_dynamic_link）
        try:
            coupled_component = app.modeler.schematic.add_subcircuit_dynamic_link(
                maxwell_design_name,
                location=[8, 2],
            )
        except Exception:
            # fallback: create_component with Maxwell library
            coupled_component = app.modeler.schematic.create_component(
                name="MotorModel",
                component_library="Maxwell",
                component_name=maxwell_design_name,
                location=[8, 2],
            )
        return _ok(ok_message(
            f"已将 Maxwell 设计 '{maxwell_design_name}' 链接到 Circuit",
            maxwell_design_name=maxwell_design_name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_circuit_simulation - 运行电路瞬态仿真
# ---------------------------------------------------------------------------

def run_circuit_simulation(
    stop_time_ms: float = 10.0,
    time_step_us: float = 10.0,
) -> dict:
    """
    运行驱动器+电机联合瞬态仿真。

    Args:
        stop_time_ms: 仿真总时间（ms）
        time_step_us: 时间步（μs）
    """
    try:
        app = _app()
        setup = app.create_setup("TransientSetup")
        setup.props["TransientData"] = [
            ["StopTime", f"{stop_time_ms}ms"],
            ["TimeStep", f"{time_step_us}us"],
        ]
        setup.update()
        app.analyze_setup("TransientSetup")
        return _ok(ok_message(
            f"电路瞬态仿真完成，时长={stop_time_ms}ms，步长={time_step_us}μs",
            stop_time_ms=stop_time_ms,
            time_step_us=time_step_us,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_circuit_results - 获取电路仿真结果
# ---------------------------------------------------------------------------

def get_circuit_results(signals: list[str] | None = None) -> dict:
    """
    提取电路仿真波形数据（电流、电压等）。

    Args:
        signals: 信号名称列表，如 ["I(PhaseA)", "V(DC_Bus)"]，None 则提取所有
    """
    try:
        app = _app()
        if signals is None:
            signals = ["I(PhaseA)", "I(PhaseB)", "I(PhaseC)", "V(DC_Bus)"]

        results = {}
        for sig in signals:
            try:
                data = app.post.get_solution_data(sig, "TransientSetup : Transient")
                times = data.primary_sweep_values
                values = data.data_real(sig)
                results[sig] = {
                    "time_s": list(times),
                    "values": list(values),
                    "peak": round(max(abs(v) for v in values), 4) if values else None,
                }
            except Exception:
                results[sig] = {"error": "无法获取该信号"}

        return _ok(results)
    except Exception as e:
        return _err(str(e))
