"""
Maxwell 工具：PyAEDT 电机电磁仿真操作封装。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import math

from tools.utils import _ok, _err

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


# ---------------------------------------------------------------------------
# 工具：connect_aedt - 连接 AEDT
# ---------------------------------------------------------------------------

def connect_aedt(version: str = "2024.1", is_3d: bool = False, non_graphical: bool = False) -> dict:
    """
    连接到运行中的 AEDT 实例或启动新实例。

    Args:
        version: AEDT 版本号，如 "2024.1"
        is_3d: True 使用 Maxwell 3D，False 使用 Maxwell 2D
        non_graphical: 是否无界面运行（批处理模式）
    """
    global _aedt_app
    try:
        if is_3d:
            from ansys.aedt.core import Maxwell3d
            _aedt_app = Maxwell3d(
                specified_version=version,
                non_graphical=non_graphical,
                new_desktop=False,
            )
        else:
            from ansys.aedt.core import Maxwell2d
            _aedt_app = Maxwell2d(
                specified_version=version,
                non_graphical=non_graphical,
                new_desktop=False,
            )
        return _ok(f"已连接到 AEDT {version}（{'Maxwell 3D' if is_3d else 'Maxwell 2D'}）")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_maxwell_project - 创建项目
# ---------------------------------------------------------------------------

def create_maxwell_project(project_name: str, design_name: str = "Motor") -> dict:
    """创建新的 Maxwell 项目和设计。"""
    try:
        app = _app()
        app.save_project(project_name)
        app.design_name = design_name
        return _ok(f"项目 '{project_name}' 已创建，设计名：'{design_name}'")
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
    if magnet_thickness <= 0:
        return _err("永磁体厚度必须为正值")
    if magnet_thickness >= (stator_inner_radius - rotor_outer_radius):
        return _err("永磁体厚度不能超过气隙宽度")
    try:
        app = _app()
        modeler = app.modeler

        # 定子轭部（环形）
        modeler.create_circle(
            position=[0, 0, 0],
            radius=stator_outer_radius,
            num_sides=0,
            name="Stator_Outer",
            material="M250-35A",
        )
        modeler.create_circle(
            position=[0, 0, 0],
            radius=stator_inner_radius,
            num_sides=0,
            name="Stator_Inner_Cut",
        )
        modeler.subtract("Stator_Outer", "Stator_Inner_Cut", keep_originals=False)
        modeler.get_object_from_name("Stator_Outer").name = "Stator"

        # 转子轭部（环形）
        modeler.create_circle(
            position=[0, 0, 0],
            radius=rotor_outer_radius,
            num_sides=0,
            name="Rotor_Outer",
            material="M250-35A",
        )
        modeler.create_circle(
            position=[0, 0, 0],
            radius=rotor_inner_radius,
            num_sides=0,
            name="Rotor_Inner_Cut",
        )
        modeler.subtract("Rotor_Outer", "Rotor_Inner_Cut", keep_originals=False)
        modeler.get_object_from_name("Rotor_Outer").name = "Rotor"

        # 气隙区域
        modeler.create_circle(
            position=[0, 0, 0],
            radius=stator_inner_radius,
            num_sides=0,
            name="AirGap_Outer",
            material="vacuum",
        )
        modeler.create_circle(
            position=[0, 0, 0],
            radius=rotor_outer_radius,
            num_sides=0,
            name="AirGap_Inner_Cut",
        )
        modeler.subtract("AirGap_Outer", "AirGap_Inner_Cut", keep_originals=False)
        modeler.get_object_from_name("AirGap_Outer").name = "AirGap"

        # 表贴式永磁体：每极一块扇形面（外弧 + 内弧封闭多边形），磁极弧系数 0.85
        # 使用 create_polyline + cover_surface=True 生成 2D 面对象（而非 1D 弧线），
        # 确保 Maxwell 2D 可正确赋予材料和参与仿真计算。
        pole_angle = 360.0 / num_poles
        magnet_arc = pole_angle * 0.85
        inner_r = rotor_outer_radius               # 永磁体内弧半径（紧贴转子表面）
        outer_r = rotor_outer_radius + magnet_thickness  # 永磁体外弧半径
        num_arc_pts = 16  # 每段弧的离散点数，越多弧形越精确

        for i in range(num_poles):
            start_angle = i * pole_angle - magnet_arc / 2
            end_angle = start_angle + magnet_arc
            obj_name = f"Magnet_{i+1}"

            # 外弧点列（start_angle → end_angle）
            outer_pts = [
                [
                    outer_r * math.cos(math.radians(start_angle + magnet_arc * k / num_arc_pts)),
                    outer_r * math.sin(math.radians(start_angle + magnet_arc * k / num_arc_pts)),
                    0,
                ]
                for k in range(num_arc_pts + 1)
            ]
            # 内弧点列（end_angle → start_angle，反向以封闭多边形）
            inner_pts = [
                [
                    inner_r * math.cos(math.radians(end_angle - magnet_arc * k / num_arc_pts)),
                    inner_r * math.sin(math.radians(end_angle - magnet_arc * k / num_arc_pts)),
                    0,
                ]
                for k in range(num_arc_pts + 1)
            ]
            polygon = outer_pts + inner_pts  # 外弧 + 内弧构成封闭扇形边界

            modeler.create_polyline(
                position_list=polygon,
                cover_surface=True,  # 将封闭折线覆盖为 2D 面对象
                name=obj_name,
                matname="NdFe35",
            )

        # 定子槽内铜导体：每槽一个扇形面
        # 槽深取定子轭部厚度的 60%，槽宽取槽距的 70%（含绝缘余量）
        slot_pitch = 360.0 / num_slots
        slot_arc = slot_pitch * 0.70
        cond_inner_r = stator_inner_radius                          # 导体内弧 = 定子内径
        yoke_thickness = stator_outer_radius - stator_inner_radius
        cond_outer_r = stator_inner_radius + yoke_thickness * 0.60  # 导体外弧

        for i in range(num_slots):
            center_angle = i * slot_pitch
            s_start = center_angle - slot_arc / 2
            s_end = s_start + slot_arc
            cond_name = f"Conductor_{i + 1}"

            cond_outer_pts = [
                [
                    cond_outer_r * math.cos(math.radians(s_start + slot_arc * k / num_arc_pts)),
                    cond_outer_r * math.sin(math.radians(s_start + slot_arc * k / num_arc_pts)),
                    0,
                ]
                for k in range(num_arc_pts + 1)
            ]
            cond_inner_pts = [
                [
                    cond_inner_r * math.cos(math.radians(s_end - slot_arc * k / num_arc_pts)),
                    cond_inner_r * math.sin(math.radians(s_end - slot_arc * k / num_arc_pts)),
                    0,
                ]
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

        return _ok(
            f"电机几何已建立：{num_slots} 槽，{num_poles} 极，"
            f"定子外径={stator_outer_radius*2}mm，转子外径={rotor_outer_radius*2}mm"
        )
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
        return _ok(f"已将材料 '{material_name}' 赋予 '{object_name}'")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_winding - 配置绕组激励
# ---------------------------------------------------------------------------

def setup_winding(
    phase_name: str,
    conductor_names: list[str],
    current_amplitude: float,
    frequency: float = 0,
    phase_angle: float = 0.0,
) -> dict:
    """
    配置绕组相激励。

    Args:
        phase_name: 相名称，如 "PhaseA"
        conductor_names: 槽内导体对象名称列表
        current_amplitude: 峰值电流（A）
        frequency: 电频率（Hz），磁静态仿真置 0
        phase_angle: 相位角（度）
    """
    try:
        app = _app()
        app.assign_coil(
            input_object=conductor_names,
            conductors_type="Stranded",
            winding_name=phase_name,
        )
        app.assign_winding(
            coil_terminals=[phase_name],
            winding_name=phase_name,
            winding_type="External" if frequency > 0 else "Current",
            current_value=f"{current_amplitude}A",
            phase_angle=f"{phase_angle}deg",
        )
        return _ok(f"绕组 '{phase_name}' 已配置：{current_amplitude}A @ {phase_angle}°")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_solution_setup - 添加求解设置
# ---------------------------------------------------------------------------

def add_solution_setup(
    solver_type: str = "Transient",
    stop_time: float = 0.02,
    time_step: float = 0.0001,
    num_passes: int = 10,
    frequency_Hz: float = 50.0,
) -> dict:
    """
    添加求解设置。

    Args:
        solver_type: "Transient"（瞬态）| "Magnetostatic"（磁静态）| "EddyCurrent"（涡流）
        stop_time: 仿真结束时间（秒，瞬态专用）
        time_step: 时间步长（秒，瞬态专用）
        num_passes: 自适应网格剖分最大迭代次数
        frequency_Hz: 涡流激励频率（Hz，EddyCurrent 专用，默认 50 Hz）
    """
    try:
        app = _app()
        if solver_type == "Transient":
            setup = app.create_setup(name="Setup1")
            setup.props["StopTime"] = f"{stop_time}s"
            setup.props["TimeStep"] = f"{time_step}s"
            setup.update()
        elif solver_type == "Magnetostatic":
            setup = app.create_setup(name="Setup1")
            setup.props["MaximumPasses"] = num_passes
            setup.update()
        elif solver_type == "EddyCurrent":
            setup = app.create_setup(name="Setup1")
            setup.props["MaximumPasses"] = num_passes
            setup.props["Frequency"] = f"{frequency_Hz}Hz"
            setup.update()
        else:
            return _err(f"未知求解器类型：{solver_type}")
        return _ok(f"求解设置已添加：{solver_type}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_simulation - 运行仿真
# ---------------------------------------------------------------------------

def run_simulation(setup_name: str = "Setup1") -> dict:
    """运行（求解）指定设置的仿真。"""
    try:
        app = _app()
        app.analyze_setup(setup_name)
        return _ok(f"仿真 '{setup_name}' 已完成")
    except Exception as e:
        return _err(str(e))
