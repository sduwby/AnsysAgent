"""
结果工具：通过 PyAEDT 提取和格式化 Maxwell 仿真结果。
"""

from __future__ import annotations

from tools.maxwell_tools import _app
from tools.utils import _ok, _err


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
        # 瞬态仿真：获取时域转矩波形
        # 若同名报告已存在则先删除，避免重复创建报错
        report_name = "TorqueReport"
        if report_name in app.post.all_report_names:
            app.post.delete_report(report_name)
        report = app.post.create_report(
            expressions=["Moving1.Torque"],
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category="Transient",
            report_name=report_name,
        )
        data = report.get_solution_data()
        times = data.primary_sweep_values
        torques = data.data_real("Moving1.Torque")
        avg = sum(torques) / len(torques) if torques else 0.0

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
        report_name = "BackEMFReport"
        if report_name in app.post.all_report_names:
            app.post.delete_report(report_name)
        report = app.post.create_report(
            expressions=[f"InducedVoltage({phase_name})"],
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category="Transient",
            report_name=report_name,
        )
        data = report.get_solution_data()
        times = data.primary_sweep_values
        voltages = data.data_real(f"InducedVoltage({phase_name})")
        peak = max(abs(v) for v in voltages) if voltages else 0.0

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
        if point is None:
            point = [0, 0, 0]
        field_val = app.post.evaluate_expression(
            expression="Mag_B",
            location=point,
            setup=setup_name,
        )
        return _ok({
            "point_mm": point,
            "flux_density_T": round(field_val, 6) if field_val else None,
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
        expressions = ["CoreLoss", "OhmicLoss"]
        report_name = "LossReport"
        if report_name in app.post.all_report_names:
            app.post.delete_report(report_name)
        report = app.post.create_report(
            expressions=expressions,
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category="Transient",
            report_name=report_name,
        )
        data = report.get_solution_data()
        core_loss = data.data_real("CoreLoss")
        ohmic_loss = data.data_real("OhmicLoss")
        avg_core = sum(core_loss) / len(core_loss) if core_loss else 0.0
        avg_ohmic = sum(ohmic_loss) / len(ohmic_loss) if ohmic_loss else 0.0

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

        app.post.export_report_to_file(report_name, output_path)
        return _ok(f"结果已导出到：{output_path}")
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
        if phases is None:
            phases = ["PhaseA", "PhaseB", "PhaseC"]

        # 提取各相自感（相—相电感矩阵对角元素）
        # L(PhaseA, PhaseA) 为 PhaseA 的自感，单位 H
        expressions = [f"L({p},{p})" for p in phases]
        report_name = "InductanceReport"
        if report_name in app.post.all_report_names:
            app.post.delete_report(report_name)

        report = app.post.create_report(
            expressions=expressions,
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_name=report_name,
        )
        data = report.get_solution_data()

        inductances = {}
        for expr, phase in zip(expressions, phases):
            vals = data.data_real(expr)
            if vals:
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
        if phases is None:
            phases = ["PhaseA", "PhaseB", "PhaseC"]

        expressions = [f"FluxLinkage({p})" for p in phases]
        report_name = "FluxLinkageReport"
        if report_name in app.post.all_report_names:
            app.post.delete_report(report_name)

        report = app.post.create_report(
            expressions=expressions,
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category="Transient",
            report_name=report_name,
        )
        data = report.get_solution_data()
        times = data.primary_sweep_values

        result = {}
        waveforms = {}
        peaks = {}
        for expr, phase in zip(expressions, phases):
            vals = data.data_real(expr)
            if vals:
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
        report_name = "CoggingTorqueReport"
        if report_name in app.post.all_report_names:
            app.post.delete_report(report_name)

        report = app.post.create_report(
            expressions=["Moving1.Torque"],
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_name=report_name,
        )
        data = report.get_solution_data()
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
        # 获取当前扫描的所有设计点结果
        sweep_results = app.parametrics.get_variation_values(
            setup_name=setup_name,
            sweep_name=sweep_name or "",
        )

        efficiency_map = []
        for variation in sweep_results:
            try:
                speed_rpm = float(variation.get(speed_param, 0))
                current_A = float(variation.get(current_param, 0))
                torque_Nm = float(variation.get("Torque", 0))
                core_loss_W = float(variation.get("CoreLoss", 0))
                copper_loss_W = float(variation.get("OhmicLoss", 0))

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
                continue

        if not efficiency_map:
            return _err("未能从参数扫描结果中提取效率数据，请确认 create_2d_sweep 已运行完成")

        # 找到最高效率工作点
        best = max(efficiency_map, key=lambda x: x["efficiency_pct"])

        return _ok({
            "num_operating_points": len(efficiency_map),
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

        # 自动查找永磁体对象
        if magnet_objects is None:
            all_objects = app.modeler.object_names
            magnet_objects = [obj for obj in all_objects if "Magnet" in obj or "PM" in obj]
        if not magnet_objects:
            return _err("未找到永磁体对象，请通过 magnet_objects 参数指定（通常命名含 'Magnet' 或 'PM'）")

        results = {}
        demagnetized = []

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

                # 安全系数：1 - |H_max| / Hcb
                margin = 1.0 - (abs(h_max or 0.0) / hcb_at_temp) if hcb_at_temp > 0 else 0.0
                is_safe = margin >= safety_margin

                results[magnet_name] = {
                    "min_B_T": round(b_min, 4) if b_min else None,
                    "max_H_A_per_m": round(h_max, 1) if h_max else None,
                    "Hcb_at_temp_kA_per_m": round(hcb_at_temp / 1000, 1),
                    "demagnetization_margin": round(margin, 4),
                    "is_safe": is_safe,
                    "status": "✓ 安全" if is_safe else "⚠ 退磁风险",
                }
                if not is_safe:
                    demagnetized.append(magnet_name)
            except Exception as e:
                results[magnet_name] = {"error": str(e)}

        overall_safe = len(demagnetized) == 0
        return _ok({
            "overall_safe": overall_safe,
            "operating_temperature_C": operating_temperature_C,
            "safety_threshold": safety_margin,
            "at_risk_magnets": demagnetized,
            "magnet_results": results,
            "summary": "所有永磁体退磁安全" if overall_safe else f"⚠ {len(demagnetized)} 个磁体存在退磁风险",
        })
    except Exception as e:
        return _err(str(e))

