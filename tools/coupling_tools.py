"""
耦合工具：Maxwell 电磁仿真与 Icepak 热分析自动耦合。
通过损耗空间映射消除手动填值的误差，支持多轮迭代直至温度收敛。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, assign_power_sources


def _maxwell_app():
    """获取 Maxwell AEDT 全局实例。"""
    from tools import maxwell_tools
    if maxwell_tools._aedt_app is None:
        raise RuntimeError("未连接到 AEDT，请先调用 connect_aedt。")
    return maxwell_tools._aedt_app


def _icepak_app():
    """获取 Icepak 全局实例。"""
    from tools import icepak_tools
    if icepak_tools._icepak_app is None:
        raise RuntimeError("未连接到 Icepak，请先调用 connect_icepak。")
    return icepak_tools._icepak_app


def _apply_temperature_feedback(maxwell_app, temperature_map: dict[str, float]) -> dict:
    """
    将热结果反馈到 Maxwell 材料/变量。

    当前项目尚未建立稳定的 Maxwell 温度依赖材料更新流程，因此此处只允许
    在 Maxwell 已存在对应设计变量时写回；否则显式返回未应用，避免伪装成
    真正的双向耦合。
    """
    variable_manager = getattr(maxwell_app, "variable_manager", None)
    if variable_manager is None:
        return {"applied": False, "reason": "Maxwell 无 variable_manager，无法写回温度反馈"}

    updated = []
    missing = []
    variable_map = {
        "Winding": "winding_temp",
        "Stator": "stator_temp",
        "Rotor": "rotor_temp",
    }
    existing_variables = set()
    try:
        existing_variables = set(variable_manager.variables.keys())
    except Exception:
        pass

    for obj_name, temp_c in temperature_map.items():
        var_name = variable_map.get(obj_name)
        if not var_name:
            continue
        if var_name not in existing_variables:
            missing.append(var_name)
            continue
        variable_manager.set_variable(var_name, f"{temp_c}cel")
        updated.append(var_name)

    if not updated:
        reason = (
            "未找到可写回的温度变量。请先在 Maxwell 中定义 "
            "'winding_temp'/'stator_temp'/'rotor_temp' 等温度变量，并用于材料或激励表达式。"
        )
        if missing:
            reason += f" 缺失变量: {', '.join(missing)}"
        return {"applied": False, "reason": reason}

    return {"applied": True, "updated_variables": updated}


# ---------------------------------------------------------------------------
# 工具：link_maxwell_to_icepak - 将 Maxwell 损耗映射到 Icepak
# ---------------------------------------------------------------------------

def link_maxwell_to_icepak(
    maxwell_design_name: str = "",
    setup_name: str = "Setup1",
    use_spatial_distribution: bool = True,
) -> dict:
    """
    将 Maxwell 仿真损耗（铁耗 + 铜耗）自动映射到 Icepak 热分析模型。

    与 setup_motor_thermal 相比，本工具使用仿真计算的实际损耗值
    （包括按几何体分布的空间信息），无需手动输入铜耗/铁耗数值，
    映射精度更高，是全自动流程的关键环节。

    Args:
        maxwell_design_name: Maxwell 设计名称；留空则使用当前活动设计
        setup_name: Maxwell 求解设置名称，用于读取损耗场
        use_spatial_distribution: True 使用空间分布损耗（3D 映射，精度高）；
                                   False 使用平均损耗值（速度快，适合 2D 设计）
    """
    try:
        maxwell_app = _maxwell_app()
        icepak_app = _icepak_app()

        design_name = maxwell_design_name or maxwell_app.design_name

        if use_spatial_distribution:
            # 使用 PyAEDT 内置的 Maxwell-Icepak 耦合（空间分布损耗映射）
            # assign_em_losses 将 Maxwell 热源映射成 Icepak volumetric heat sources
            icepak_app.assign_em_losses(
                design_name=design_name,
                setup_name=setup_name,
                mesh_frequency="50Hz",
            )
            method_desc = "空间分布（assign_em_losses）"
        else:
            # 从 Maxwell 提取平均损耗，设置为均匀热源
            try:
                solution_data = maxwell_app.post.get_solution_data(
                    expressions=["CoreLoss", "OhmicLoss"],
                    setup_sweep_name=f"{setup_name} : LastAdaptive",
                )
                core_vals = solution_data.data_real("CoreLoss")
                ohmic_vals = solution_data.data_real("OhmicLoss")
                avg_core = sum(core_vals) / len(core_vals) if core_vals else 0.0
                avg_ohmic = sum(ohmic_vals) / len(ohmic_vals) if ohmic_vals else 0.0
            except Exception as e:
                return _err(f"读取 Maxwell 损耗失败: {e}")

            if avg_core <= 0 and avg_ohmic <= 0:
                return _err("Maxwell 损耗结果为空或全为 0，无法映射到 Icepak")

            # 设置均匀热源
            assignment = assign_power_sources(icepak_app, {
                "Winding": avg_ohmic,
                "Stator": avg_core * 0.9,
                "Rotor": avg_core * 0.1,
            })
            assigned_sources = assignment["assigned"]
            assignment_errors = assignment["errors"]
            if not assigned_sources:
                return _err(
                    "未能将任何热源映射到 Icepak。"
                    + (f" 失败详情: {'; '.join(assignment_errors)}" if assignment_errors else "")
                )
            method_desc = f"均匀平均值（铁耗={avg_core:.2f}W，铜耗={avg_ohmic:.2f}W）"
            if assignment_errors:
                method_desc += f"，部分失败={'; '.join(assignment_errors)}"

        return _ok(
            f"Maxwell 损耗已映射到 Icepak（设计='{design_name}'，"
            f"方法={method_desc}，求解设置='{setup_name}'）"
        )
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_em_thermal_iteration - 电磁-热耦合迭代
# ---------------------------------------------------------------------------

def run_em_thermal_iteration(
    max_iterations: int = 3,
    convergence_temp_delta: float = 1.0,
    maxwell_setup_name: str = "Setup1",
    icepak_setup_name: str = "SetupThermal",
    feedback_mode: str = "one_way",
) -> dict:
    """
    运行 Maxwell-Icepak 耦合迭代求解，直至温度场收敛或达到最大迭代次数。

    迭代逻辑：
      1. 运行 Maxwell 电磁仿真，提取损耗场
      2. 将损耗映射到 Icepak（调用 link_maxwell_to_icepak）
      3. 运行 Icepak 热仿真，获取各部件温度
      4. 将温度结果反馈 Maxwell（更新导体导率等温度相关参数）
      5. 重复直到最高温度变化 < convergence_temp_delta（°C）或超过 max_iterations

    Args:
        max_iterations: 最大耦合迭代次数（推荐 2~5）
        convergence_temp_delta: 收敛判据：相邻两轮最高温度差（°C），默认 1.0
        maxwell_setup_name: Maxwell 求解设置名称
        icepak_setup_name: Icepak 求解设置名称
        feedback_mode: "one_way" 为单向 Maxwell→Icepak 热迭代；
                       "two_way" 为严格双向耦合，要求温度可写回 Maxwell
    """
    try:
        if feedback_mode not in {"one_way", "two_way"}:
            return _err(f"未知 feedback_mode: {feedback_mode}，仅支持 one_way / two_way")

        maxwell_app = _maxwell_app()
        icepak_app = _icepak_app()

        history = []    # 每轮 {"iteration": n, "max_temp_C": T, "delta_T": ΔT}
        prev_max_temp = None
        feedback_applied = False

        # 在循环前创建 Icepak 求解设置（若已存在则直接复用，避免每轮重复创建报错）
        existing_setup_names = [s.name for s in icepak_app.setups]
        if icepak_setup_name not in existing_setup_names:
            _setup = icepak_app.create_setup(icepak_setup_name)
            _setup.props["Convergence Criteria - Max Iterations"] = 100
            _setup.update()

        for iteration in range(1, max_iterations + 1):
            # Step 1：运行 Maxwell 仿真
            maxwell_app.analyze_setup(maxwell_setup_name)

            # Step 2：损耗映射到 Icepak
            link_result = link_maxwell_to_icepak(
                maxwell_design_name=maxwell_app.design_name,
                setup_name=maxwell_setup_name,
                use_spatial_distribution=False,  # 均匀平均值适合迭代效率
            )
            if not link_result.get("success"):
                return _err(f"损耗映射失败（第{iteration}轮）：{link_result.get('error')}")

            # Step 3：运行 Icepak 热仿真
            icepak_app.analyze_setup(icepak_setup_name)

            # Step 4：提取最高温度并判断收敛
            current_max_temp = None
            temperature_map = {}
            for obj_name in ["Winding", "Stator", "Rotor"]:
                try:
                    temp = icepak_app.post.get_scalar_field_value(
                        "Temperature", "Maximum", object_name=obj_name,
                    )
                    if temp is not None:
                        temp_value = float(temp)
                        temperature_map[obj_name] = temp_value
                        current_max_temp = max(current_max_temp or 0.0, temp_value)
                except Exception:
                    pass

            if current_max_temp is None:
                return _err(f"第{iteration}轮未能从 Icepak 提取任何有效温度结果，无法继续耦合迭代")

            feedback_result = {"applied": False, "updated_variables": [], "mode": feedback_mode}
            # Step 5：可选温度反馈回 Maxwell。
            if feedback_mode == "two_way":
                feedback_result = _apply_temperature_feedback(maxwell_app, temperature_map)
                feedback_result["mode"] = feedback_mode
                if not feedback_result.get("applied"):
                    return _err(
                        f"第{iteration}轮未能将温度反馈回 Maxwell：{feedback_result.get('reason')}"
                    )
                feedback_applied = True
            else:
                feedback_result["reason"] = "单向模式未执行 Maxwell 温度回写"

            delta_t = abs(current_max_temp - prev_max_temp) if (
                prev_max_temp is not None and current_max_temp is not None
            ) else None

            history.append({
                "iteration": iteration,
                "max_temp_C": round(current_max_temp, 2) if current_max_temp else None,
                "delta_T": round(delta_t, 3) if delta_t is not None else "N/A",
                "feedback_mode": feedback_mode,
                "feedback_variables": feedback_result.get("updated_variables", []),
            })

            # 收敛判断
            if delta_t is not None and delta_t < convergence_temp_delta:
                return _ok({
                    "converged": True,
                    "iterations": iteration,
                    "final_max_temp_C": round(current_max_temp, 2),
                    "feedback_applied": feedback_applied,
                    "feedback_mode": feedback_mode,
                    "history": history,
                    "message": f"第 {iteration} 轮收敛（ΔT={delta_t:.3f}°C < {convergence_temp_delta}°C）",
                })
            prev_max_temp = current_max_temp

        # 达到最大迭代次数
        return _ok({
            "converged": False,
            "iterations": max_iterations,
            "final_max_temp_C": round(prev_max_temp, 2) if prev_max_temp else None,
            "feedback_applied": feedback_applied,
            "feedback_mode": feedback_mode,
            "history": history,
            "message": f"已达最大迭代次数 {max_iterations}，未完全收敛",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_thermal_to_mechanical - 温度场导入结构（热-结构耦合）
# ---------------------------------------------------------------------------

def import_thermal_to_mechanical(
    icepak_project_path: str = "",
    setup_name: str = "SetupThermal",
    analysis_name: str = "Static Structural",
) -> dict:
    """
    将 Icepak 温度场结果导入 Ansys Mechanical 作为热载荷，
    用于分析热应力、热变形（转子热膨胀、轴弯曲等）。

    工作流：Icepak 热仿真 → 温度分布 → Mechanical 结构分析 → 热应力/变形结果

    Args:
        icepak_project_path: Icepak 项目文件路径（.aedt）；
                              留空则尝试从当前项目路径推导
        setup_name: Icepak 求解设置名称（含温度结果）
        analysis_name: Mechanical 中目标分析名称，默认 "Static Structural"
    """
    try:
        from tools import mechanical_tools
        if mechanical_tools._mech_app is None:
            raise RuntimeError("未连接到 Mechanical，请先调用 connect_mechanical。")
        mech_app = mechanical_tools._mech_app

        # 若未指定 Icepak 路径，从当前 AEDT 项目推导
        if not icepak_project_path:
            try:
                from tools import maxwell_tools
                if maxwell_tools._aedt_app is not None:
                    icepak_project_path = maxwell_tools._aedt_app.project_file
            except Exception:
                pass

        # 通过 ACT 脚本将 Icepak 温度场导入 Mechanical
        script = f"""
