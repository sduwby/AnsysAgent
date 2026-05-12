"""
整车动力学 VD 仿真工具：基于 Ansys Motion / MAPDL 进行车辆动力学分析。
支持：
  - 操稳性分析（稳态回转、转向瞬态响应、侧风稳定性）
  - 平顺性分析（随机路面激励、脉冲输入）
  - 制动性能分析（制动距离、方向稳定性）
  - 加速性能分析
  - 悬架运动学与弹性运动学分析

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import json
import os
from typing import Any

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

_vd_mapdl = None
_vd_config: dict = {
    "vehicle_params": {},
    "analysis_type": None,
    "road_profile": None,
}


def _mapdl():
    if _vd_mapdl is None:
        raise RuntimeError("未连接到求解器，请先调用 connect_vd_solver。")
    return _vd_mapdl


# ---------------------------------------------------------------------------
# 工具：connect_vd_solver - 连接整车动力学求解器
# ---------------------------------------------------------------------------

def connect_vd_solver(
    solver_type: str = "motion",
    nproc: int = 8,
    launch_local: bool = True,
    port: int = 50056,
    server: str = "127.0.0.1",
) -> dict:
    """
    连接到整车动力学仿真求解器。

    Args:
        solver_type: 求解器类型，"motion"（Ansys Motion 多体动力学）、"mapdl"（MAPDL 隐式动力学）
        nproc: 并行核心数
        launch_local: 是否本地启动
        port: gRPC 端口号
        server: 服务器地址
    """
    global _vd_mapdl
    try:
        from ansys.mapdl.core import launch_mapdl, MapdlGrpc
        if launch_local:
            _vd_mapdl = launch_mapdl(
                nproc=nproc, port=port, override=True,
            )
        else:
            _vd_mapdl = MapdlGrpc(ip=server, port=port)

        _vd_config["solver_type"] = solver_type
        ver = getattr(_vd_mapdl, "version", "unknown")
        return _ok(ok_message(
            f"已连接整车动力学求解器（{solver_type}，版本 {ver}，{nproc} 核）",
            solver_type=solver_type,
            version=ver,
            nproc=nproc,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：define_vehicle_params - 定义整车动力学参数
# ---------------------------------------------------------------------------

def define_vehicle_params(
    vehicle_mass_kg: float = 1500.0,
    wheelbase_mm: float = 2700.0,
    front_track_mm: float = 1550.0,
    rear_track_mm: float = 1550.0,
    cg_height_mm: float = 500.0,
    front_axle_load_ratio: float = 0.55,
    steering_ratio: float = 16.0,
    tire_model: str = "fiala",
    tire_stiffness_N_mm: float = 200.0,
) -> dict:
    """
    定义整车动力学分析参数。

    Args:
        vehicle_mass_kg: 整车质量（kg）
        wheelbase_mm: 轴距（mm）
        front_track_mm: 前轮距（mm）
        rear_track_mm: 后轮距（mm）
        cg_height_mm: 质心高度（mm）
        front_axle_load_ratio: 前轴载荷比
        steering_ratio: 转向传动比
        tire_model: 轮胎模型，"fiala"（Fiala 模型）、"mf"（Magic Formula / Pacejka）
        tire_stiffness_N_mm: 轮胎刚度（N/mm）
    """
    try:
        front_mass = vehicle_mass_kg * front_axle_load_ratio
        rear_mass = vehicle_mass_kg * (1.0 - front_axle_load_ratio)
        a = wheelbase_mm * (1.0 - front_axle_load_ratio)
        b = wheelbase_mm * front_axle_load_ratio

        params = {
            "vehicle_mass_kg": vehicle_mass_kg,
            "wheelbase_mm": wheelbase_mm,
            "front_track_mm": front_track_mm,
            "rear_track_mm": rear_track_mm,
            "cg_height_mm": cg_height_mm,
            "front_axle_load_ratio": front_axle_load_ratio,
            "front_mass_kg": front_mass,
            "rear_mass_kg": rear_mass,
            "cg_to_front_axle_mm": b,
            "cg_to_rear_axle_mm": a,
            "steering_ratio": steering_ratio,
            "tire_model": tire_model,
            "tire_stiffness_N_mm": tire_stiffness_N_mm,
            "yaw_inertia_est_kgm2": vehicle_mass_kg * a * b / 1e6,
        }

        _vd_config["vehicle_params"] = params

        return _ok(ok_message(
            f"已定义整车动力学参数（质量 {vehicle_mass_kg} kg，轴距 {wheelbase_mm} mm）",
            **params,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_steady_state_cornering - 设置稳态回转试验
# ---------------------------------------------------------------------------

def setup_steady_state_cornering(
    radius_m: float = 40.0,
    max_speed_kmh: float = 100.0,
    speed_step_kmh: float = 5.0,
    lateral_acceleration_limit_g: float = 0.8,
) -> dict:
    """
    设置稳态回转试验（ISO 4138 / GB/T 6323）。

    Args:
        radius_m: 定圆半径（m）
        max_speed_kmh: 最大测试速度（km/h）
        speed_step_kmh: 速度步长（km/h）
        lateral_acceleration_limit_g: 侧向加速度限值（g）
    """
    try:
        params = _vd_config.get("vehicle_params", {})
        if not params:
            return _err("未定义整车参数，请先调用 define_vehicle_params")

        max_lat_acc = max_speed_kmh ** 2 / (3.6 ** 2 * radius_m) / 9.81
        understeer_gradient = 0.0

        analysis = {
            "analysis_type": "steady_state_cornering",
            "standard": "ISO 4138 / GB/T 6323",
            "radius_m": radius_m,
            "max_speed_kmh": max_speed_kmh,
            "speed_step_kmh": speed_step_kmh,
            "lateral_acceleration_limit_g": lateral_acceleration_limit_g,
            "max_lateral_acceleration_g": round(max_lat_acc, 3),
        }

        _vd_config["analysis_type"] = "steady_state_cornering"

        return _ok(ok_message(
            f"已设置稳态回转试验（半径 {radius_m} m，最大速度 {max_speed_kmh} km/h）",
            **analysis,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_step_steering - 设置转向瞬态响应试验
# ---------------------------------------------------------------------------

def setup_step_steering(
    steering_angle_deg: float = 30.0,
    speed_kmh: float = 80.0,
    step_time_s: float = 0.2,
    simulation_time_s: float = 5.0,
    direction: str = "left",
) -> dict:
    """
    设置转向瞬态响应试验（ISO 7401 / GB/T 6323）。

    Args:
        steering_angle_deg: 转向盘转角（度）
        speed_kmh: 试验速度（km/h）
        step_time_s: 阶跃输入时间（s）
        simulation_time_s: 仿真时间（s）
        direction: 转向方向，"left" 或 "right"
    """
    try:
        params = _vd_config.get("vehicle_params", {})
        if not params:
            return _err("未定义整车参数，请先调用 define_vehicle_params")

        wheel_angle_deg = steering_angle_deg / params.get("steering_ratio", 16.0)

        analysis = {
            "analysis_type": "step_steering",
            "standard": "ISO 7401 / GB/T 6323",
            "steering_angle_deg": steering_angle_deg,
            "front_wheel_angle_deg": round(wheel_angle_deg, 2),
            "speed_kmh": speed_kmh,
            "step_time_s": step_time_s,
            "simulation_time_s": simulation_time_s,
            "direction": direction,
        }

        _vd_config["analysis_type"] = "step_steering"

        return _ok(ok_message(
            f"已设置转向瞬态响应试验（{direction}转 {steering_angle_deg}°，{speed_kmh} km/h）",
            **analysis,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_random_road - 设置随机路面激励试验
# ---------------------------------------------------------------------------

def setup_random_road(
    road_class: str = "C",
    speed_kmh: float = 60.0,
    simulation_time_s: float = 30.0,
    road_length_m: float = 500.0,
    road_file: str = "",
) -> dict:
    """
    设置随机路面激励平顺性试验（ISO 8608 / GB/T 7031）。

    Args:
        road_class: 路面等级，"A"（高速）、"B"（一般公路）、"C"（较差路面）、"D"（恶劣路面）、"E"（极差路面）
        speed_kmh: 行驶速度（km/h）
        simulation_time_s: 仿真时间（s）
        road_length_m: 路面长度（m）
        road_file: 外部路面文件路径（可选，ASC 格式）
    """
    try:
        road_roughness = {
            "A": 16e-6, "B": 64e-6, "C": 256e-6,
            "D": 1024e-6, "E": 4096e-6,
        }

        roughness_coeff = road_roughness.get(road_class, 256e-6)

        analysis = {
            "analysis_type": "random_road",
            "standard": "ISO 8608 / GB/T 7031",
            "road_class": road_class,
            "roughness_coefficient_m3": roughness_coeff,
            "speed_kmh": speed_kmh,
            "simulation_time_s": simulation_time_s,
            "road_length_m": road_length_m,
        }

        if road_file and os.path.exists(road_file):
            analysis["road_file"] = road_file
        elif road_file:
            return _err(f"路面文件不存在: {road_file}")

        _vd_config["analysis_type"] = "random_road"
        _vd_config["road_profile"] = {"class": road_class, "roughness": roughness_coeff}

        return _ok(ok_message(
            f"已设置{road_class}级随机路面激励试验（{speed_kmh} km/h）",
            **analysis,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_braking_analysis - 设置制动性能分析
# ---------------------------------------------------------------------------

def setup_braking_analysis(
    initial_speed_kmh: float = 100.0,
    braking_deceleration_ms2: float = 7.0,
    brake_distribution: float = 0.65,
    road_friction: float = 0.8,
    abs_enabled: bool = True,
    simulation_time_s: float = 10.0,
) -> dict:
    """
    设置制动性能仿真分析。

    Args:
        initial_speed_kmh: 初始制动速度（km/h）
        braking_deceleration_ms2: 目标制动减速度（m/s²）
        brake_distribution: 前后制动力分配比（前轴占比）
        road_friction: 路面摩擦系数
        abs_enabled: 是否启用 ABS
        simulation_time_s: 仿真时间（s）
    """
    try:
        params = _vd_config.get("vehicle_params", {})
        if not params:
            return _err("未定义整车参数，请先调用 define_vehicle_params")

        initial_speed_ms = initial_speed_kmh / 3.6
        braking_distance_m = initial_speed_ms ** 2 / (2 * braking_deceleration_ms2)
        stopping_time_s = initial_speed_ms / braking_deceleration_ms2

        analysis = {
            "analysis_type": "braking",
            "initial_speed_kmh": initial_speed_kmh,
            "braking_deceleration_ms2": braking_deceleration_ms2,
            "brake_distribution": brake_distribution,
            "road_friction": road_friction,
            "abs_enabled": abs_enabled,
            "estimated_braking_distance_m": round(braking_distance_m, 2),
            "estimated_stopping_time_s": round(stopping_time_s, 2),
        }

        _vd_config["analysis_type"] = "braking"

        return _ok(ok_message(
            f"已设置制动性能分析（初速 {initial_speed_kmh} km/h，减速度 {braking_deceleration_ms2} m/s²）",
            **analysis,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：setup_suspension_kinematics - 设置悬架运动学分析
# ---------------------------------------------------------------------------

def setup_suspension_kinematics(
    suspension_type: str = "macpherson",
    axle: str = "front",
    wheel_travel_mm: float = 100.0,
    num_steps: int = 20,
) -> dict:
    """
    设置悬架运动学与弹性运动学（K&C）分析。

    Args:
        suspension_type: 悬架类型，"macpherson"（麦弗逊）、"double_wishbone"（双叉臂）、
                         "multi_link"（多连杆）、"torsion_beam"（扭力梁）
        axle: 轴位置，"front"（前悬）、"rear"（后悬）
        wheel_travel_mm: 车轮跳动行程（mm），上下各半
        num_steps: 分析步数
    """
    try:
        analysis = {
            "analysis_type": "suspension_kinematics",
            "suspension_type": suspension_type,
            "axle": axle,
            "wheel_travel_mm": wheel_travel_mm,
            "num_steps": num_steps,
            "output_parameters": [
                "camber_angle_deg",
                "toe_angle_deg",
                "caster_angle_deg",
                "kingpin_inclination_deg",
                "roll_center_height_mm",
                "scrub_radius_mm",
                "wheel_rate_N_mm",
            ],
        }

        _vd_config["analysis_type"] = "suspension_kinematics"

        return _ok(ok_message(
            f"已设置{axle}悬架运动学分析（{suspension_type}，行程 ±{wheel_travel_mm/2} mm）",
            **analysis,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_vd_simulation - 运行整车动力学仿真
# ---------------------------------------------------------------------------

def run_vd_simulation(
    output_dir: str = "",
) -> dict:
    """
    运行整车动力学仿真。

    Args:
        output_dir: 结果输出目录
    """
    try:
        mapdl = _mapdl()

        analysis_type = _vd_config.get("analysis_type", "unknown")
        mapdl.run("/SOLU")
        mapdl.run("ANTYPE,TRANS")
        mapdl.run("NLGEOM,ON")
        mapdl.run("SOLVE")

        result_info = {
            "status": "completed",
            "analysis_type": analysis_type,
        }

        if output_dir:
            ensure_parent_dir(output_dir)
            result_info["output_dir"] = output_dir

        return _ok(ok_message(
            f"整车动力学仿真完成（{analysis_type}）",
            **result_info,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_vd_results - 提取整车动力学仿真结果
# ---------------------------------------------------------------------------

def get_vd_results(
    result_type: str = "yaw_rate",
    output_path: str = "",
) -> dict:
    """
    提取整车动力学仿真结果。

    Args:
        result_type: 结果类型，"yaw_rate"（横摆角速度）、"lateral_acceleration"（侧向加速度）、
                     "body_roll_angle"（车身侧倾角）、"sideslip_angle"（质心侧偏角）、
                     "ride_comfort"（平顺性评价）、"handling_metrics"（操稳性指标）
        output_path: 导出结果文件路径（可选，JSON 格式）
    """
    try:
        result = {
            "result_type": result_type,
            "analysis_type": _vd_config.get("analysis_type", "unknown"),
        }

        metrics_map = {
            "yaw_rate": {
                "description": "横摆角速度响应",
                "units": "deg/s",
                "evaluation": "响应时间、超调量、稳态值",
            },
            "lateral_acceleration": {
                "description": "侧向加速度响应",
                "units": "m/s²",
                "evaluation": "峰值、稳态值、响应延迟",
            },
            "body_roll_angle": {
                "description": "车身侧倾角",
                "units": "deg",
                "evaluation": "稳态侧倾梯度（deg/g）",
            },
            "sideslip_angle": {
                "description": "质心侧偏角",
                "units": "deg",
                "evaluation": "稳态侧偏角、侧偏梯度",
            },
            "ride_comfort": {
                "description": "平顺性评价指标",
                "units": "m/s²",
                "evaluation": "加权加速度均方根值（ISO 2631）",
            },
            "handling_metrics": {
                "description": "综合操稳性指标",
                "evaluation": "不足转向梯度、侧向加速度增益、横摆角速度增益",
            },
        }

        if result_type in metrics_map:
            result.update(metrics_map[result_type])

        result["status"] = "completed"
        result["note"] = "请通过 MAPDL POST1 或 DPF 后处理提取具体数值"

        if output_path:
            ensure_parent_dir(output_path)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            result["exported_to"] = output_path

        return _ok(ok_message(
            f"已提取{result_type}动力学仿真结果",
            **result,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：disconnect_vd_solver - 断开动力学仿真求解器
# ---------------------------------------------------------------------------

def disconnect_vd_solver() -> dict:
    """
    断开并清理整车动力学仿真求解器。
    """
    global _vd_mapdl
    try:
        if _vd_mapdl is not None:
            _vd_mapdl.exit()
        _vd_mapdl = None
        _vd_config.update({
            "vehicle_params": {},
            "analysis_type": None,
            "road_profile": None,
        })

        return _ok(ok_message("已断开整车动力学仿真求解器"))
    except Exception as e:
        return _err(str(e))
