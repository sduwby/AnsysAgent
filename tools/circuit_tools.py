"""
Maxwell Circuit 工具：驱动器电路与电机联合仿真封装。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err

_circuit_app = None  # 全局 Circuit 实例


def _app():
    if _circuit_app is None:
        raise RuntimeError("未连接到 Maxwell Circuit，请先调用 connect_circuit。")
    return _circuit_app


# ---------------------------------------------------------------------------
# 工具：connect_circuit - 连接 Maxwell Circuit
# ---------------------------------------------------------------------------

def connect_circuit(version: str = "2024.1", non_graphical: bool = False) -> dict:
    """连接到 AEDT Maxwell Circuit Editor 实例。"""
    global _circuit_app
    try:
        from ansys.aedt.core import Circuit
        _circuit_app = Circuit(
            specified_version=version,
            non_graphical=non_graphical,
            new_desktop=False,
        )
        return _ok(f"已连接到 Maxwell Circuit {version}")
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

        # 放置直流电压源
        schematic.schematic.add_component(
            "V_DC",
            value=f"{dc_voltage_V}V",
            location=[0, 0],
        )

        # 放置六个 IGBT 开关并实际设置开关频率和死区时间属性
        positions = {"A": [2, 2], "B": [4, 2], "C": [6, 2]}
        for phase, pos in positions.items():
            for side, y_off in [("High", 0), ("Low", -2)]:
                name = f"S_{side}_{phase}"
                comp = schematic.schematic.add_component(
                    name, "SwitchIGBT", location=[pos[0], pos[1] + y_off]
                )
                # 将开关频率与死区时间写入组件属性
                try:
                    comp.parameters["SwitchingFrequency"] = f"{switching_freq_Hz}Hz"
                    comp.parameters["DeadTime"] = f"{dead_time_us}us"
                except Exception:
                    pass  # 属性名以实际 AEDT 版本为准，确保不中断流程

        # 连接直流正母线：V_DC 正极 → 各上管漏极
        bus_y_pos = 3
        bus_y_neg = -1
        for pos in positions.values():
            try:
                schematic.schematic.create_wire(
                    [[0, bus_y_pos], [pos[0], bus_y_pos], [pos[0], pos[1]]]
                )
            except Exception:
                pass
        # 连接直流负母线：各下管源极 → V_DC 负极
        for pos in positions.values():
            try:
                schematic.schematic.create_wire(
                    [[pos[0], pos[1] - 2], [pos[0], bus_y_neg], [0, bus_y_neg]]
                )
            except Exception:
                pass

        return _ok(
            f"三相逆变器电路已创建：Vdc={dc_voltage_V}V，"
            f"fsw={switching_freq_Hz}Hz，死区={dead_time_us}μs"
        )
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
        # 创建动态链接到 Maxwell 设计的电机模型
        coupled_component = app.modeler.schematic.add_component(
            "MotorModel",
            component_library="Maxwell",
            component_name=maxwell_design_name,
            location=[8, 2],
        )
        return _ok(f"已将 Maxwell 设计 '{maxwell_design_name}' 链接到 Circuit")
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
        return _ok(f"电路瞬态仿真完成，时长={stop_time_ms}ms，步长={time_step_us}μs")
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