import json
results = {{}}
try:
    _analysis_name = "{analysis_name}"
    analysis = next(
        (a for a in Model.Analyses if a.Name == _analysis_name),
        Model.Analyses[0]
    )
    # 创建导入温度载荷
    imported_load_env = analysis.CreateLoadEnvironment()
    thermal_cond = imported_load_env.AddThermalCondition()
    thermal_cond.Properties["Source"].Value = "Imported Temperature"
    if r"{icepak_project_path}":
        thermal_cond.Properties["Source File"].Value = r"{icepak_project_path}"
    thermal_cond.ImportData()
    results["status"] = "success"
    results["analysis"] = _analysis_name
    results["message"] = "Icepak 温度场已导入作为热载荷"
except Exception as err:
    results["status"] = "error"
    results["error"] = str(err)
print(json.dumps(results))
"""
        import json as _json
        output = mech_app.run_python_script(script)
        data = _json.loads(output) if output else {}

        if data.get("status") == "error":
            return _err(f"热载荷导入失败：{data.get('error')}")

        return _ok({
            "analysis_name": analysis_name,
            "icepak_source": icepak_project_path or "（当前项目）",
            "setup_name": setup_name,
            "message": (
                f"Icepak 温度场已映射到 Mechanical '{analysis_name}' 分析。"
                "请运行静力学分析以获取热应力和热变形结果。"
            ),
        })
    except Exception as e:
        return _err(str(e))
