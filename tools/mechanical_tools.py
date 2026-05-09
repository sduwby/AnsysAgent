"""
Mechanical 结构工具：驱动 Ansys Mechanical 进行结构/热分析。
支持两种连接模式：
  1. AEDT 内嵌模式（通过 PyAEDT，用于电机 NVH/转子应力）
  2. 独立批处理模式（通过 ansys-mechanical-core launch_mechanical，
     用于 PCB 热分析、排气歧管热力耦合等完整 Mechanical 工作流）

参考工作流：
  - pyansys-workflows/geometry-mechanical-dpf/wf_gmd_02_mechanical.py（PCB 热分析）
  - pyansys-workflows/fluent-mechanical/wf_fm_02_mechanical.py（排气歧管热力耦合）

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, ok_message

_mech_app = None     # 全局 Mechanical 实例（AEDT 内嵌或独立模式均使用）
_mech_standalone = False  # 标记当前是否为独立批处理模式


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
# 工具：launch_mechanical_standalone - 独立批处理模式启动 Mechanical
# ---------------------------------------------------------------------------

def launch_mechanical_standalone(
    batch: bool = True,
    cleanup_on_exit: bool = False,
    version: str | None = None,
) -> dict:
    """
    以独立批处理模式启动 Ansys Mechanical（通过 ansys-mechanical-core launch_mechanical）。
    适用于不依赖 AEDT 的 PCB 热分析、排气歧管热力耦合等完整 Mechanical 工作流。

    参考工作流：
      - geometry-mechanical-dpf/wf_gmd_02_mechanical.py（mech.App() 内嵌模式）
      - fluent-mechanical/wf_fm_02_mechanical.py（launch_mechanical batch 模式）

    Args:
        batch: True 以批处理模式运行（无图形界面，适合自动化流程）
        cleanup_on_exit: True 则退出时自动清理临时文件
        version: Ansys 版本号，如 "251"（2025 R1），None 使用默认安装版本
    """
    global _mech_app, _mech_standalone
    try:
        from ansys.mechanical.core import launch_mechanical

        kwargs: dict = dict(batch=batch, cleanup_on_exit=cleanup_on_exit)
        if version is not None:
            kwargs["version"] = int(version)

        _mech_app = launch_mechanical(**kwargs)
        _mech_standalone = True

        project_dir = _mech_app.project_directory
        return _ok(ok_message(
            f"已以独立批处理模式启动 Mechanical（batch={batch}）",
            batch=batch,
            project_directory=project_dir,
            version=version,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：mechanical_run_script - 在 Mechanical 中执行 Python 脚本
# ---------------------------------------------------------------------------

def mechanical_run_script(script: str) -> dict:
    """
    在当前 Mechanical 会话中执行任意 Python/ACT 脚本，返回脚本输出。
    适用于独立批处理模式下精细控制 Mechanical 操作。

    Args:
        script: 要在 Mechanical 中执行的 Python 脚本字符串
    """
    try:
        app = _app()
        if _mech_standalone:
            output = app.run_python_script(script)
        else:
            output = app.run_python_script(script)
        return _ok(ok_message(
            "脚本执行完成",
            output=output or "",
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：mechanical_upload_file - 上传文件到 Mechanical 项目目录
# ---------------------------------------------------------------------------

def mechanical_upload_file(local_file_path: str) -> dict:
    """
    将本地文件上传到 Mechanical 服务器项目目录（独立批处理模式专用）。
    用于传递几何文件、材料 XML、CFD 结果 CSV 等输入文件。

    参考工作流：fluent-mechanical/wf_fm_02_mechanical.py（mechanical.upload）

    Args:
        local_file_path: 本地文件的绝对路径
    """
    try:
        import os
        app = _app()
        project_dir = app.project_directory
        app.upload(
            file_name=local_file_path,
            file_location_destination=project_dir,
        )
        base_name = os.path.basename(local_file_path)
        server_path = os.path.join(project_dir, base_name)
        # 将服务器路径注入 Mechanical 会话变量（供后续脚本引用）
        var_name = base_name.replace(".", "_").replace("-", "_").replace(" ", "_")
        app.run_python_script(f"{var_name} = r'{server_path}'")

        return _ok(ok_message(
            f"文件已上传：{base_name} → {server_path}",
            local_file=local_file_path,
            server_path=server_path,
            session_variable=var_name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：mechanical_download_file - 从 Mechanical 项目目录下载文件
# ---------------------------------------------------------------------------

def mechanical_download_file(server_file_path: str, local_target_dir: str) -> dict:
    """
    从 Mechanical 服务器项目目录下载结果文件（图片、数据等）到本地。

    参考工作流：fluent-mechanical/wf_fm_02_mechanical.py（mechanical.download）

    Args:
        server_file_path: 服务器上的文件完整路径
        local_target_dir: 本地目标目录
    """
    try:
        import os
        app = _app()
        app.download(files=server_file_path, target_dir=local_target_dir)
        base_name = os.path.basename(server_file_path)
        local_path = os.path.join(local_target_dir, base_name)
        return _ok(ok_message(
            f"文件已下载：{base_name} → {local_path}",
            server_file=server_file_path,
            local_path=local_path,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_steady_state_thermal - 稳态热分析（Mechanical 独立模式）
# ---------------------------------------------------------------------------

def run_steady_state_thermal(
    geometry_file_var: str = "geometry_path",
    internal_heat_gen_w_m3: float = 5e7,
    heated_component_ns: str = "ic-6",
    convection_film_coeff: float = 5.0,
    convection_ns: str = "all_bodies",
    output_dir: str | None = None,
) -> dict:
    """
    在独立 Mechanical 中执行稳态热分析。
    工作流：导入几何 → 设置内热源 → 设置对流边界 → 求解 → 导出结果图。

    参考工作流：geometry-mechanical-dpf/wf_gmd_02_mechanical.py

    Args:
        geometry_file_var: Mechanical 会话中已定义的几何文件路径变量名
        internal_heat_gen_w_m3: 内热生成率（W/m³）
        heated_component_ns: 施加内热的命名选择名称
        convection_film_coeff: 对流换热系数（W/m²·°C）
        convection_ns: 施加对流的命名选择名称（通常为所有体）
        output_dir: 结果图导出目录；None 则使用 Mechanical 项目目录
    """
    try:
        app = _app()
        script = f"""
