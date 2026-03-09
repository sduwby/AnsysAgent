"""
结果工具：通过 PyAEDT 提取和格式化 Maxwell 仿真结果。
"""

from __future__ import annotations
from typing import Any
from tools.maxwell_tools import _app, _ok, _err


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
        report = app.post.create_report(
            expressions=["Moving1.Torque"],
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category="Transient",
            report_name="TorqueReport",
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
        report = app.post.create_report(
            expressions=[f"InducedVoltage({phase_name})"],
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category="Transient",
            report_name="BackEMFReport",
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
        report = app.post.create_report(
            expressions=expressions,
            setup_sweep_name=f"{setup_name} : {sweep_name}",
            report_category="Transient",
            report_name="LossReport",
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

