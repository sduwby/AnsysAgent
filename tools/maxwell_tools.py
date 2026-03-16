"""
Maxwell 工具：PyAEDT 电机电磁仿真操作封装。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import math

from tools.utils import _ok, _err, append_warnings, ensure_parent_dir, get_design_names, ok_message

# PyAEDT 延迟导入，允许在未安装 Ansys 的环境中加载模块
_aedt_app = None  # 全局 AEDT Maxwell2d/3d 实例


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _app():
    """返回当前活跃的 Maxwell 应用实例，未连接时抛出异常。"""
    if _aedt_app is None:
        raise RuntimeError("未连接到 AEDT，请先调用 connect_aedt。")
    return _aedt_app


def _get_setup_names(app) -> list[str]:
    existing = getattr(app, "existing_analysis_setups", None)
    if callable(existing):
        existing = existing()
    if existing:
        return list(existing)
    setups = getattr(app, "setups", None)
    if isinstance(setups, list):
        return [getattr(s, "name", s) for s in setups]
    return []


def _get_model_state(app) -> dict:
    state = getattr(app, "_ansysagent_model_state", None)
    if not isinstance(state, dict):
        state = {}
        setattr(app, "_ansysagent_model_state", state)
    return state


def _infer_phase_conductors(app, phase_name: str, grouping_strategy: str = "three_phase_equal_spacing") -> list[str]:
    if grouping_strategy == "manual_only":
        return []
    if grouping_strategy != "three_phase_equal_spacing":
        return []

    state = _get_model_state(app)
    geometry = state.get("geometry", {})
    num_slots = geometry.get("num_slots")
    if not num_slots or num_slots % 3 != 0:
        return []

    phase_index_map = {
        "PHASEA": 0,
        "A": 0,
        "PHASEB": 1,
        "B": 1,
        "PHASEC": 2,
        "C": 2,
    }
    phase_index = phase_index_map.get(phase_name.upper())
    if phase_index is None:
        return []

    conductors = []
    modeler = getattr(app, "modeler", None)
    get_object = getattr(modeler, "get_object_from_name", None)
    for slot_idx in range(phase_index + 1, num_slots + 1, 3):
        conductor_name = f"Conductor_{slot_idx}"
        if callable(get_object) and get_object(conductor_name) is None:
            return []
        conductors.append(conductor_name)
    return conductors


def _apply_magnetization(app, magnet_name: str, angle_deg: float) -> bool:
    angle_value = f"{angle_deg}deg"
    candidates = [
        lambda: app.assign_magnetization(assignment=[magnet_name], direction=angle_value),
        lambda: app.assign_magnetization(magnet_name, angle=angle_value),
        lambda: app.modeler.get_object_from_name(magnet_name).set_magnetization(angle_value),
        lambda: setattr(app.modeler.get_object_from_name(magnet_name), "magnetization_angle", angle_value),
    ]
    for setter in candidates:
        try:
            setter()
            return True
        except Exception:
            continue
    return False


def _configure_rotation_motion(app, rotor_name: str, airgap_name: str) -> bool:
    candidates = [
        lambda: app.assign_rotate_motion(
            assignment=[rotor_name],
            coordinate_system="Global",
            axis="Z",
            positive_movement=True,
        ),
        lambda: app.assign_rotation(
            object_list=[rotor_name],
            axis="Z",
        ),
        lambda: app.modeler.create_band(
            rotor_name=rotor_name,
            airgap_name=airgap_name,
            band_name="MotionBand",
        ),
    ]
    for setter in candidates:
        try:
            setter()
            return True
        except Exception:
            continue
    return False


def _set_geometry_variables(app, geometry_values: dict[str, float]) -> tuple[dict[str, str], list[str]]:
    warnings: list[str] = []
    variable_manager = getattr(app, "variable_manager", None)
    set_variable = getattr(variable_manager, "set_variable", None)
    geometry_variables: dict[str, str] = {}
    for name, value in geometry_values.items():
        geometry_variables[name] = name
        if callable(set_variable):
            try:
                set_variable(name, f"{value}mm")
            except Exception as e:
                warnings.append(f"设计变量 {name} 写入失败: {e}")
        else:
            warnings.append("当前 Maxwell 接口未暴露 variable_manager，几何尺寸不会绑定为设计变量")
            break
    return geometry_variables, warnings


def _radial_point_expr(radius_expr: str, angle_deg: float) -> list[str]:
    cos_value = math.cos(math.radians(angle_deg))
    sin_value = math.sin(math.radians(angle_deg))
    return [
        f"({radius_expr})*({cos_value:.12g})",
        f"({radius_expr})*({sin_value:.12g})",
        "0mm",
    ]

# ---------------------------------------------------------------------------
# 工具：connect_aedt - 连接 AEDT
# ---------------------------------------------------------------------------

def connect_aedt(
    version: str = "2024.1",
    is_3d: bool = False,
    non_graphical: bool = False,
    project_path: str = "",
    design_name: str = "",
) -> dict:
    """
    连接到运行中的 AEDT 实例或启动新实例。

    Args:
        version: AEDT 版本号，如 "2024.1"
        is_3d: True 使用 Maxwell 3D，False 使用 Maxwell 2D
        non_graphical: 是否无界面运行（批处理模式）
        project_path: 目标项目路径或项目名；留空则连接当前活动项目
        design_name: 目标设计名；留空则使用当前活动设计
    """
    global _aedt_app
    try:
        kwargs = {
            "specified_version": version,
            "non_graphical": non_graphical,
            "new_desktop": False,
        }
        if project_path:
            kwargs["project"] = project_path
        if design_name:
            kwargs["design"] = design_name
        if is_3d:
            from ansys.aedt.core import Maxwell3d
            _aedt_app = Maxwell3d(**kwargs)
        else:
            from ansys.aedt.core import Maxwell2d
            _aedt_app = Maxwell2d(**kwargs)
        target = []
        if project_path:
            target.append(f"项目={project_path}")
        if design_name:
            target.append(f"设计={design_name}")
        target_desc = f"，{', '.join(target)}" if target else ""
        return _ok(ok_message(
            f"已连接到 AEDT {version}（{'Maxwell 3D' if is_3d else 'Maxwell 2D'}{target_desc}）",
            version=version,
            is_3d=is_3d,
            project_path=project_path or None,
            design_name=design_name or None,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_maxwell_project - 创建项目
# ---------------------------------------------------------------------------

def create_maxwell_project(project_name: str, design_name: str = "Motor") -> dict:
    """创建新的 Maxwell 项目和设计。"""
    import os
    try:
        app = _app()
        if not project_name.endswith(".aedt"):
            project_name = project_name + ".aedt"
        if not os.path.isabs(project_name):
            project_name = os.path.join(os.getcwd(), project_name)

        # 显式新建项目，避免把当前已打开项目误当成“新项目”继续写入。
        if hasattr(app, "odesktop") and hasattr(app.odesktop, "NewProject"):
            app.odesktop.NewProject()

        # 显式新建设计；如果当前已有默认设计则仅重命名该设计。
        design_names = get_design_names(app)
        if design_names:
            active_design = getattr(app, "active_design", None)
            if active_design is not None:
                active_design.name = design_name
        elif hasattr(app, "insert_design"):
            app.insert_design(design_name=design_name)
        elif hasattr(app, "new_design"):
            app.new_design(design_name=design_name)
        else:
            raise RuntimeError("当前 AEDT 接口不支持创建新设计")

        ensure_parent_dir(project_name)
        app.save_project(project_name)
        return _ok(ok_message(
            f"项目 '{project_name}' 已创建，设计名：'{design_name}'",
            project_name=project_name,
            design_name=design_name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_motor_geometry - 建立电机几何模型
# ---------------------------------------------------------------------------

def create_motor_geometry(
    stator_outer_radius: float,
    stator_inner_radius: float,
    rotor_outer_radius: float,
    rotor_inner_radius: float,
    num_slots: int,
    num_poles: int,
    magnet_thickness: float,
    stack_length: float = 50.0,
) -> dict:
    """
    在 Maxwell 2D 中建立表贴式 PMSM 简化几何模型。
    所有尺寸单位为 mm，使用 PyAEDT 图元接口。
    """
    # 前置几何合法性校验
    if stator_inner_radius >= stator_outer_radius:
        return _err("定子内径必须小于外径")
    if rotor_outer_radius >= stator_inner_radius:
        return _err("转子外径必须小于定子内径（气隙不存在）")
    if rotor_inner_radius >= rotor_outer_radius:
        return _err("转子内径必须小于外径")
    if num_slots <= 0 or num_poles <= 0:
        return _err("槽数和极数必须为正整数")
    if num_poles % 2 != 0:
        return _err("PMSM 极数必须为偶数")
    if magnet_thickness <= 0:
        return _err("永磁体厚度必须为正值")
    if magnet_thickness >= (stator_inner_radius - rotor_outer_radius):
        return _err("永磁体厚度不能超过气隙宽度")
    try:
        app = _app()
        modeler = app.modeler
        warnings: list[str] = []
        geometry_variables, variable_warnings = _set_geometry_variables(
            app,
            {
                "stator_outer_radius": stator_outer_radius,
                "stator_inner_radius": stator_inner_radius,
                "rotor_outer_radius": rotor_outer_radius,
                "rotor_inner_radius": rotor_inner_radius,
                "magnet_thickness": magnet_thickness,
                "stack_length": stack_length,
            },
        )
        warnings.extend(variable_warnings)
        if geometry_variables:
            warnings.append(
                "连续几何尺寸已绑定为 Maxwell 设计变量；num_slots/num_poles 仍属于拓扑参数，修改后需重建几何"
            )

        # 定子轭部（环形）
        modeler.create_circle(
            position=[0, 0, 0],
            radius=geometry_variables.get("stator_outer_radius", stator_outer_radius),
            num_sides=0,
            name="Stator_Outer",
            material="M250-35A",
        )
        modeler.create_circle(
            position=[0, 0, 0],
            radius=geometry_variables.get("stator_inner_radius", stator_inner_radius),
            num_sides=0,
            name="Stator_Inner_Cut",
        )
        modeler.subtract("Stator_Outer", "Stator_Inner_Cut", keep_originals=False)
        # subtract 后刷新对象缓存，确保跨 PyAEDT 版本均能通过原名找到对象
        modeler.refresh_all_ids()
        stator_obj = modeler.get_object_from_name("Stator_Outer")
        if stator_obj is None:
            raise RuntimeError("subtract 后未找到 Stator_Outer，请检查 PyAEDT 版本兼容性")
        stator_obj.name = "Stator"

        # 转子轭部（环形）
        modeler.create_circle(
            position=[0, 0, 0],
            radius=geometry_variables.get("rotor_outer_radius", rotor_outer_radius),
            num_sides=0,
            name="Rotor_Outer",
            material="M250-35A",
        )
        modeler.create_circle(
            position=[0, 0, 0],
            radius=geometry_variables.get("rotor_inner_radius", rotor_inner_radius),
            num_sides=0,
            name="Rotor_Inner_Cut",
        )
        modeler.subtract("Rotor_Outer", "Rotor_Inner_Cut", keep_originals=False)
        modeler.refresh_all_ids()
        rotor_obj = modeler.get_object_from_name("Rotor_Outer")
        if rotor_obj is None:
            raise RuntimeError("subtract 后未找到 Rotor_Outer，请检查 PyAEDT 版本兼容性")
        rotor_obj.name = "Rotor"

        # 气隙区域
        modeler.create_circle(
            position=[0, 0, 0],
            radius=geometry_variables.get("stator_inner_radius", stator_inner_radius),
            num_sides=0,
            name="AirGap_Outer",
            material="vacuum",
        )
        modeler.create_circle(
            position=[0, 0, 0],
            radius=geometry_variables.get("rotor_outer_radius", rotor_outer_radius),
            num_sides=0,
            name="AirGap_Inner_Cut",
        )
        modeler.subtract("AirGap_Outer", "AirGap_Inner_Cut", keep_originals=False)
        modeler.refresh_all_ids()
        airgap_obj = modeler.get_object_from_name("AirGap_Outer")
        if airgap_obj is None:
            raise RuntimeError("subtract 后未找到 AirGap_Outer，请检查 PyAEDT 版本兼容性")
        airgap_obj.name = "AirGap"

        # 表贴式永磁体：每极一块扇形面（外弧 + 内弧封闭多边形），磁极弧系数 0.85
        # 使用 create_polyline + cover_surface=True 生成 2D 面对象（而非 1D 弧线），
        # 确保 Maxwell 2D 可正确赋予材料和参与仿真计算。
        pole_angle = 360.0 / num_poles
        magnet_arc = pole_angle * 0.85
        inner_r_expr = geometry_variables.get("rotor_outer_radius", str(rotor_outer_radius))
        outer_r_expr = (
            f"({geometry_variables['rotor_outer_radius']} + {geometry_variables['magnet_thickness']})"
            if geometry_variables
            else str(rotor_outer_radius + magnet_thickness)
        )
        num_arc_pts = 16  # 每段弧的离散点数，越多弧形越精确

        for i in range(num_poles):
            start_angle = i * pole_angle - magnet_arc / 2
            end_angle = start_angle + magnet_arc
            obj_name = f"Magnet_{i+1}"
            magnetization_angle = i * pole_angle if i % 2 == 0 else i * pole_angle + 180.0

            # 外弧点列（start_angle → end_angle）
            outer_pts = [
                _radial_point_expr(outer_r_expr, start_angle + magnet_arc * k / num_arc_pts)
                for k in range(num_arc_pts + 1)
            ]
            # 内弧点列（end_angle → start_angle，反向以封闭多边形）
            inner_pts = [
                _radial_point_expr(inner_r_expr, end_angle - magnet_arc * k / num_arc_pts)
                for k in range(num_arc_pts + 1)
            ]
            polygon = outer_pts + inner_pts  # 外弧 + 内弧构成封闭扇形边界

            modeler.create_polyline(
                position_list=polygon,
                cover_surface=True,  # 将封闭折线覆盖为 2D 面对象
                name=obj_name,
                matname="NdFe35",
            )
            if not _apply_magnetization(app, obj_name, magnetization_angle):
                warnings.append(f"未能自动设置 {obj_name} 的磁化方向（目标角度 {magnetization_angle:.1f}deg）")

        # 定子槽内铜导体：每槽一个扇形面
        # 槽深取定子轭部厚度的 60%，槽宽取槽距的 70%（含绝缘余量）
        slot_pitch = 360.0 / num_slots
        slot_arc = slot_pitch * 0.70
        cond_inner_r_expr = geometry_variables.get("stator_inner_radius", str(stator_inner_radius))
        cond_outer_r_expr = (
            f"({geometry_variables['stator_inner_radius']} + "
            f"0.6*({geometry_variables['stator_outer_radius']} - {geometry_variables['stator_inner_radius']}))"
            if geometry_variables
            else str(stator_inner_radius + (stator_outer_radius - stator_inner_radius) * 0.60)
        )

        for i in range(num_slots):
            center_angle = i * slot_pitch
            s_start = center_angle - slot_arc / 2
            s_end = s_start + slot_arc
            cond_name = f"Conductor_{i + 1}"

            cond_outer_pts = [
                _radial_point_expr(cond_outer_r_expr, s_start + slot_arc * k / num_arc_pts)
                for k in range(num_arc_pts + 1)
            ]
            cond_inner_pts = [
                _radial_point_expr(cond_inner_r_expr, s_end - slot_arc * k / num_arc_pts)
                for k in range(num_arc_pts + 1)
            ]
            cond_polygon = cond_outer_pts + cond_inner_pts

            modeler.create_polyline(
                position_list=cond_polygon,
                cover_surface=True,
                name=cond_name,
                matname="copper",
            )
            # 从定子铁心挖去导体区域，keep_originals=True 保留导体对象
            modeler.subtract("Stator", cond_name, keep_originals=True)

        stack_length_applied = False
        for setter in (
            lambda: app.change_design_settings({"ModelDepth": f"{stack_length}mm"}),
            lambda: setattr(app, "model_depth", stack_length),
            lambda: app.odesign.SetDesignSettings(
                ["NAME:Design Settings Data", "ModelDepth:=", f"{stack_length}mm"]
            ),
        ):
            try:
                setter()
                stack_length_applied = True
                break
            except Exception:
                continue
        if not stack_length_applied:
            warnings.append(
                "未能将 stack_length 写入 Maxwell 2D 的模型深度设置，请在 AEDT 中复核 ModelDepth"
            )
        motion_configured = _configure_rotation_motion(app, "Rotor", "AirGap")
        if not motion_configured:
            warnings.append(
                "未能自动建立旋转运动带/主运动设置，若直接提取 Moving1.Torque 可能无有效结果"
            )
        magnetization_configured = not any("磁化方向" in warning for warning in warnings)
        if not magnetization_configured:
            warnings.append("请在 AEDT 中复核永磁体极性交替磁化方向后再做精确 PMSM 仿真")
        state = _get_model_state(app)
        state.update({
            "geometry_defined": True,
            "geometry": {
                "num_slots": num_slots,
                "num_poles": num_poles,
                "stack_length_mm": stack_length,
                "geometry_design_variables": list(geometry_variables),
                "parametric_geometry_ready": bool(geometry_variables),
                "topology_locked": True,
            },
            "motion_configured": motion_configured,
            "magnetization_configured": magnetization_configured,
            "torque_ready": bool(magnetization_configured and motion_configured),
        })

        return _ok(append_warnings(ok_message(
            f"电机几何已建立：{num_slots} 槽，{num_poles} 极，"
            f"定子外径={stator_outer_radius*2}mm，转子外径={rotor_outer_radius*2}mm",
            num_slots=num_slots,
            num_poles=num_poles,
            stator_outer_diameter_mm=stator_outer_radius * 2,
            rotor_outer_diameter_mm=rotor_outer_radius * 2,
            stack_length_mm=stack_length,
            geometry_design_variables=list(geometry_variables),
            parametric_geometry_ready=bool(geometry_variables),
            topology_locked=True,
            magnetization_configured=magnetization_configured,
            motion_configured=motion_configured,
            torque_ready=state["torque_ready"],
        ), warnings))
        
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：assign_material - 赋予材料
# ---------------------------------------------------------------------------

def assign_material(object_name: str, material_name: str) -> dict:
    """为几何体对象赋予材料。"""
    try:
        app = _app()
        obj = app.modeler.get_object_from_name(object_name)
        obj.material_name = material_name
        return _ok(ok_message(
            f"已将材料 '{material_name}' 赋予 '{object_name}'",
            object_name=object_name,
            material_name=material_name,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_winding - 配置绕组激励
# ---------------------------------------------------------------------------

def setup_winding(
    phase_name: str,
    current_amplitude: float,
    conductor_names: list[str] | None = None,
    grouping_strategy: str = "three_phase_equal_spacing",
    frequency: float = 0,
    phase_angle: float = 0.0,
    turns: int = 1,
    parallel_branches: int = 1,
    reverse_polarity: bool = False,
) -> dict:
    """
    配置绕组相激励。

    Args:
        phase_name: 相名称，如 "PhaseA"
        conductor_names: 槽内导体对象名称列表；为空时会尝试按 grouping_strategy 自动推断
        grouping_strategy: 自动槽分组策略；默认 "three_phase_equal_spacing"，可选 "manual_only"
        current_amplitude: 峰值电流（A）
        frequency: 电频率（Hz），磁静态仿真置 0
        phase_angle: 相位角（度）
        turns: 匝数，默认 1
        parallel_branches: 并联支路数，默认 1
        reverse_polarity: 是否反向极性，默认 False
    """
    try:
        app = _app()
        warnings: list[str] = []
        valid_grouping_strategies = {"three_phase_equal_spacing", "manual_only"}
        if grouping_strategy not in valid_grouping_strategies:
            return _err(
                f"未知 grouping_strategy: {grouping_strategy}；"
                f"可选 {sorted(valid_grouping_strategies)}"
            )
        if not conductor_names:
            conductor_names = _infer_phase_conductors(app, phase_name, grouping_strategy)
            if conductor_names:
                warnings.append(
                    f"未显式提供 conductor_names，已按 {grouping_strategy} 为 {phase_name} 自动推断导体列表"
                )
            else:
                return _err(
                    "conductor_names 不能为空，且当前几何/分组策略不足以自动推断相绕组导体列表"
                )
        if turns <= 0:
            return _err("turns 必须为正整数")
        if parallel_branches <= 0:
            return _err("parallel_branches 必须为正整数")

        modeler = app.modeler
        get_object = getattr(modeler, "get_object_from_name", None)
        missing_conductors = []
        if callable(get_object):
            missing_conductors = [name for name in conductor_names if get_object(name) is None]
        if missing_conductors:
            return _err(f"以下导体对象不存在: {', '.join(missing_conductors)}")

        coil_terminals = []
        for conductor_name in conductor_names:
            coil_result = app.assign_coil(
                input_object=[conductor_name],
                conductors_type="Stranded",
                winding_name=phase_name,
            )
            coil_name = None
            for attr in ("name", "coil_name"):
                coil_name = getattr(coil_result, attr, None)
                if coil_name:
                    break
            if not coil_name and isinstance(coil_result, str):
                coil_name = coil_result
            coil_terminals.append(coil_name or conductor_name)
        # 始终使用 "Current" 类型：
        #   - 磁静态（frequency=0）：直流电流表达式 "XA"
        #   - 瞬态/交流（frequency>0）：正弦电流表达式（Maxwell 内嵌函数）
        # "External" 类型需要配合 Circuit 联仿，独立使用时 AEDT 会报配置错误。
        if frequency > 0:
            current_expr = (
                f"{current_amplitude}*cos(2*pi*{frequency}*Time"
                f"+{phase_angle}*pi/180)A"
            )
        else:
            current_expr = f"{current_amplitude}A"
        winding_kwargs = {
            "coil_terminals": coil_terminals,
            "winding_name": phase_name,
            "winding_type": "Current",
            "current_value": current_expr,
            "phase_angle": f"{phase_angle}deg",
        }
        optional_winding_fields = {
            "number_of_turns": turns,
            "parallel_branches": parallel_branches,
            "polarity": "Negative" if reverse_polarity else "Positive",
        }
        for field_name, value in optional_winding_fields.items():
            winding_kwargs[field_name] = value
        try:
            app.assign_winding(**winding_kwargs)
        except TypeError:
            for field_name in list(optional_winding_fields):
                winding_kwargs.pop(field_name, None)
            app.assign_winding(**winding_kwargs)

        state = _get_model_state(app)
        state.setdefault("windings", {})[phase_name] = {
            "conductors": list(conductor_names),
            "turns": turns,
            "parallel_branches": parallel_branches,
            "reverse_polarity": reverse_polarity,
            "grouping_strategy": grouping_strategy,
        }
        state["winding_defined"] = True
        return _ok(append_warnings(ok_message(
            f"绕组 '{phase_name}' 已配置：{current_amplitude}A @ {phase_angle}°",
            phase_name=phase_name,
            conductor_names=conductor_names,
            current_amplitude=current_amplitude,
            frequency=frequency,
            phase_angle=phase_angle,
            turns=turns,
            parallel_branches=parallel_branches,
            reverse_polarity=reverse_polarity,
            grouping_strategy=grouping_strategy,
        ), warnings))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_solution_setup - 添加求解设置
# ---------------------------------------------------------------------------

def add_solution_setup(
    setup_name: str = "Setup1",
    solver_type: str = "Transient",
    stop_time: float = 0.02,
    time_step: float = 0.0001,
    num_passes: int = 10,
    frequency_Hz: float = 50.0,
) -> dict:
    """
    添加求解设置。

    Args:
        setup_name: 求解设置名称
        solver_type: "Transient"（瞬态）| "Magnetostatic"（磁静态）| "EddyCurrent"（涡流）
        stop_time: 仿真结束时间（秒，瞬态专用）
        time_step: 时间步长（秒，瞬态专用）
        num_passes: 自适应网格剖分最大迭代次数
        frequency_Hz: 涡流激励频率（Hz，EddyCurrent 专用，默认 50 Hz）
    """
    try:
        app = _app()
        if num_passes <= 0:
            return _err("num_passes 必须为正整数")
        if solver_type == "Transient":
            if stop_time <= 0 or time_step <= 0:
                return _err("Transient 求解要求 stop_time 和 time_step 都为正值")
            if time_step >= stop_time:
                return _err("Transient 求解要求 time_step 小于 stop_time")
        if solver_type == "EddyCurrent" and frequency_Hz <= 0:
            return _err("EddyCurrent 求解要求 frequency_Hz 为正值")

        if solver_type == "Transient":
            setup = app.create_setup(name=setup_name)
            setup.props["StopTime"] = f"{stop_time}s"
            setup.props["TimeStep"] = f"{time_step}s"
            setup.props["MaximumPasses"] = num_passes
            setup.update()
        elif solver_type == "Magnetostatic":
            setup = app.create_setup(name=setup_name)
            setup.props["MaximumPasses"] = num_passes
            setup.update()
        elif solver_type == "EddyCurrent":
            setup = app.create_setup(name=setup_name)
            setup.props["MaximumPasses"] = num_passes
            setup.props["Frequency"] = f"{frequency_Hz}Hz"
            setup.update()
        else:
            return _err(f"未知求解器类型：{solver_type}")
        state = _get_model_state(app)
        state.setdefault("setups", {})[setup_name] = {
            "solver_type": solver_type,
            "stop_time": stop_time if solver_type == "Transient" else None,
            "time_step": time_step if solver_type == "Transient" else None,
            "num_passes": num_passes,
            "frequency_Hz": frequency_Hz if solver_type == "EddyCurrent" else None,
            "solved": False,
        }
        state["last_setup_name"] = setup_name
        state["last_solver_type"] = solver_type
        return _ok(ok_message(
            f"求解设置已添加：{setup_name}（{solver_type}）",
            setup_name=setup_name,
            solver_type=solver_type,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_simulation - 运行仿真
# ---------------------------------------------------------------------------

def run_simulation(setup_name: str = "Setup1") -> dict:
    """运行（求解）指定设置的仿真。"""
    try:
        app = _app()
        setup_names = _get_setup_names(app)
        if setup_names and setup_name not in setup_names:
            return _err(f"求解设置不存在: {setup_name}；当前可用: {', '.join(setup_names)}")
        app.analyze_setup(setup_name)
        state = _get_model_state(app)
        setup_info = state.setdefault("setups", {}).setdefault(setup_name, {})
        setup_info["solved"] = True
        state.setdefault("solved_setups", [])
        if setup_name not in state["solved_setups"]:
            state["solved_setups"].append(setup_name)
        state["last_solved_setup"] = setup_name
        return _ok(ok_message(f"仿真 '{setup_name}' 已完成", setup_name=setup_name))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_custom_material - 创建自定义电磁材料
# ---------------------------------------------------------------------------

def create_custom_material(
    material_name: str,
    conductivity: float = 0.0,
    mass_density: float = 7650.0,
    permeability: float | None = None,
    bh_curve: list[list[float]] | None = None,
    core_loss_kh: float | None = None,
    core_loss_kc: float | None = None,
    core_loss_ke: float | None = None,
) -> dict:
    """
    在 AEDT 材料库中创建自定义电磁材料（支持 B-H 曲线和铁耗系数）。

    Args:
        material_name: 新材料名称；若已存在则直接修改其属性
        conductivity: 电导率（S/m），硅钢片典型值 1.9e6~2.0e6
        mass_density: 质量密度（kg/m³），硅钢片典型值 7650
        permeability: 相对磁导率（常数），提供 bh_curve 时忽略此参数
        bh_curve: B-H 曲线数据点列表 [[H1, B1], [H2, B2], ...]
                  H 单位 A/m，B 单位 T；点数建议 ≥ 10
        core_loss_kh: 磁滞损耗系数 Kh（W/(m³·T²·Hz)）
        core_loss_kc: 涡流损耗系数 Kc（W/(m³·T²·Hz²)）
        core_loss_ke: 附加（过量）损耗系数 Ke（W/(m³·T^1.5·Hz^1.5)）
    """
    try:
        app = _app()
        # 获取或创建材料
        if material_name in app.materials.material_keys:
            mat = app.materials[material_name]
        else:
            mat = app.materials.add_material(material_name)

        mat.conductivity.value = conductivity
        mat.mass_density.value = mass_density

        if bh_curve:
            # 非线性磁导率：以 B-H 曲线描述
            mat.permeability.type = "nonlinear"
            mat.permeability.value = bh_curve
        elif permeability is not None:
            mat.permeability.value = permeability

        # 铁耗系数（Steinmetz 模型）
        if core_loss_kh is not None:
            mat.core_loss_type = "electrical_steel"
            if hasattr(mat, "core_loss_kh"):
                mat.core_loss_kh = core_loss_kh
            if core_loss_kc is not None and hasattr(mat, "core_loss_kc"):
                mat.core_loss_kc = core_loss_kc
            if core_loss_ke is not None and hasattr(mat, "core_loss_ke"):
                mat.core_loss_ke = core_loss_ke

        parts = [f"材料='{material_name}'", f"σ={conductivity} S/m", f"ρ={mass_density} kg/m³"]
        if bh_curve:
            parts.append(f"B-H 曲线（{len(bh_curve)} 点）")
        elif permeability is not None:
            parts.append(f"μr={permeability}")
        if core_loss_kh is not None:
            parts.append(f"铁耗系数 Kh={core_loss_kh}")
        return _ok(ok_message("，".join(parts), material_name=material_name))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_bh_curve - 从 CSV 导入 B-H 曲线
# ---------------------------------------------------------------------------

def import_bh_curve(
    material_name: str,
    csv_path: str,
    h_column: int = 0,
    b_column: int = 1,
    skip_header: bool = True,
) -> dict:
    """
    从 CSV 文件读取 B-H 数据并更新指定材料的非线性磁导率。
    材料须已通过 create_custom_material 创建。

    Args:
        material_name: 目标材料名称
        csv_path: CSV 文件路径（绝对路径）
        h_column: H 值所在列索引（从0开始，默认第0列，单位 A/m）
        b_column: B 值所在列索引（从0开始，默认第1列，单位 T）
        skip_header: 是否跳过第一行标题，默认 True
    """
    import csv as csv_module
    import os

    try:
        if not os.path.exists(csv_path):
            return _err(f"CSV 文件不存在: {csv_path}")

        bh_data: list[list[float]] = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv_module.reader(f)
            if skip_header:
                next(reader, None)
            for row in reader:
                try:
                    h = float(row[h_column])
                    b = float(row[b_column])
                    bh_data.append([h, b])
                except (ValueError, IndexError):
                    continue

        if len(bh_data) < 2:
            return _err(
                f"有效 B-H 数据点不足（仅解析到 {len(bh_data)} 个），"
                "请检查 CSV 格式和列索引"
            )

        app = _app()
        if material_name not in app.materials.material_keys:
            return _err(f"材料 '{material_name}' 不存在，请先调用 create_custom_material 创建")

        mat = app.materials[material_name]
        mat.permeability.type = "nonlinear"
        mat.permeability.value = bh_data

        return _ok(
            f"B-H 曲线已导入至 '{material_name}'：{len(bh_data)} 个数据点，"
            f"H 范围 {bh_data[0][0]:.1f}~{bh_data[-1][0]:.1f} A/m"
        )
    except Exception as e:
        return _err(str(e))