import os, json

# 导入几何
geometry_path = {geometry_file_var}
geometry_import_group = Model.GeometryImportGroup
geometry_import = geometry_import_group.AddGeometryImport()
geometry_import_format = Ansys.Mechanical.DataModel.Enums.GeometryImportPreference.Format.Automatic
geometry_import_preferences = Ansys.ACT.Mechanical.Utilities.GeometryImportPreferences()
geometry_import_preferences.ProcessNamedSelections = True
geometry_import.Import(geometry_path, geometry_import_format, geometry_import_preferences)

# 设置单位
ExtAPI.Application.ActiveUnitSystem = MechanicalUnitSystem.StandardMKS

# 生成网格
mesh = Model.Mesh
mesh.GenerateMesh()

# 稳态热分析
steady = Model.AddSteadyStateThermalAnalysis()

# 内热生成
NSall = ExtAPI.DataModel.Project.Model.NamedSelections.GetChildren[
    Ansys.ACT.Automation.Mechanical.NamedSelection](True)
heated_ns = [i for i in NSall if i.Name == "{heated_component_ns}"]
if heated_ns:
    ihg = steady.AddInternalHeatGeneration()
    ihg.Location = heated_ns[0]
    ihg.Magnitude.Output.SetDiscreteValue(0, Quantity({internal_heat_gen_w_m3}, "W m^-1 m^-1 m^-1"))

# 对流边界条件
conv_ns = [i for i in NSall if i.Name == "{convection_ns}"]
if conv_ns:
    conv = steady.AddConvection()
    conv.Location = conv_ns[0]
    conv.FilmCoefficient.Output.DiscreteValues = [Quantity("{convection_film_coeff}[W m^-2 C^-1]")]

# 求解
sol = steady.Solution
sol.AddTemperature()
sol.Solve(True)

