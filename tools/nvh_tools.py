"""
NVH（噪声、振动与声振粗糙度）专用工具：整合电磁力→结构振动→声学的完整 NVH 链路。
与 mechanical_tools（通用结构分析）互补，专注电机 NVH 端到端流程。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, append_warnings, ok_message

_nvh_mech_app = None   # Mechanical 实例
_nvh_mapdl_app = None  # MAPDL 实例
_nvh_config: dict = {}  # NVH 链路配置


def _mech_app():
    if _nvh_mech_app is None:
        raise RuntimeError("未连接到 Mechanical（NVH），请先调用 connect_nvh_mechanical。")
    return _nvh_mech_app


def _mapdl_app():
    if _nvh_mapdl_app is None:
        raise RuntimeError("未连接到 MAPDL（NVH），请先调用 connect_nvh_mapdl。")
    return _nvh_mapdl_app


# ---------------------------------------------------------------------------
# 工具：connect_nvh_mechanical - 连接 Mechanical（NVH 分析）
# ---------------------------------------------------------------------------

def connect_nvh_mechanical(version: str = "242") -> dict:
    """连接 Ansys Mechanical 实例用于 NVH 分析。

    Args:
        version: Ansys 版本号，三位整数字符串，如 "242"（2024 R2）
    """
    global _nvh_mech_app
    try:
        from ansys.mechanical.core import find_mechanical, launch_mechanical
        ver_int = int(version)
        mechs = find_mechanical(ver_int)
        if mechs:
            _nvh_mech_app = launch_mechanical(exec_file=mechs[0], batch=True)
        else:
            _nvh_mech_app = launch_mechanical(batch=True)
        return _ok(ok_message(f"已连接到 Mechanical（NVH 分析，版本 {version}）", version=version))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：connect_nvh_mapdl - 连接 MAPDL（NVH 分析）
# ---------------------------------------------------------------------------

def connect_nvh_mapdl(version: str = "242") -> dict:
    """连接 MAPDL 求解器用于 NVH 结构分析。

    Args:
        version: Ansys 版本号
    """
    global _nvh_mapdl_app
    try:
        from ansys.mapdl.core import launch_mapdl
        _nvh_mapdl_app = launch_mapdl(version=version)
        return _ok(ok_message(f"已连接到 MAPDL（NVH 分析，版本 {version}）", version=version))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：extract_maxwell_electromagnetic_forces - 提取 Maxwell 电磁力
# ---------------------------------------------------------------------------

def extract_maxwell_electromagnetic_forces(
    maxwell_project_path: str,
    design_name: str = "",
    setup_name: str = "Setup1",
    force_type: str = "radial",
    export_path: str = "",
) -> dict:
    """从 Maxwell 仿真提取电磁力密度分布（径向力 / 切向力），作为 NVH 链路的输入。

    电磁力是电机 NVH 的根源激励源，本工具将 Maxwell 仿真得到的
    Maxwell Stress Tensor 力密度导出为结构分析可用的格式。

    Args:
        maxwell_project_path: Maxwell 项目文件路径（.aedt）
        design_name: Maxwell 设计名称；留空使用当前活动设计
        setup_name: 求解设置名称
        force_type: 力类型，"radial"（径向）/ "tangential"（切向）/ "both"
        export_path: 导出文件路径；留空则自动生成
    """
    try:
        from tools import maxwell_tools
        if maxwell_tools._aedt_app is None:
            return _err("未连接到 AEDT，请先调用 connect_aedt。")
        app = maxwell_tools._aedt_app
        warnings: list[str] = []

        # 创建力密度场计算器表达式
        force_exprs = []
        if force_type in ("radial", "both"):
            force_exprs.append("ForceDensity_Radial")
        if force_type in ("tangential", "both"):
            force_exprs.append("ForceDensity_Tangential")

        force_results = {}
        for expr in force_exprs:
            try:
                data = app.post.get_solution_data(
                    expressions=[expr],
                    setup_sweep_name=f"{setup_name} : LastAdaptive",
                )
                force_results[expr] = {
                    "values": list(data.data_real(expr)),
                    "peak": round(max(abs(v) for v in data.data_real(expr)), 4) if data.data_real(expr) else None,
                }
            except Exception as e:
                warnings.append(f"{expr} 提取失败: {e}")

        # 导出到文件（用于后续 Mechanical 导入）
        if not export_path:
            import os
            export_path = os.path.join(os.path.dirname(maxwell_project_path), "nvh_forces.csv")

        try:
            app.post.export_field_plot(
                file_name=export_path,
                setup_name=f"{setup_name} : LastAdaptive",
            )
        except Exception as e:
            warnings.append(f"力场导出失败: {e}")

        _nvh_config["em_forces"] = {
            "source": maxwell_project_path,
            "force_type": force_type,
            "export_path": export_path,
        }

        result = {
            "force_type": force_type,
            "force_results": force_results,
            "export_path": export_path,
            "message": f"电磁力已提取并导出至 '{export_path}'（类型: {force_type}）",
        }
        return _ok(append_warnings(result, warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_forces_to_structural - 将电磁力导入结构模型
# ---------------------------------------------------------------------------

def import_forces_to_structural(
    force_data_path: str,
    structural_project_path: str = "",
    mapping_method: str = "node_based",
) -> dict:
    """将 Maxwell 电磁力密度数据导入 Mechanical/MAPDL 结构模型，
    作为谐响应分析的载荷激励。

    Args:
        force_data_path: 电磁力数据文件路径（CSV/AEDT 导出格式）
        structural_project_path: 结构模型项目路径；留空则使用当前已连接的 Mechanical
        mapping_method: 映射方式，"node_based"（节点插值）/ "element_based"（单元映射）
    """
    try:
        app = _mech_app()
        warnings: list[str] = []

        script = f"""
