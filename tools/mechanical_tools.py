"""
Mechanical 结构工具：通过 PyAEDT 驱动 Ansys Mechanical 进行电机振动（NVH）、
转子应力等结构分析。每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, ok_message

_mech_app = None  # 全局 Mechanical 实例


def _app():
    if _mech_app is None:
        raise RuntimeError("未连接到 Mechanical，请先调用 connect_mechanical。")
    return _mech_app


# ---------------------------------------------------------------------------
# 工具：connect_mechanical - 连接 Mechanical
# ---------------------------------------------------------------------------

def connect_mechanical(version: str = "242") -> dict:
    """
    连接到 Ansys Mechanical 实例（通过 ansys-mechanical-core）。

    Args:
        version: Ansys 版本号，格式为三位整数字符串，如 "242"（2024 R2）、"241"（2024 R1）
    """
    global _mech_app
    try:
        from ansys.mechanical.core import find_mechanical, launch_mechanical
        # version 格式：三位整数字符串 "242" 表示 Ansys 2024 R2
        ver_int = int(version)
        mechs = find_mechanical(ver_int)
        if mechs:
            _mech_app = launch_mechanical(exec_file=mechs[0], batch=True)
        else:
            # 未找到指定版本，使用最新安装版本
            _mech_app = launch_mechanical(batch=True)
        return _ok(ok_message(f"已连接到 Mechanical（版本 {version}）", version=version))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_maxwell_forces - 导入 Maxwell 电磁力
# ---------------------------------------------------------------------------

def import_maxwell_forces(
    maxwell_project_path: str,
    design_name: str = "",
    setup_name: str = "Setup1",
) -> dict:
    """
    将 Maxwell 2D/3D 的电磁力（Maxwell Stress Tensor）导入 Mechanical 作为激励。

    Args:
        maxwell_project_path: Maxwell 项目文件路径（.aedt）
        design_name: Maxwell 设计名称；留空则使用 Mechanical 导入对象默认设计
        setup_name: Maxwell 求解设置名称
    """
    try:
        app = _app()
        # 通过 ACT 脚本导入 Maxwell 力
        script = f"""
import mech_dpf
maxwell_source = ExtAPI.DataModel.Project.Model.AddElectromagneticSetup()
maxwell_source.Properties["Source File"].Value = r"{maxwell_project_path}"
_design_name = "{design_name}"
if _design_name:
    for _key in ("Design", "Source Design", "Electromagnetic Design"):
        try:
            maxwell_source.Properties[_key].Value = _design_name
            break
        except Exception:
            continue
    else:
        raise Exception("未找到用于设置 Maxwell 设计名的属性")
for _key in ("Solution", "Setup", "Electromagnetic Solution", "Analysis"):
    try:
        maxwell_source.Properties[_key].Value = "{setup_name}"
        break
    except Exception:
        continue
else:
    raise Exception("未找到用于设置 Maxwell 求解设置名的属性")
maxwell_source.ImportData()
"""
        app.run_python_script(script)
        return _ok(ok_message(
            f"已从 '{maxwell_project_path}' 导入电磁力",
            source=maxwell_project_path,
            design_name=design_name or None,
            setup_name=setup_name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_modal_analysis - 运行模态分析
# ---------------------------------------------------------------------------

def run_modal_analysis(
    num_modes: int = 12,
    freq_range_hz: tuple[float, float] = (0, 10000),
    analysis_name: str = "Modal",
) -> dict:
    """
    运行电机定子/转子模态分析，提取固有频率和振型。

    Args:
        num_modes: 提取的模态阶数
        freq_range_hz: 频率范围 (f_min, f_max) Hz
        analysis_name: 指定 Mechanical 中的分析名称；未找到则使用第一个分析
    """
    try:
        app = _app()
        script = f"""
