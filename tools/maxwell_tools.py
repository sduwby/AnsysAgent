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
    import os
    try:
        app = _app()
        # 确保 project_name 是带 .aedt 扩展名的合法路径
        # save_project() 保存当前（新建）项目到指定路径，起到命名+持久化的作用
        if not project_name.endswith(".aedt"):
            project_name = project_name + ".aedt"
        if not os.path.isabs(project_name):
            project_name = os.path.join(os.getcwd(), project_name)
        app.save_project(project_name)
        # 重命名当前激活设计
        if app.design_list:
            app.active_design.name = design_name
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
        # subtract 后刷新对象缓存，确保跨 PyAEDT 版本均能通过原名找到对象
        modeler.refresh_all_ids()
        stator_obj = modeler.get_object_from_name("Stator_Outer")
        if stator_obj is None:
            raise RuntimeError("subtract 后未找到 Stator_Outer，请检查 PyAEDT 版本兼容性")
        stator_obj.name = "Stator"

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
        modeler.refresh_all_ids()
        rotor_obj = modeler.get_object_from_name("Rotor_Outer")
        if rotor_obj is None:
            raise RuntimeError("subtract 后未找到 Rotor_Outer，请检查 PyAEDT 版本兼容性")
        rotor_obj.name = "Rotor"

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
        app.assign_winding(
            coil_terminals=[phase_name],
            winding_name=phase_name,
            winding_type="Current",
            current_value=current_expr,
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
        return _ok("，".join(parts))
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