import mech_dpf
# 导入电磁力作为激励载荷
em_setup = ExtAPI.DataModel.Project.Model.AddElectromagneticSetup()
em_setup.Properties["Source File"].Value = r"{force_data_path}"
for _key in ("Mapping Method", "Interpolation"):
    try:
        em_setup.Properties[_key].Value = "{mapping_method}"
        break
    except Exception:
        continue
em_setup.ImportData()
"""
        app.run_python_script(script)

        _nvh_config["structural"] = {
            "force_source": force_data_path,
            "mapping_method": mapping_method,
        }

        result = {
            "force_data_path": force_data_path,
            "mapping_method": mapping_method,
            "message": f"电磁力已导入结构模型（映射方式: {mapping_method}）",
        }
        return _ok(append_warnings(result, warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_nvh_modal_analysis - 运行 NVH 模态分析
# ---------------------------------------------------------------------------

def run_nvh_modal_analysis(
    num_modes: int = 20,
    freq_range_hz: tuple[float, float] = (0, 10000),
    analysis_name: str = "NVH_Modal",
) -> dict:
    """运行定子/转子模态分析，提取与电磁力频率匹配的固有频率和振型。

    NVH 模态分析需要比普通结构分析提取更多阶数和更宽频率范围，
    以覆盖电磁力的各次谐波频率。

    Args:
        num_modes: 提取的模态阶数（NVH 建议 >= 20）
        freq_range_hz: 频率范围 (f_min, f_max) Hz
        analysis_name: Mechanical 中的分析名称
    """
    try:
        app = _mech_app()
        script = f"""
modal = next((a for a in Model.Analyses if a.Name == "{analysis_name}"), Model.Analyses[0])
modal.Properties["Options/Maximum Modes to Find"].Value = {num_modes}
modal.Properties["Options/Limit Search to Range"].Value = True
modal.Properties["Options/Range Minimum"].Value = {freq_range_hz[0]}
modal.Properties["Options/Range Maximum"].Value = {freq_range_hz[1]}
modal.Solution.Solve(True)
"""
        app.run_python_script(script)

        _nvh_config["modal"] = {
            "num_modes": num_modes,
            "freq_range_hz": list(freq_range_hz),
            "analysis_name": analysis_name,
        }

        return _ok(ok_message(
            f"NVH 模态分析完成：{num_modes} 阶，{freq_range_hz[0]}-{freq_range_hz[1]} Hz",
            num_modes=num_modes,
            freq_range_hz=list(freq_range_hz),
            analysis_name=analysis_name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_nvh_harmonic_response - 运行 NVH 谐响应分析
# ---------------------------------------------------------------------------

def run_nvh_harmonic_response(
    freq_range_hz: tuple[float, float] = (0, 5000),
    num_steps: int = 200,
    damping_ratio: float = 0.02,
    excitation_source: str = "electromagnetic_force",
    analysis_name: str = "NVH_Harmonic",
) -> dict:
    """运行谐响应分析，计算电磁力激励下的振动响应。

    本工具与 mechanical_tools.run_harmonic_analysis 的区别：
    - 显式使用电磁力作为激励源（而非通用载荷）
    - 更密的频率步数（NVH 需要精细频率分辨率）
    - 与 extract_maxwell_electromagnetic_forces 联动

    Args:
        freq_range_hz: 频率扫描范围（Hz）
        num_steps: 频率步数（NVH 建议 >= 200）
        damping_ratio: 阻尼比
        excitation_source: 激励源描述（元数据记录）
        analysis_name: Mechanical 中的分析名称
    """
    try:
        app = _mech_app()
        script = f"""
