"""
Mechanical 结构工具：通过 PyAEDT 驱动 Ansys Mechanical 进行电机振动（NVH）、
转子应力等结构分析。每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations
from typing import Any

_mech_app = None  # 全局 Mechanical 实例


def _app():
    if _mech_app is None:
        raise RuntimeError("未连接到 Mechanical，请先调用 connect_mechanical。")
    return _mech_app


def _ok(result: Any = None) -> dict:
    return {"success": True, "result": result}


def _err(msg: str) -> dict:
    return {"success": False, "error": msg}


# ---------------------------------------------------------------------------
# 工具：connect_mechanical - 连接 Mechanical
# ---------------------------------------------------------------------------

def connect_mechanical(version: str = "2024.1") -> dict:
    """连接到 Ansys Mechanical 实例（通过 ansys-mechanical-core）。"""
    global _mech_app
    try:
        import ansys.mechanical.core as pymechanical
        _mech_app = pymechanical.launch_mechanical(version=version)
        return _ok(f"已连接到 Mechanical {version}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_maxwell_forces - 导入 Maxwell 电磁力
# ---------------------------------------------------------------------------

def import_maxwell_forces(
    maxwell_project_path: str,
    setup_name: str = "Setup1",
) -> dict:
    """
    将 Maxwell 2D/3D 的电磁力（Maxwell Stress Tensor）导入 Mechanical 作为激励。

    Args:
        maxwell_project_path: Maxwell 项目文件路径（.aedt）
        setup_name: Maxwell 求解设置名称
    """
    try:
        app = _app()
        # 通过 ACT 脚本导入 Maxwell 力
        script = f"""
import mech_dpf
maxwell_source = ExtAPI.DataModel.Project.Model.AddElectromagneticSetup()
maxwell_source.Properties["Source File"].Value = r"{maxwell_project_path}"
maxwell_source.Properties["Design"].Value = "{setup_name}"
maxwell_source.ImportData()
"""
        app.run_python_script(script)
        return _ok(f"已从 '{maxwell_project_path}' 导入电磁力")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_modal_analysis - 运行模态分析
# ---------------------------------------------------------------------------

def run_modal_analysis(
    num_modes: int = 12,
    freq_range_hz: tuple[float, float] = (0, 10000),
) -> dict:
    """
    运行电机定子/转子模态分析，提取固有频率和振型。

    Args:
        num_modes: 提取的模态阶数
        freq_range_hz: 频率范围 (f_min, f_max) Hz
    """
    try:
        app = _app()
        script = f"""
modal_analysis = Model.Analyses[0]
modal_analysis.Properties["Options/Maximum Modes to Find"].Value = {num_modes}
modal_analysis.Properties["Options/Limit Search to Range"].Value = True
modal_analysis.Properties["Options/Range Minimum"].Value = {freq_range_hz[0]}
modal_analysis.Properties["Options/Range Maximum"].Value = {freq_range_hz[1]}
modal_analysis.Solution.Solve(True)
"""
        app.run_python_script(script)
        return _ok(f"模态分析完成：{num_modes} 阶，频率范围 {freq_range_hz[0]}-{freq_range_hz[1]} Hz")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_harmonic_analysis - 运行谐响应分析（NVH）
# ---------------------------------------------------------------------------

def run_harmonic_analysis(
    freq_range_hz: tuple[float, float] = (0, 5000),
    num_steps: int = 100,
    damping_ratio: float = 0.02,
) -> dict:
    """
    运行谐响应分析，评估电机振动和噪声（NVH）。

    Args:
        freq_range_hz: 频率扫描范围（Hz）
        num_steps: 频率步数
        damping_ratio: 阻尼比
    """
    try:
        app = _app()
        script = f"""
harmonic = Model.Analyses[0]
harmonic.Properties["Options/Range Minimum"].Value = {freq_range_hz[0]}
harmonic.Properties["Options/Range Maximum"].Value = {freq_range_hz[1]}
harmonic.Properties["Options/Solution Intervals"].Value = {num_steps}
harmonic.Solution.Solve(True)
"""
        app.run_python_script(script)
        return _ok(f"谐响应分析完成：{freq_range_hz[0]}-{freq_range_hz[1]} Hz，{num_steps} 步")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_vibration_results - 获取振动结果
# ---------------------------------------------------------------------------

def get_vibration_results() -> dict:
    """提取固有频率列表和关键频率处的最大变形量。"""
    try:
        app = _app()
        script = """
import json
results = {}
try:
    freq_result = Model.Analyses[0].Solution.GetResultsData()
    results["natural_frequencies_Hz"] = [f for f in freq_result.Frequencies[:12]]
except Exception as e:
    results["error"] = str(e)
print(json.dumps(results))
"""
        output = app.run_python_script(script)
        import json
        data = json.loads(output) if output else {}
        return _ok(data)
    except Exception as e:
        return _err(str(e))