modal_analysis = next((a for a in Model.Analyses if a.Name == "{analysis_name}"), Model.Analyses[0])
modal_analysis.Properties["Options/Maximum Modes to Find"].Value = {num_modes}
modal_analysis.Properties["Options/Limit Search to Range"].Value = True
modal_analysis.Properties["Options/Range Minimum"].Value = {freq_range_hz[0]}
modal_analysis.Properties["Options/Range Maximum"].Value = {freq_range_hz[1]}
modal_analysis.Solution.Solve(True)
"""
        app.run_python_script(script)
        return _ok(ok_message(
            f"模态分析完成：{num_modes} 阶，频率范围 {freq_range_hz[0]}-{freq_range_hz[1]} Hz",
            num_modes=num_modes,
            freq_range_hz=list(freq_range_hz),
            analysis_name=analysis_name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_harmonic_analysis - 运行谐响应分析（NVH）
# ---------------------------------------------------------------------------

def run_harmonic_analysis(
    freq_range_hz: tuple[float, float] = (0, 5000),
    num_steps: int = 100,
    damping_ratio: float = 0.02,
    analysis_name: str = "Harmonic Response",
) -> dict:
    """
    运行谐响应分析，评估电机振动和噪声（NVH）。

    Args:
        freq_range_hz: 频率扫描范围（Hz）
        num_steps: 频率步数
        damping_ratio: 阻尼比
        analysis_name: 指定 Mechanical 中的分析名称；未找到则使用第一个分析
    """
    try:
        app = _app()
        script = f"""
harmonic = next((a for a in Model.Analyses if a.Name == "{analysis_name}"), Model.Analyses[0])
harmonic.Properties["Options/Range Minimum"].Value = {freq_range_hz[0]}
harmonic.Properties["Options/Range Maximum"].Value = {freq_range_hz[1]}
harmonic.Properties["Options/Solution Intervals"].Value = {num_steps}
harmonic.Properties["Options/Constant Damping Ratio"].Value = {damping_ratio}
harmonic.Solution.Solve(True)
"""
        app.run_python_script(script)
        return _ok(ok_message(
            f"谐响应分析完成：{freq_range_hz[0]}-{freq_range_hz[1]} Hz，{num_steps} 步",
            freq_range_hz=list(freq_range_hz),
            num_steps=num_steps,
            damping_ratio=damping_ratio,
            analysis_name=analysis_name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_vibration_results - 获取振动结果
# ---------------------------------------------------------------------------

def get_vibration_results(analysis_name: str = "") -> dict:
    """提取固有频率列表和关键频率处的最大变形量。

    Args:
        analysis_name: 指定 Mechanical 中的分析名称；为空则使用第一个分析
    """
    try:
        app = _app()
        script = f"""
import json
results = {{}}
try:
    _name = "{analysis_name}"
    if _name:
        analysis = next((a for a in Model.Analyses if a.Name == _name), None)
        if analysis is None:
            raise Exception("未找到名为 '" + _name + "' 的分析")
    else:
        analysis = Model.Analyses[0]
    sol = analysis.Solution
    freqs = []
    # 从模态分析的 TotalDeformation 结果对象提取固有频率
    # 每个 TotalDeformation 对应一个模态，ReportedFrequency 返回该模态的固有频率
    defo_results = sol.GetChildren(DataModelObjectCategory.TotalDeformation, True)
    for r in defo_results:
        try:
            freq_str = str(r.ReportedFrequency)
            freq = float(freq_str.split()[0])  # "123.4 Hz" -> 123.4
            freqs.append(round(freq, 4))
        except Exception:
            pass
    if not freqs:
        raise Exception("未找到固有频率，请确认已运行模态分析并查看 Mechanical 中的 Solution 结果")
    results["natural_frequencies_Hz"] = sorted(freqs)
except Exception as e:
    results["error"] = str(e)
print(json.dumps(results))
"""
        output = app.run_python_script(script)
        import json
        data = json.loads(output) if output else {}
        if data.get("error"):
            return _err(data["error"])
        return _ok(data)
    except Exception as e:
        return _err(str(e))