harmonic = next((a for a in Model.Analyses if a.Name == "{analysis_name}"), Model.Analyses[0])
harmonic.Properties["Options/Range Minimum"].Value = {freq_range_hz[0]}
harmonic.Properties["Options/Range Maximum"].Value = {freq_range_hz[1]}
harmonic.Properties["Options/Solution Intervals"].Value = {num_steps}
harmonic.Properties["Options/Constant Damping Ratio"].Value = {damping_ratio}
harmonic.Solution.Solve(True)
"""
        app.run_python_script(script)

        _nvh_config["harmonic"] = {
            "freq_range_hz": list(freq_range_hz),
            "num_steps": num_steps,
            "damping_ratio": damping_ratio,
            "excitation_source": excitation_source,
            "analysis_name": analysis_name,
        }

        return _ok(ok_message(
            f"NVH 谐响应分析完成：{freq_range_hz[0]}-{freq_range_hz[1]} Hz，{num_steps} 步，"
            f"激励源={excitation_source}",
            freq_range_hz=list(freq_range_hz),
            num_steps=num_steps,
            damping_ratio=damping_ratio,
            excitation_source=excitation_source,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：extract_vibration_noise_results - 提取振动与噪声结果
# ---------------------------------------------------------------------------

def extract_vibration_noise_results(
    analysis_name: str = "",
    surface_names: list[str] | None = None,
    freq_of_interest_Hz: list[float] | None = None,
) -> dict:
    """提取 NVH 分析结果：振动加速度、表面速度、声压级（SPL）等。

    Args:
        analysis_name: 分析名称；为空则使用谐响应分析
        surface_names: 提取振动结果的表面名称列表
        freq_of_interest_Hz: 关注的特定频率点列表（Hz）
    """
    try:
        app = _mech_app()
        warnings: list[str] = []

        script = """
import json
results = {}
try:
    _name = """ + '"' + (analysis_name or "") + '"' + """
    if _name.strip('"'):
        analysis = next((a for a in Model.Analyses if a.Name == _name.strip('"')), None)
        if analysis is None:
            raise Exception("未找到分析: " + _name)
    else:
        analysis = Model.Analyses[-1]
    sol = analysis.Solution

    # 提取振动结果
    vib_results = sol.GetChildren(DataModelObjectCategory.Velocity, True)
    velocities = []
    for r in vib_results:
        try:
            velocities.append({
                "name": r.Name,
                "max_value": float(str(r.Maximum).split()[0]),
                "unit": str(r.Maximum).split()[-1] if len(str(r.Maximum).split()) > 1 else "mm/s",
            })
        except Exception:
            pass
    results["vibration_velocities"] = velocities

    # 提取加速度结果
    acc_results = sol.GetChildren(DataModelObjectCategory.Acceleration, True)
    accelerations = []
    for r in acc_results:
        try:
            accelerations.append({
                "name": r.Name,
                "max_value": float(str(r.Maximum).split()[0]),
            })
        except Exception:
            pass
    results["accelerations"] = accelerations

    # 提取变形结果
    def_results = sol.GetChildren(DataModelObjectCategory.TotalDeformation, True)
    deformations = []
    for r in def_results:
        try:
            freq_str = str(getattr(r, "ReportedFrequency", ""))
            deformations.append({
                "name": r.Name,
                "frequency_Hz": float(freq_str.split()[0]) if freq_str else None,
                "max_deformation_mm": float(str(r.Maximum).split()[0]),
            })
        except Exception:
            pass
    results["modal_deformations"] = deformations

except Exception as e:
    results["error"] = str(e)