# 导出结果摘要
result = {{"status": str(sol.Status)}}
import json
print(json.dumps(result))
"""
        output = app.run_python_script(script)
        import json as json_mod
        data = {}
        try:
            data = json_mod.loads(output) if output and output.strip().startswith("{") else {}
        except Exception:
            pass

        return _ok(ok_message(
            f"稳态热分析完成（内热={internal_heat_gen_w_m3} W/m³，"
            f"对流系数={convection_film_coeff} W/m²·°C）",
            heated_component_ns=heated_component_ns,
            convection_ns=convection_ns,
            solver_status=data.get("status", "Unknown"),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_fluent_htc_to_mechanical - 导入 Fluent CHT 结果到 Mechanical
# ---------------------------------------------------------------------------

def import_fluent_htc_to_mechanical(
    csv_file_vars: list[str],
    csv_labels: list[str],
    target_ns: str = "interface_surface",
) -> dict:
    """
    将 Fluent CHT 分析导出的 HTC/温度 CSV 文件作为外部数据导入 Mechanical，
    用于瞬态热分析的对流边界条件映射。

    参考工作流：fluent-mechanical/wf_fm_02_mechanical.py
    （ExternalDataFileCollection + ImportSettingsFactory）

    Args:
        csv_file_vars: Mechanical 会话中已定义的 CSV 文件路径变量名列表
                       （如 ["temp_htc_data_high_path", "temp_htc_data_med_path"]）
        csv_labels: 每个文件对应的标签（如 ["High", "Med", "Low"]），
                    用于时间步映射
        target_ns: 施加导入对流的命名选择名称（Mechanical 中的 interface 面）
    """
    try:
        app = _app()

        # 构建外部数据文件脚本
        file_entries = ""
        for i, (var, label) in enumerate(zip(csv_file_vars, csv_labels)):
            is_main = "True" if i == 0 else "False"
            file_entries += f"""
edf_{i} = Ansys.Mechanical.ExternalData.ExternalDataFile()
external_data_files.Add(edf_{i})
edf_{i}.Identifier = "File{i+1}"
edf_{i}.Description = "{label}"
edf_{i}.IsMainFile = {is_main}
edf_{i}.FilePath = {var}
edf_{i}.ImportSettings = (
    Ansys.Mechanical.ExternalData.ImportSettingsFactory.GetSettingsForFormat(
        MechanicalEnums.ExternalData.ImportFormat.Delimited
    )
)
isettings_{i} = edf_{i}.ImportSettings
isettings_{i}.SkipRows = 1
isettings_{i}.SkipFooter = 0
isettings_{i}.Delimiter = ","
isettings_{i}.AverageCornerNodesToMidsideNodes = False
isettings_{i}.UseColumn(0, MechanicalEnums.ExternalData.VariableType.NodeId, "", "Node ID@A")
isettings_{i}.UseColumn(1, MechanicalEnums.ExternalData.VariableType.XCoordinate, "m", "X@B")
isettings_{i}.UseColumn(2, MechanicalEnums.ExternalData.VariableType.YCoordinate, "m", "Y@C")
isettings_{i}.UseColumn(3, MechanicalEnums.ExternalData.VariableType.ZCoordinate, "m", "Z@D")
isettings_{i}.UseColumn(4, MechanicalEnums.ExternalData.VariableType.Temperature, "K", "Temperature@E")
isettings_{i}.UseColumn(5, MechanicalEnums.ExternalData.VariableType.HeatTransferCoefficient,
    "W m^-2 K^-1", "HTC@F")
"""

        script = f"""
import json
external_data_files = Ansys.Mechanical.ExternalData.ExternalDataFileCollection()
external_data_files.SaveFilesWithProject = False
{file_entries}

# 找到目标分析（假设第一个为瞬态热分析）
TRANS_THERM = Model.Analyses[0]
imported_load_group = TRANS_THERM.AddImportedLoadExternalData()
imported_convection = imported_load_group.AddImportedConvection()
imported_load_group.ImportExternalDataFiles(external_data_files)

# 设置位置
NSall = ExtAPI.DataModel.Project.Model.NamedSelections.GetChildren[
    Ansys.ACT.Automation.Mechanical.NamedSelection](True)
target_ns = [i for i in NSall if i.Name == "{target_ns}"]
if target_ns:
    imported_convection.Location = target_ns[0]
imported_convection.ImportLoad()
print(json.dumps({{"status": "ok", "files": {len(csv_file_vars)}}}))
"""
        output = app.run_python_script(script)
        return _ok(ok_message(
            f"已导入 {len(csv_file_vars)} 个 Fluent CHT 文件到 Mechanical（目标面={target_ns}）",
            file_count=len(csv_file_vars),
            target_ns=target_ns,
            labels=csv_labels,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：mechanical_exit - 退出 Mechanical 会话
# ---------------------------------------------------------------------------

def mechanical_exit() -> dict:
    """
    退出当前 Mechanical 会话并释放资源（独立批处理模式专用）。
    每次完成分析后应调用此函数以避免进程残留。
    """
    global _mech_app, _mech_standalone
    try:
        if _mech_app is not None:
            _mech_app.exit()
            _mech_app = None
            _mech_standalone = False
        return _ok(ok_message("Mechanical 会话已退出", closed=True))
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
