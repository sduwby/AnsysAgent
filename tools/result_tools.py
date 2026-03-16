"""
结果工具：通过 PyAEDT 提取和格式化 Maxwell 仿真结果。
"""

from __future__ import annotations

import os
import re

from tools.maxwell_tools import _app, _get_model_state
from tools.utils import _ok, _err, append_warnings, create_report_and_get_data, ensure_parent_dir, ok_message


def _report_category(app) -> str:
    """
    根据当前 Maxwell 设计的求解类型自动选择报告类别。
    瞬态仿真返回 "Transient"，磁静态/涡流等返回 "Standard"。
    """
    try:
        sol_type = app.solution_type or ""
        if "Transient" in sol_type:
            return "Transient"
    except Exception:
        pass
    return "Standard"


def _parse_numeric_value(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        raise ValueError("empty value")
    text = str(value).strip()
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if not match:
        raise ValueError(f"cannot parse numeric value from {text!r}")
    return float(match.group(0))


def _require_series(data, expression: str, error_message: str):
    values = data.data_real(expression)
    if not values:
        raise ValueError(error_message)
    return values


def _require_motor_state(app, *, needs_motion: bool = False, needs_winding: bool = False) -> None:
    state = _get_model_state(app)
    if needs_motion and state.get("motion_configured") is False:
        raise ValueError("当前模型未配置旋转运动语义，无法严谨提取运动相关结果")
    if needs_winding and state.get("winding_defined") is False:
        raise ValueError("当前模型未配置绕组语义，无法严谨提取绕组相关结果")


def _require_solver_type(app, setup_name: str, allowed_solver_types: set[str]) -> None:
    state = _get_model_state(app)
    setup_info = state.get("setups", {}).get(setup_name)
    if not setup_info:
        return
    solver_type = setup_info.get("solver_type")
    if solver_type and solver_type not in allowed_solver_types:
        raise ValueError(
            f"求解设置 '{setup_name}' 的类型为 {solver_type}，"
            f"与当前结果提取不匹配；期望 {sorted(allowed_solver_types)}"
        )


def _require_solved_setup(app, setup_name: str) -> None:
    state = _get_model_state(app)
    setup_info = state.get("setups", {}).get(setup_name)
    if not setup_info:
        return
    if setup_info.get("solved") is False:
        raise ValueError(
            f"求解设置 '{setup_name}' 尚未完成求解；"
            "请先调用 run_simulation 再提取结果"
        )


# ---------------------------------------------------------------------------
# 工具：get_torque - 提取转矩
# ---------------------------------------------------------------------------

def get_torque(setup_name: str = "Setup1", sweep_name: str = "LastAdaptive") -> dict:
    """
    从瞬态或磁静态求解结果中提取平均转矩和转矩波形。

    返回:
        包含 avg_torque（Nm）和 waveform（[时间, 转矩] 列表）的字典
    """
    try:
        app = _app()
        _require_motor_state(app, needs_motion=True)
        _require_solver_type(app, setup_name, {"Transient", "Magnetostatic"})
        _require_solved_setup(app, setup_name)
        data = create_report_and_get_data(
            app.post,
            expressions=["Moving1.Torque"],
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category=_report_category(app),
            report_name="TorqueReport",
        )
        times = data.primary_sweep_values
        torques = _require_series(data, "Moving1.Torque", "未获取到转矩数据，请确认已完成求解并存在运动设置")
        avg = sum(torques) / len(torques)

        return _ok({
            "avg_torque_Nm": round(avg, 4),
            "waveform": list(zip(times, torques)),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_back_emf - 提取反电动势
# ---------------------------------------------------------------------------

def get_back_emf(
    phase_name: str = "PhaseA",
    setup_name: str = "Setup1",
    sweep_name: str = "LastAdaptive",
) -> dict:
    """提取指定相的反电动势波形。"""
    try:
        app = _app()
        _require_motor_state(app, needs_winding=True)
        _require_solver_type(app, setup_name, {"Transient"})
        _require_solved_setup(app, setup_name)
        data = create_report_and_get_data(
            app.post,
            expressions=[f"InducedVoltage({phase_name})"],
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category=_report_category(app),
            report_name="BackEMFReport",
        )
        times = data.primary_sweep_values
        voltages = _require_series(
            data,
            f"InducedVoltage({phase_name})",
            f"未获取到相 {phase_name} 的反电动势数据，请确认绕组和求解类型配置正确",
        )
        peak = max(abs(v) for v in voltages)

        return _ok({
            "phase": phase_name,
            "peak_emf_V": round(peak, 4),
            "waveform": list(zip(times, voltages)),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_flux_density - 获取磁通密度
# ---------------------------------------------------------------------------

def get_flux_density(setup_name: str = "Setup1", point: list[float] | None = None) -> dict:
    """
    获取指定点的磁通密度幅值（默认为气隙中心）。

    Args:
        point: [x, y, z]（mm）。未指定时默认 [0, 0, 0]。
    """
    try:
        app = _app()
        _require_solver_type(app, setup_name, {"Transient", "Magnetostatic", "EddyCurrent"})
        _require_solved_setup(app, setup_name)
        if point is None:
            point = [0, 0, 0]
        if len(point) != 3:
            return _err("point 必须为长度为 3 的坐标列表 [x, y, z]")
        field_val = app.post.evaluate_expression(
            expression="Mag_B",
            location=point,
            setup=setup_name,
        )
        if field_val is None:
            return _err("未获取到磁通密度值，请确认求解结果和采样点位置有效")
        return _ok({
            "point_mm": point,
            "flux_density_T": round(field_val, 6),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_losses - 获取损耗
# ---------------------------------------------------------------------------

def get_losses(setup_name: str = "Setup1", sweep_name: str = "LastAdaptive") -> dict:
    """获取平均铁耗（CoreLoss）和铜耗（OhmicLoss）。"""
    try:
        app = _app()
        _require_motor_state(app, needs_winding=True)
        _require_solver_type(app, setup_name, {"Transient", "EddyCurrent", "Magnetostatic"})
        _require_solved_setup(app, setup_name)
        expressions = ["CoreLoss", "OhmicLoss"]
        data = create_report_and_get_data(
            app.post,
            expressions=expressions,
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category=_report_category(app),
            report_name="LossReport",
        )
        core_loss = _require_series(data, "CoreLoss", "未获取到铁耗数据，请确认损耗求解已完成")
        ohmic_loss = _require_series(data, "OhmicLoss", "未获取到铜耗数据，请确认导体损耗求解已完成")
        avg_core = sum(core_loss) / len(core_loss)
        avg_ohmic = sum(ohmic_loss) / len(ohmic_loss)

        return _ok({
            "avg_core_loss_W": round(avg_core, 4),
            "avg_copper_loss_W": round(avg_ohmic, 4),
            "total_loss_W": round(avg_core + avg_ohmic, 4),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_results - 导出结果
# ---------------------------------------------------------------------------

def export_results(output_path: str, result_type: str = "torque") -> dict:
    """
    将仿真结果导出为 CSV 文件。

    Args:
        output_path: 输出 CSV 文件的完整路径
        result_type: "torque"（转矩）| "back_emf"（反电动势）| "losses"（损耗）
    """
    try:
        app = _app()
        report_name_map = {
            "torque": "TorqueReport",
            "back_emf": "BackEMFReport",
            "losses": "LossReport",
        }
        report_name = report_name_map.get(result_type)
        if not report_name:
            return _err(f"未知结果类型：{result_type}")

        # 检查报告是否已存在（需先调用对应的 get_* 工具）
        all_reports = app.post.all_report_names
        if report_name not in all_reports:
            return _err(f"报告 '{report_name}' 不存在，请先调用对应的 get_* 工具。")

        ensure_parent_dir(output_path)
        app.post.export_report_to_file(report_name, output_path)
        if not os.path.exists(output_path):
            return _err(f"结果导出后未生成文件: {output_path}")
        return _ok(ok_message(f"结果已导出到：{output_path}", output_path=output_path, result_type=result_type))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_inductance - 提取 Ld/Lq 电感
# ---------------------------------------------------------------------------

def get_inductance(
    setup_name: str = "Setup1",
    sweep_name: str = "LastAdaptive",
    phases: list[str] | None = None,
) -> dict:
    """
    提取 PMSM 的 d 轴电感 Ld 和 q 轴电感 Lq。

    使用 Maxwell 2D 磁静态/瞬态求解结果中相绕组磁链，通过 Park 变换
    （dq0 变换）计算：
        Ld = ψd / Id，Lq = ψq / Iq

    Args:
        setup_name: 求解设置名称
        sweep_name: 扫描/时间步名称
        phases: 三相名称列表，默认 ["PhaseA", "PhaseB", "PhaseC"]
    """
    try:
        app = _app()
        _require_motor_state(app, needs_winding=True)
        _require_solver_type(app, setup_name, {"Magnetostatic", "Transient"})
        _require_solved_setup(app, setup_name)
        if phases is None:
            phases = ["PhaseA", "PhaseB", "PhaseC"]

        # 提取各相自感（相—相电感矩阵对角元素）
        # L(PhaseA, PhaseA) 为 PhaseA 的自感，单位 H
        expressions = [f"L({p},{p})" for p in phases]
        data = create_report_and_get_data(
            app.post,
            expressions=expressions,
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_name="InductanceReport",
        )

        inductances = {}
        for expr, phase in zip(expressions, phases):
            vals = _require_series(data, expr, f"未获取到 {phase} 的自感数据，请确认相关表达式可用")
            avg_L = sum(vals) / len(vals)
            inductances[f"L_{phase}_H"] = round(avg_L, 9)

        # 近似 dq 电感（对称三相绕组）：
        # Ld ≈ Laa - Mab（直轴分量），Lq ≈ Laa + Mab（交轴分量）
        # 此处若仅有自感，用相自感均值估算 Ld≈Lq≈Lself
        l_vals = list(inductances.values())
        l_avg = sum(l_vals) / len(l_vals) if l_vals else None
        if l_avg is not None:
            inductances["Ld_approx_H"] = round(l_avg, 9)
            inductances["Lq_approx_H"] = round(l_avg, 9)
            inductances["dq_inductance_is_approximate"] = True
            inductances["dq_inductance_method"] = "phase_self_inductance_average"
            inductances["note"] = (
                "Ld/Lq 为相自感近似值；精确分析需在不同电流角下运行多次磁静态仿真"
            )

        return _ok(inductances)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_flux_linkage - 提取磁链
# ---------------------------------------------------------------------------

def get_flux_linkage(
    setup_name: str = "Setup1",
    sweep_name: str = "LastAdaptive",
    phases: list[str] | None = None,
) -> dict:
    """
    提取各相绕组磁链波形（ψA, ψB, ψC），并计算峰值和 dq 磁链分量。

    磁链是 PMSM 矢量控制的核心参数，用于计算 Ld、Lq 和空载磁链 ψ0。
    dq 变换：ψd = (2/3)[ψA·cos(θ) + ψB·cos(θ-2π/3) + ψC·cos(θ+2π/3)]

    Args:
        setup_name: 求解设置名称
        sweep_name: 扫描/时间步名称
        phases: 三相名称，默认 ["PhaseA", "PhaseB", "PhaseC"]
    """
    try:
        import math
        app = _app()
        _require_motor_state(app, needs_winding=True)
        _require_solver_type(app, setup_name, {"Transient", "Magnetostatic"})
        _require_solved_setup(app, setup_name)
        if phases is None:
            phases = ["PhaseA", "PhaseB", "PhaseC"]

        expressions = [f"FluxLinkage({p})" for p in phases]
        data = create_report_and_get_data(
            app.post,
            expressions=expressions,
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category=_report_category(app),
            report_name="FluxLinkageReport",
        )
        times = data.primary_sweep_values

        result = {}
        waveforms = {}
        peaks = {}
        for expr, phase in zip(expressions, phases):
            vals = _require_series(data, expr, f"未获取到 {phase} 的磁链数据，请确认绕组定义和求解结果")
            peaks[phase] = round(max(abs(v) for v in vals), 6)
            waveforms[phase] = list(zip(times, vals))

        result["peak_flux_linkage_Wb"] = peaks
        result["waveforms"] = waveforms

        # 简化 dq 变换（取第一时刻的快照，假设旋转坐标初始对准）
        if len(phases) == 3:
            try:
                first_vals = [data.data_real(f"FluxLinkage({p})")[0] for p in phases]
                theta = 0.0  # 初始电气角
                angles = [theta, theta - 2 * math.pi / 3, theta + 2 * math.pi / 3]
                psi_d = (2 / 3) * sum(v * math.cos(a) for v, a in zip(first_vals, angles))
                psi_q = (2 / 3) * sum(-v * math.sin(a) for v, a in zip(first_vals, angles))
                result["psi_d_Wb"] = round(psi_d, 6)
                result["psi_q_Wb"] = round(psi_q, 6)
                result["dq_snapshot_only"] = True
                result["dq_electrical_angle_deg"] = 0.0
                result["dq_note"] = "psi_d/psi_q 基于首个时刻快照和固定 0° 电角度，仅作快速参考"
            except Exception:
                pass

        return _ok(result)
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_cogging_torque - 提取齿槽转矩
# ---------------------------------------------------------------------------

def get_cogging_torque(
    setup_name: str = "Setup1",
    sweep_name: str = "LastAdaptive",
) -> dict:
    """
    提取 PMSM 的齿槽转矩（Cogging Torque）波形及谐波特性。

    齿槽转矩是零励磁（电流=0）时转子旋转产生的周期性转矩脉动，
    是电机 NVH 和控制精度的重要指标。

    需在零电流激励下运行参数化磁静态仿真（对转子位置扫描），
    再调用本工具提取结果。

    Args:
        setup_name: 求解设置名称（应为参数扫描基础设置）
        sweep_name: 参数扫描名称
    """
    try:
        app = _app()
        _require_motor_state(app, needs_motion=True)
        _require_solver_type(app, setup_name, {"Magnetostatic", "Transient"})
        _require_solved_setup(app, setup_name)
        data = create_report_and_get_data(
            app.post,
            expressions=["Moving1.Torque"],
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_name="CoggingTorqueReport",
        )
        positions = data.primary_sweep_values  # 转子位置（度）
        torques = data.data_real("Moving1.Torque")

        if not torques:
            return _err("未获取到转矩数据，请确认已运行零励磁参数化磁静态仿真")

        peak_to_peak = max(torques) - min(torques)
        avg = sum(torques) / len(torques)

        return _ok({
            "cogging_torque_peak_to_peak_Nm": round(peak_to_peak, 6),
            "avg_torque_Nm": round(avg, 6),
            "max_Nm": round(max(torques), 6),
            "min_Nm": round(min(torques), 6),
            "waveform": list(zip(positions, torques)),
            "num_points": len(torques),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_efficiency_map - 生成效率 MAP
# ---------------------------------------------------------------------------

def get_efficiency_map(
    speed_param: str = "Speed",
    current_param: str = "Current",
    setup_name: str = "Setup1",
    sweep_name: str = "",
    rated_voltage: float = 400.0,
) -> dict:
    """
    从二维参数扫描（转速 × 电流）结果中聚合生成效率 MAP。

    前置条件：已通过 create_2d_sweep 创建转速/电流双参数扫描并运行完成。
    效率计算：η = Pout / (Pout + Ploss) = T·ω / (T·ω + Pcore + Pcopper)

    Args:
        speed_param: 转速设计变量名（与 add_parametric_variable 一致）
        current_param: 电流设计变量名
        setup_name: 求解设置名称
        sweep_name: 参数扫描名称，空则使用最新扫描
        rated_voltage: 额定直流母线电压（V），用于计算 MTPA 参考线
    """
    try:
        app = _app()
        state = _get_model_state(app)
        sweep_metadata = state.get("parametric_sweeps", {}).get(sweep_name) if sweep_name else None
        if sweep_name:
            if not sweep_metadata:
                return _err(f"未找到参数扫描 '{sweep_name}' 的元数据，请先通过 create_2d_sweep 创建并运行该扫描")
            if sweep_metadata.get("type") != "2d":
                return _err(f"参数扫描 '{sweep_name}' 不是二维扫描，不能用于效率 MAP")
            if not sweep_metadata.get("analyzed"):
                return _err(f"参数扫描 '{sweep_name}' 尚未执行，请先调用 run_parametric_sweep")
            param_names = sweep_metadata.get("param_names", [])
            if speed_param not in param_names or current_param not in param_names:
                return _err(
                    f"参数扫描 '{sweep_name}' 不包含 speed/current 参数组合 "
                    f"({speed_param}, {current_param})；当前参数: {', '.join(param_names)}"
                )
            required_expressions = {"Moving1.Torque", "CoreLoss", "OhmicLoss"}
            configured_expressions = set(sweep_metadata.get("result_expressions", []))
            missing_expressions = sorted(required_expressions - configured_expressions)
            if missing_expressions:
                return _err(
                    f"参数扫描 '{sweep_name}' 缺少效率 MAP 所需结果表达式: "
                    f"{', '.join(missing_expressions)}"
                )
        # 获取当前扫描的所有设计点结果
        sweep_results = app.parametrics.get_variation_values(
            setup_name=setup_name,
            sweep_name=sweep_name or "",
        )

        efficiency_map = []
        skipped_points = 0
        for variation in sweep_results:
            try:
                if speed_param not in variation or current_param not in variation:
                    raise ValueError("missing speed/current parameter")
                speed_rpm = _parse_numeric_value(variation.get(speed_param, 0))
                current_A = _parse_numeric_value(variation.get(current_param, 0))
                # 转矩表达式名在 create_2d_sweep 中为 "Moving1.Torque"（带运动体前缀），
                # 此处兼容不同版本/配置下的多种可能键名
                torque_value = variation.get("Moving1.Torque") or variation.get("Torque")
                core_loss_value = variation.get("CoreLoss") or variation.get("Core Loss")
                copper_loss_value = variation.get("OhmicLoss") or variation.get("Ohmic Loss")
                if torque_value is None or core_loss_value is None or copper_loss_value is None:
                    raise ValueError("missing torque/loss expressions")
                torque_Nm = _parse_numeric_value(torque_value)
                core_loss_W = _parse_numeric_value(core_loss_value)
                copper_loss_W = _parse_numeric_value(copper_loss_value)

                # 输出功率 Pout = T * ω（W）
                omega = speed_rpm * 2 * 3.14159 / 60
                p_out = torque_Nm * omega
                p_loss = core_loss_W + copper_loss_W
                efficiency = p_out / (p_out + p_loss) * 100 if (p_out + p_loss) > 0 else 0.0

                efficiency_map.append({
                    "speed_rpm": speed_rpm,
                    "current_A": current_A,
                    "torque_Nm": round(torque_Nm, 3),
                    "efficiency_pct": round(efficiency, 2),
                    "p_out_W": round(p_out, 2),
                    "p_loss_W": round(core_loss_W + copper_loss_W, 2),
                })
            except Exception:
                skipped_points += 1
                continue

        if not efficiency_map:
            return _err("未能从参数扫描结果中提取效率数据，请确认 create_2d_sweep 已运行完成")

        # 找到最高效率工作点
        best = max(efficiency_map, key=lambda x: x["efficiency_pct"])

        return _ok({
            "num_operating_points": len(efficiency_map),
            "skipped_points": skipped_points,
            "peak_efficiency_pct": best["efficiency_pct"],
            "best_operating_point": best,
            "efficiency_map": efficiency_map,
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：check_demagnetization - 永磁体退磁校核
# ---------------------------------------------------------------------------

def check_demagnetization(
    setup_name: str = "Setup1",
    sweep_name: str = "LastAdaptive",
    magnet_objects: list[str] | None = None,
    operating_temperature_C: float = 120.0,
    safety_margin: float = 0.1,
) -> dict:
    """
    校核永磁体在极端工况下的退磁安全裕量。

    通过提取永磁体区域磁场强度 H 的最小值（最大退磁风险点），
    与该温度下的矫顽力 Hcb 对比，计算退磁安全系数。

    Args:
        setup_name: 求解设置名称（应为短路/过载工况仿真结果）
        sweep_name: 扫描名称
        magnet_objects: 永磁体几何体名称列表；None 则自动搜索含 "Magnet" 的对象
        operating_temperature_C: 工作温度（°C），用于温度修正 Hcb
        safety_margin: 退磁安全裕量阈值（0~1），低于此值为危险，默认 0.1（10%）
    """
    try:
        app = _app()
        _require_motor_state(app)
        _require_solver_type(app, setup_name, {"Transient", "Magnetostatic"})
        _require_solved_setup(app, setup_name)
        if not (0.0 <= safety_margin <= 1.0):
            return _err("safety_margin 必须在 0 到 1 之间")
        if operating_temperature_C < -273.15:
            return _err("operating_temperature_C 不能低于绝对零度")
        if operating_temperature_C >= 186.7:
            return _err("当前线性温度系数模型会导致 Hcb<=0，无法进行有效退磁校核")

        # 自动查找永磁体对象
        if magnet_objects is None:
            all_objects = getattr(app.modeler, "object_names", None)
            if callable(all_objects):
                all_objects = all_objects()
            if all_objects is None:
                all_objects = []
            magnet_objects = [obj for obj in all_objects if "Magnet" in obj or "PM" in obj]
        if not magnet_objects:
            return _err("未找到永磁体对象，请通过 magnet_objects 参数指定（通常命名含 'Magnet' 或 'PM'）")

        results = {}
        demagnetized = []
        successful_magnets = []
        failed_magnets = []

        for magnet_name in magnet_objects:
            try:
                # 提取磁体区域最小磁通密度 B（T）
                b_min = app.post.get_scalar_field_value(
                    "Mag_B",
                    "Minimum",
                    object_name=magnet_name,
                    setup_sweep_name=f"{setup_name} : {sweep_name}",
                )
                # 提取最大 H 场幅值（退磁方向）
                h_max = app.post.get_scalar_field_value(
                    "Mag_H",
                    "Maximum",
                    object_name=magnet_name,
                    setup_sweep_name=f"{setup_name} : {sweep_name}",
                )

                # NdFe35 典型矫顽力温度系数：约 -0.6%/°C（相对 20°C）
                # Hcb_20C（NdFe35）≈ 875 kA/m
                hcb_20c = 875000.0  # A/m
                temp_coeff = -0.006  # /°C，即每°C 降低 0.6%
                delta_t = operating_temperature_C - 20.0
                hcb_at_temp = hcb_20c * (1 + temp_coeff * delta_t)  # A/m
                if hcb_at_temp <= 0:
                    raise ValueError("温度修正后的 Hcb<=0，当前线性模型已失效")
                if b_min is None or h_max is None:
                    raise ValueError("未获取到完整的磁体场量数据")

                # 安全系数：1 - |H_max| / Hcb
                margin = 1.0 - (abs(h_max) / hcb_at_temp)
                is_safe = margin >= safety_margin

                results[magnet_name] = {
                    "min_B_T": round(b_min, 4),
                    "max_H_A_per_m": round(h_max, 1),
                    "Hcb_at_temp_kA_per_m": round(hcb_at_temp / 1000, 1),
                    "demagnetization_margin": round(margin, 4),
                    "is_safe": is_safe,
                    "status": "✓ 安全" if is_safe else "⚠ 退磁风险",
                }
                successful_magnets.append(magnet_name)
                if not is_safe:
                    demagnetized.append(magnet_name)
            except Exception as e:
                results[magnet_name] = {"error": str(e)}
                failed_magnets.append(magnet_name)

        if not successful_magnets:
            return _err("未能成功提取任何永磁体的退磁校核数据，请确认磁体对象、求解结果和场量表达式有效")

        overall_safe = len(demagnetized) == 0 and not failed_magnets
        result = {
            "overall_safe": overall_safe,
            "operating_temperature_C": operating_temperature_C,
            "safety_threshold": safety_margin,
            "at_risk_magnets": demagnetized,
            "evaluated_magnets": successful_magnets,
            "failed_magnets": failed_magnets,
            "magnet_results": results,
            "summary": (
                "所有永磁体退磁安全"
                if overall_safe
                else f"⚠ {len(demagnetized)} 个磁体存在退磁风险，{len(failed_magnets)} 个磁体校核失败"
            ),
        }
        warnings = []
        if failed_magnets:
            warnings.append(f"以下磁体未完成退磁校核: {', '.join(failed_magnets)}")
        return _ok(append_warnings(result, warnings))
    except Exception as e:
        return _err(str(e))