print(json.dumps(results))
"""
        raw = app.run_python_script(script)

        import json
        parsed = {}
        if raw and isinstance(raw, str):
            # 从脚本输出中提取 JSON
            for line in raw.strip().split("\n"):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        parsed = json.loads(line)
                        break
                    except Exception:
                        pass

        if not parsed:
            parsed = {"warning": "未能从 Mechanical 提取 NVH 结果"}
            warnings.append("脚本输出解析失败")

        # 计算等效声压级（简化公式：SPL = 20*log10(v/v_ref)，v_ref = 5e-8 m/s）
        vib_vels = parsed.get("vibration_velocities", [])
        v_ref = 5e-8  # m/s（参考声压对应的参考速度）
        spl_estimates = []
        import math
        for vib in vib_vels:
            v_ms = vib.get("max_value", 0) * 1e-3  # mm/s → m/s
            if v_ms > 0:
                spl = 20 * math.log10(v_ms / v_ref)
                spl_estimates.append({
                    "surface": vib.get("name"),
                    "velocity_mm_s": vib.get("max_value"),
                    "estimated_SPL_dBA": round(spl, 1),
                })
        if spl_estimates:
            parsed["estimated_SPL"] = spl_estimates

        result = {
            "nvh_results": parsed,
            "nvh_config": _nvh_config,
        }
        return _ok(append_warnings(result, warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_nvh_full_chain - 一键运行完整 NVH 链路
# ---------------------------------------------------------------------------

def run_nvh_full_chain(
    maxwell_project_path: str,
    design_name: str = "",
    setup_name: str = "Setup1",
    num_modes: int = 20,
    freq_range_hz: tuple[float, float] = (0, 5000),
    num_harmonic_steps: int = 200,
    damping_ratio: float = 0.02,
) -> dict:
    """一键运行电磁力→结构振动→噪声评估的完整 NVH 链路。

    流程：
    1. 从 Maxwell 提取电磁力（径向+切向）
    2. 导入结构模型作为激励载荷
    3. 运行模态分析，获取固有频率
    4. 运行谐响应分析，获取振动响应
    5. 估算声压级

    Args:
        maxwell_project_path: Maxwell 项目路径
        design_name: Maxwell 设计名称
        setup_name: 求解设置名称
        num_modes: 模态阶数
        freq_range_hz: 频率范围
        num_harmonic_steps: 谐响应步数
        damping_ratio: 阻尼比
    """
    try:
        steps_log = []

        # Step 1: 提取电磁力
        force_result = extract_maxwell_electromagnetic_forces(
            maxwell_project_path=maxwell_project_path,
            design_name=design_name,
            setup_name=setup_name,
            force_type="both",
        )
        steps_log.append({"step": "extract_em_forces", "success": force_result["success"]})
        if not force_result["success"]:
            return _err(f"电磁力提取失败: {force_result.get('error')}")

        export_path = force_result["result"].get("export_path", "")

        # Step 2: 导入结构模型
        if export_path:
            import_result = import_forces_to_structural(force_data_path=export_path)
            steps_log.append({"step": "import_forces", "success": import_result["success"]})
            if not import_result["success"]:
                return _err(f"力导入失败: {import_result.get('error')}")

        # Step 3: 模态分析
        modal_result = run_nvh_modal_analysis(
            num_modes=num_modes,
            freq_range_hz=freq_range_hz,
        )
        steps_log.append({"step": "modal_analysis", "success": modal_result["success"]})
        if not modal_result["success"]:
            return _err(f"模态分析失败: {modal_result.get('error')}")

        # Step 4: 谐响应分析
        harmonic_result = run_nvh_harmonic_response(
            freq_range_hz=freq_range_hz,
            num_steps=num_harmonic_steps,
            damping_ratio=damping_ratio,
            excitation_source="electromagnetic_force",
        )
        steps_log.append({"step": "harmonic_response", "success": harmonic_result["success"]})
        if not harmonic_result["success"]:
            return _err(f"谐响应分析失败: {harmonic_result.get('error')}")

        # Step 5: 提取结果
        nv_result = extract_vibration_noise_results()
        steps_log.append({"step": "extract_results", "success": nv_result["success"]})

        result = {
            "chain_steps": steps_log,
            "em_forces": force_result.get("result", {}),
            "nvh_results": nv_result.get("result", {}),
            "config": _nvh_config,
            "message": f"NVH 完整链路已完成（{len(steps_log)} 步），已从电磁力到振动噪声评估全流程跑通",
        }
        return _ok(result)
    except Exception as e:
        return _err(str(e))
