"""
Result tools: extract and format Maxwell simulation results via PyAEDT.
"""

from __future__ import annotations
from typing import Any
from tools.maxwell_tools import _app, _ok, _err


# ---------------------------------------------------------------------------
# Tool: get_torque
# ---------------------------------------------------------------------------

def get_torque(setup_name: str = "Setup1", sweep_name: str = "LastAdaptive") -> dict:
    """
    Extract average torque and torque waveform from a transient or magnetostatic solution.

    Returns:
        dict with keys: avg_torque (Nm), waveform (list of [time, torque] pairs)
    """
    try:
        app = _app()
        # For transient: get time-domain torque
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
# Tool: get_back_emf
# ---------------------------------------------------------------------------

def get_back_emf(
    phase_name: str = "PhaseA",
    setup_name: str = "Setup1",
    sweep_name: str = "LastAdaptive",
) -> dict:
    """Extract back-EMF waveform for a given phase."""
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
# Tool: get_flux_density
# ---------------------------------------------------------------------------

def get_flux_density(setup_name: str = "Setup1", point: list[float] | None = None) -> dict:
    """
    Get the flux density magnitude at a given point (or default to air gap center).

    Args:
        point: [x, y, z] in mm. Defaults to [0, air_gap_mid, 0].
    """
    try:
        app = _app()
        if point is None:
            point = [0, 0, 0]  # Will be set to air gap mid by the agent if needed
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
# Tool: get_losses
# ---------------------------------------------------------------------------

def get_losses(setup_name: str = "Setup1", sweep_name: str = "LastAdaptive") -> dict:
    """Get iron loss and copper (ohmic) loss totals."""
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
# Tool: export_results
# ---------------------------------------------------------------------------

def export_results(output_path: str, result_type: str = "torque") -> dict:
    """
    Export simulation results to a CSV file.

    Args:
        output_path: full path to output CSV file
        result_type: "torque" | "back_emf" | "losses"
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
            return _err(f"Unknown result type: {result_type}")

        # Export existing report if available
        all_reports = app.post.all_report_names
        if report_name not in all_reports:
            return _err(f"Report '{report_name}' not found. Run the corresponding get_* tool first.")

        app.post.export_report_to_file(report_name, output_path)
        return _ok(f"Results exported to: {output_path}")
    except Exception as e:
        return _err(str(e))
