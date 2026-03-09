"""
Maxwell tools: PyAEDT wrappers for motor EM simulation operations.
Each function returns a dict with 'success', 'result', and optional 'error'.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# PyAEDT is imported lazily to allow the module to load even without Ansys installed.
_aedt_app = None  # global AEDT Maxwell2d/3d instance


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _app():
    """Return the active Maxwell app, raise if not connected."""
    if _aedt_app is None:
        raise RuntimeError("Not connected to AEDT. Call connect_aedt first.")
    return _aedt_app


def _ok(result: Any = None) -> dict:
    return {"success": True, "result": result}


def _err(msg: str) -> dict:
    return {"success": False, "error": msg}


# ---------------------------------------------------------------------------
# Tool: connect_aedt
# ---------------------------------------------------------------------------

def connect_aedt(version: str = "2024.1", is_3d: bool = False, non_graphical: bool = False) -> dict:
    """
    Connect to a running AEDT instance or launch a new one.

    Args:
        version: AEDT version string, e.g. "2024.1"
        is_3d: True for Maxwell 3D, False for Maxwell 2D
        non_graphical: Run without GUI (batch mode)
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
        return _ok(f"Connected to AEDT {version} ({'Maxwell 3D' if is_3d else 'Maxwell 2D'})")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Tool: create_maxwell_project
# ---------------------------------------------------------------------------

def create_maxwell_project(project_name: str, design_name: str = "Motor") -> dict:
    """Create a new Maxwell project and design."""
    try:
        app = _app()
        app.save_project(project_name)
        app.design_name = design_name
        return _ok(f"Project '{project_name}' created with design '{design_name}'")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Tool: create_motor_geometry
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
    Create a simplified PMSM (surface-mounted) geometry in Maxwell 2D.

    All dimensions in mm. Uses PyAEDT primitives.
    """
    try:
        app = _app()
        modeler = app.modeler

        # Stator yoke (annulus)
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

        # Rotor yoke (annulus)
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

        # Air gap region
        air_gap_outer = rotor_outer_radius + (stator_inner_radius - rotor_outer_radius) / 2
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

        # Surface magnets (simplified: one magnet per pole, rectangular arc approximation)
        import math
        pole_angle = 360.0 / num_poles
        magnet_arc = pole_angle * 0.85  # magnet covers 85% of pole pitch
        for i in range(num_poles):
            start_angle = i * pole_angle - magnet_arc / 2
            name = f"Magnet_{i+1}"
            modeler.create_circle_arc_3points(
                arc_beginning=[
                    (rotor_outer_radius) * math.cos(math.radians(start_angle)),
                    (rotor_outer_radius) * math.sin(math.radians(start_angle)),
                    0,
                ],
                arc_end=[
                    (rotor_outer_radius) * math.cos(math.radians(start_angle + magnet_arc)),
                    (rotor_outer_radius) * math.sin(math.radians(start_angle + magnet_arc)),
                    0,
                ],
                arc_center=[0, 0, 0],
                name=name,
                material="NdFe35",
            )

        return _ok(
            f"Motor geometry created: {num_slots} slots, {num_poles} poles, "
            f"stator OD={stator_outer_radius*2}mm, rotor OD={rotor_outer_radius*2}mm"
        )
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Tool: assign_material
# ---------------------------------------------------------------------------

def assign_material(object_name: str, material_name: str) -> dict:
    """Assign a material to a geometry object."""
    try:
        app = _app()
        obj = app.modeler.get_object_from_name(object_name)
        obj.material_name = material_name
        return _ok(f"Assigned material '{material_name}' to '{object_name}'")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Tool: setup_winding
# ---------------------------------------------------------------------------

def setup_winding(
    phase_name: str,
    conductor_names: list[str],
    current_amplitude: float,
    frequency: float = 0,
    phase_angle: float = 0.0,
) -> dict:
    """
    Set up a winding phase excitation.

    Args:
        phase_name: e.g. "PhaseA"
        conductor_names: list of slot conductor object names
        current_amplitude: peak current in A
        frequency: electrical frequency in Hz (0 for magnetostatic)
        phase_angle: phase angle in degrees
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
        return _ok(f"Winding '{phase_name}' configured: {current_amplitude}A @ {phase_angle}°")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Tool: add_solution_setup
# ---------------------------------------------------------------------------

def add_solution_setup(
    solver_type: str = "Transient",
    stop_time: float = 0.02,
    time_step: float = 0.0001,
    num_passes: int = 10,
) -> dict:
    """
    Add a solution setup.

    Args:
        solver_type: "Transient" | "Magnetostatic" | "EddyCurrent"
        stop_time: simulation stop time in seconds (transient only)
        time_step: time step in seconds (transient only)
        num_passes: adaptive mesh passes
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
            setup.update()
        else:
            return _err(f"Unknown solver type: {solver_type}")
        return _ok(f"Solution setup added: {solver_type}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# Tool: run_simulation
# ---------------------------------------------------------------------------

def run_simulation(setup_name: str = "Setup1") -> dict:
    """Analyze (run) the specified setup."""
    try:
        app = _app()
        app.analyze_setup(setup_name)
        return _ok(f"Simulation '{setup_name}' completed successfully")
    except Exception as e:
        return _err(str(e))
