import inspect
import os
import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path

dotenv_stub = types.ModuleType("dotenv")
dotenv_stub.set_key = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", dotenv_stub)

rich_stub = types.ModuleType("rich")
rich_console_stub = types.ModuleType("rich.console")
rich_panel_stub = types.ModuleType("rich.panel")
rich_prompt_stub = types.ModuleType("rich.prompt")


class _DummyConsole:
    def print(self, *args, **kwargs):
        return None


class _DummyPanel:
    def __init__(self, *args, **kwargs):
        pass


class _DummyPrompt:
    @staticmethod
    def ask(*args, **kwargs):
        return ""


rich_console_stub.Console = _DummyConsole
rich_panel_stub.Panel = _DummyPanel
rich_prompt_stub.Prompt = _DummyPrompt
sys.modules.setdefault("rich", rich_stub)
sys.modules.setdefault("rich.console", rich_console_stub)
sys.modules.setdefault("rich.panel", rich_panel_stub)
sys.modules.setdefault("rich.prompt", rich_prompt_stub)

from agent import config_manager, tool_definitions
from tools import circuit_tools, coupling_tools, dynamic_reporting_tools, fluent_tools, icepak_tools, mapdl_tools, maxwell_tools, mechanical_tools, motorcad_tools, project_tools, report_tools, rmxprt_tools, sweep_tools
from tools import result_tools, utils as tool_utils, visualization_tools


class DummySolutionData:
    def __init__(self, core_loss, ohmic_loss):
        self._core_loss = core_loss
        self._ohmic_loss = ohmic_loss

    def data_real(self, expression):
        if expression == "CoreLoss":
            return self._core_loss
        if expression == "OhmicLoss":
            return self._ohmic_loss
        return []


class DummyVariableManager:
    def __init__(self, variables=None):
        self.variables = dict(variables or {})
        self.updated = {}

    def set_variable(self, name, value):
        self.updated[name] = value


class DummyMaxwellPost:
    def __init__(self, core_loss=None, ohmic_loss=None):
        self._core_loss = core_loss or [10.0]
        self._ohmic_loss = ohmic_loss or [5.0]

    def get_solution_data(self, expressions=None, setup_sweep_name=None):
        return DummySolutionData(self._core_loss, self._ohmic_loss)


class DummyMaxwellApp:
    def __init__(self, variables=None, core_loss=None, ohmic_loss=None):
        self.design_name = "Motor"
        self.variable_manager = DummyVariableManager(variables)
        self.post = DummyMaxwellPost(core_loss=core_loss, ohmic_loss=ohmic_loss)
        self.analyzed = []

    def analyze_setup(self, setup_name):
        self.analyzed.append(setup_name)


class DummyIcepakPost:
    def get_scalar_field_value(self, field, operation, object_name=None):
        values = {
            "Winding": 120.0,
            "Stator": 90.0,
            "Rotor": 70.0,
        }
        return values.get(object_name)


class DummySetup:
    def __init__(self, name):
        self.name = name
        self.props = {}

    def update(self):
        return None


class DummyModeler:
    def __init__(self, available_objects):
        self.available_objects = set(available_objects)

    def set_working_coordinate_system(self, name):
        return None

    def get_object_from_name(self, name):
        return name if name in self.available_objects else None


class DummyIcepakApp:
    def __init__(self, available_objects=None, fail_assign=False):
        if available_objects is None:
            available_objects = {"Winding", "Stator", "Rotor"}
        self.available_objects = available_objects
        self.fail_assign = fail_assign
        self.assigned = []
        self.post = DummyIcepakPost()
        self.modeler = DummyModeler(self.available_objects)
        self.setups = []

    def assign_source(self, obj_name, source_type, thermal_condition=None, assignment_value=None):
        if self.fail_assign:
            raise RuntimeError("assign failed")
        self.assigned.append((obj_name, assignment_value))

    def assign_free_opening(self, objects, temperature=None):
        return None

    def assign_openings(self, objects, boundary_type=None, temperature=None):
        return None

    def create_setup(self, name):
        setup = DummySetup(name)
        self.setups.append(setup)
        return setup

    def analyze_setup(self, setup_name):
        return None


class DummyProjectApp:
    def __init__(self, design_list):
        self.design_list = design_list
        self.project_name = "DemoProject"
        self.project_file = "/tmp/demo.aedt"
        self.design_name = design_list[0] if design_list else ""


class DummyProjectAppMethod:
    def __init__(self, design_list):
        self._design_list = design_list

    def design_list(self):
        return self._design_list


class DummyReportData:
    def __init__(self, values_by_expr, sweep_values=None):
        self._values_by_expr = values_by_expr
        self.primary_sweep_values = sweep_values or [0.0, 1.0]

    def data_real(self, expression):
        return self._values_by_expr.get(expression, [])


class DummyReport:
    def __init__(self, data):
        self._data = data

    def get_solution_data(self):
        return self._data


class DummyPost:
    def __init__(self, data, reports=None):
        self._data = data
        self.all_report_names = list(reports or [])
        self.deleted = []
        self.created = []
        self.exported = []

    def delete_report(self, name):
        self.deleted.append(name)

    def create_report(self, **kwargs):
        self.created.append(kwargs)
        return DummyReport(self._data)

    def export_report_to_file(self, report_name, output_path):
        self.exported.append((report_name, output_path))


class DummyCircuitComponent:
    def __init__(self):
        self.parameters = {}


class DummyCircuitSchematic:
    def __init__(self, fail_wires=False):
        self.fail_wires = fail_wires
        self.components = []
        self.wires = []

    def add_component(self, *args, **kwargs):
        self.components.append((args, kwargs))
        return DummyCircuitComponent()

    def create_wire(self, points):
        if self.fail_wires:
            raise RuntimeError("wire failed")
        self.wires.append(points)


class DummyCircuitModeler:
    def __init__(self, fail_wires=False):
        self.schematic = DummyCircuitSchematic(fail_wires=fail_wires)


class DummyCircuitApp:
    def __init__(self, fail_wires=False):
        self.modeler = DummyCircuitModeler(fail_wires=fail_wires)


class DummyVisualizationPost:
    def __init__(self):
        self.oModule = types.SimpleNamespace(FitAll=lambda: None)
        self.exports = []

    def SetActiveVariation(self, name, value):
        return None

    def export_field_image_to_file(self, plot_name=None, file_path=None, width=None, height=None):
        with open(file_path, "wb") as f:
            f.write(b"png")
        self.exports.append((plot_name, file_path, width, height))


class DummyVisualizationApp:
    def __init__(self):
        self.post = DummyVisualizationPost()


class DummyReportExportPost:
    def __init__(self):
        self.all_report_names = ["R1"]
        self.csv_exports = []
        self.jpg_exports = []

    def export_report_to_file(self, name, path):
        self.csv_exports.append((name, path))

    def export_report_to_jpg(self, name, path):
        raise RuntimeError("jpg unsupported")


class DummyMechanicalScriptApp:
    def __init__(self):
        self.scripts = []

    def run_python_script(self, script):
        self.scripts.append(script)
        return None


class DummySweepSolutionData:
    def __init__(self, values, primary_sweep_values=None):
        self._values = values
        self.primary_sweep_values = primary_sweep_values or []

    def data_real(self, expression):
        return self._values.get(expression, [])


class DummyMaxwellModeler:
    def __init__(self, existing_objects=None):
        self.existing_objects = set(existing_objects or [])
        self.objects = {
            name: types.SimpleNamespace(name=name)
            for name in self.existing_objects
        }

    def get_object_from_name(self, name):
        return self.objects.get(name)

    def create_circle(self, position=None, radius=None, num_sides=None, name=None, material=None):
        self.existing_objects.add(name)
        self.objects.setdefault(name, types.SimpleNamespace(name=name))

    def subtract(self, blank, tool, keep_originals=False):
        if not keep_originals:
            self.existing_objects.discard(tool)
            self.objects.pop(tool, None)

    def refresh_all_ids(self):
        return None

    def create_polyline(self, position_list=None, cover_surface=None, name=None, matname=None):
        self.existing_objects.add(name)
        self.objects.setdefault(name, types.SimpleNamespace(name=name))


class RegressionTests(unittest.TestCase):
    def test_load_llm_config_uses_provider_specific_key(self):
        env = {
            "LLM_PROVIDER": "openai",
            "LLM_API_KEY": "",
            "LLM_MODEL": "",
            "LLM_API_KEY_OPENAI": "provider-key",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = config_manager.load_llm_config()
        self.assertEqual(cfg.provider, "openai")
        self.assertEqual(cfg.api_key, "provider-key")

    def test_list_designs_accepts_design_list_property(self):
        app = DummyProjectApp(["Design1", "Design2"])
        with patch("tools.project_tools._app", return_value=app):
            result = project_tools.list_designs()
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["count"], 2)

    def test_get_design_names_accepts_design_list_method(self):
        app = DummyProjectAppMethod(["DesignA", "DesignB"])
        self.assertEqual(tool_utils.get_design_names(app), ["DesignA", "DesignB"])

    def test_setup_motor_thermal_fails_when_no_sources_assigned(self):
        app = DummyIcepakApp(available_objects=set())
        with patch("tools.icepak_tools._app", return_value=app):
            result = icepak_tools.setup_motor_thermal(10.0, 20.0)
        self.assertFalse(result["success"])
        self.assertIn("未能成功分配任何热源", result["error"])

    def test_assign_power_sources_reports_partial_success(self):
        app = DummyIcepakApp(available_objects={"Winding", "Rotor"}, fail_assign=False)
        result = tool_utils.assign_power_sources(app, {
            "Winding": 10.0,
            "Stator": 20.0,
            "Rotor": 5.0,
        })
        self.assertEqual(result["missing"], ["Stator"])
        self.assertEqual(len(result["assigned"]), 2)
        self.assertEqual(result["errors"], [])

    def test_create_report_and_get_data_deletes_existing_report(self):
        data = DummyReportData({"Expr": [1.0, 2.0]})
        post = DummyPost(data, reports=["DemoReport"])
        result = tool_utils.create_report_and_get_data(
            post,
            expressions=["Expr"],
            setup_sweep_name="Setup1 : LastAdaptive",
            report_name="DemoReport",
        )
        self.assertIs(result, data)
        self.assertEqual(post.deleted, ["DemoReport"])
        self.assertEqual(post.created[0]["report_name"], "DemoReport")

    def test_run_em_thermal_iteration_one_way_succeeds_without_feedback_variables(self):
        maxwell_app = DummyMaxwellApp(variables={})
        icepak_app = DummyIcepakApp()
        with patch("tools.coupling_tools._maxwell_app", return_value=maxwell_app), \
             patch("tools.coupling_tools._icepak_app", return_value=icepak_app):
            result = coupling_tools.run_em_thermal_iteration(
                max_iterations=2,
                convergence_temp_delta=0.1,
                feedback_mode="one_way",
            )
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["feedback_mode"], "one_way")
        self.assertFalse(result["result"]["feedback_applied"])

    def test_run_em_thermal_iteration_two_way_requires_feedback_variables(self):
        maxwell_app = DummyMaxwellApp(variables={})
        icepak_app = DummyIcepakApp()
        with patch("tools.coupling_tools._maxwell_app", return_value=maxwell_app), \
             patch("tools.coupling_tools._icepak_app", return_value=icepak_app):
            result = coupling_tools.run_em_thermal_iteration(
                max_iterations=1,
                feedback_mode="two_way",
            )
        self.assertFalse(result["success"])
        self.assertIn("未能将温度反馈回 Maxwell", result["error"])

    def test_get_torque_reuses_named_report_flow(self):
        data = DummyReportData({"Moving1.Torque": [1.0, 3.0]}, sweep_values=[0.0, 0.1])
        post = DummyPost(data, reports=["TorqueReport"])
        app = types.SimpleNamespace(post=post, solution_type="Transient")
        with patch("tools.result_tools._app", return_value=app):
            result = result_tools.get_torque()
        self.assertTrue(result["success"])
        self.assertEqual(post.deleted, ["TorqueReport"])
        self.assertEqual(result["result"]["avg_torque_Nm"], 2.0)

    def test_get_torque_fails_when_series_is_empty(self):
        data = DummyReportData({"Moving1.Torque": []}, sweep_values=[])
        post = DummyPost(data, reports=["TorqueReport"])
        app = types.SimpleNamespace(post=post, solution_type="Transient")
        with patch("tools.result_tools._app", return_value=app):
            result = result_tools.get_torque()
        self.assertFalse(result["success"])
        self.assertIn("未获取到转矩数据", result["error"])

    def test_get_torque_rejects_when_motion_is_explicitly_missing(self):
        data = DummyReportData({"Moving1.Torque": [1.0]}, sweep_values=[0.0])
        post = DummyPost(data, reports=["TorqueReport"])
        app = types.SimpleNamespace(post=post, solution_type="Transient")
        maxwell_tools._get_model_state(app)["motion_configured"] = False
        with patch("tools.result_tools._app", return_value=app):
            result = result_tools.get_torque()
        self.assertFalse(result["success"])
        self.assertIn("未配置旋转运动语义", result["error"])

    def test_get_back_emf_rejects_when_winding_is_explicitly_missing(self):
        data = DummyReportData({"InducedVoltage(PhaseA)": [1.0]}, sweep_values=[0.0])
        post = DummyPost(data, reports=["BackEMFReport"])
        app = types.SimpleNamespace(post=post, solution_type="Transient")
        maxwell_tools._get_model_state(app)["winding_defined"] = False
        with patch("tools.result_tools._app", return_value=app):
            result = result_tools.get_back_emf()
        self.assertFalse(result["success"])
        self.assertIn("未配置绕组语义", result["error"])

    def test_get_back_emf_rejects_mismatched_solver_type(self):
        data = DummyReportData({"InducedVoltage(PhaseA)": [1.0]}, sweep_values=[0.0])
        post = DummyPost(data, reports=["BackEMFReport"])
        app = types.SimpleNamespace(post=post, solution_type="Transient")
        state = maxwell_tools._get_model_state(app)
        state["winding_defined"] = True
        state["setups"] = {"Setup1": {"solver_type": "Magnetostatic"}}
        with patch("tools.result_tools._app", return_value=app):
            result = result_tools.get_back_emf()
        self.assertFalse(result["success"])
        self.assertIn("与当前结果提取不匹配", result["error"])

    def test_create_inverter_circuit_fails_if_all_wires_fail(self):
        app = DummyCircuitApp(fail_wires=True)
        with patch("tools.circuit_tools._app", return_value=app):
            result = circuit_tools.create_inverter_circuit()
        self.assertFalse(result["success"])
        self.assertIn("所有母线连接均失败", result["error"])

    def test_connect_aedt_accepts_project_and_design(self):
        captured = {}

        class _DummyMaxwell:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        ansys_stub = types.ModuleType("ansys")
        aedt_stub = types.ModuleType("ansys.aedt")
        core_stub = types.ModuleType("ansys.aedt.core")
        core_stub.Maxwell2d = _DummyMaxwell
        sys.modules["ansys"] = ansys_stub
        sys.modules["ansys.aedt"] = aedt_stub
        sys.modules["ansys.aedt.core"] = core_stub
        try:
            result = maxwell_tools.connect_aedt(
                project_path="demo.aedt",
                design_name="MotorA",
            )
        finally:
            sys.modules.pop("ansys.aedt.core", None)
            sys.modules.pop("ansys.aedt", None)
            sys.modules.pop("ansys", None)

        self.assertTrue(result["success"])
        self.assertEqual(captured["project"], "demo.aedt")
        self.assertEqual(captured["design"], "MotorA")

    def test_create_motor_geometry_rejects_odd_pole_count(self):
        result = maxwell_tools.create_motor_geometry(
            stator_outer_radius=60.0,
            stator_inner_radius=40.0,
            rotor_outer_radius=35.0,
            rotor_inner_radius=10.0,
            num_slots=12,
            num_poles=7,
            magnet_thickness=2.0,
        )
        self.assertFalse(result["success"])
        self.assertIn("极数必须为偶数", result["error"])

    def test_apply_magnetization_uses_assign_magnetization_when_available(self):
        captured = {}

        class _DummyApp:
            def assign_magnetization(self, assignment=None, direction=None):
                captured["assignment"] = assignment
                captured["direction"] = direction

        result = maxwell_tools._apply_magnetization(_DummyApp(), "Magnet_1", 30.0)
        self.assertTrue(result)
        self.assertEqual(captured["assignment"], ["Magnet_1"])
        self.assertEqual(captured["direction"], "30.0deg")

    def test_configure_rotation_motion_uses_rotate_motion_when_available(self):
        captured = {}

        class _DummyApp:
            def assign_rotate_motion(self, **kwargs):
                captured.update(kwargs)

        result = maxwell_tools._configure_rotation_motion(_DummyApp(), "Rotor", "AirGap")
        self.assertTrue(result)
        self.assertEqual(captured["assignment"], ["Rotor"])
        self.assertEqual(captured["axis"], "Z")

    def test_create_motor_geometry_sets_torque_ready_when_motion_and_magnetization_exist(self):
        class _DummyApp:
            def __init__(self):
                self.modeler = DummyMaxwellModeler()
                self.motion_calls = 0
                self.magnetization_calls = 0
                self.odesign = types.SimpleNamespace(SetDesignSettings=lambda settings: None)

            def change_design_settings(self, settings):
                return None

            def assign_magnetization(self, assignment=None, direction=None):
                self.magnetization_calls += 1

            def assign_rotate_motion(self, **kwargs):
                self.motion_calls += 1

        app = _DummyApp()
        with patch("tools.maxwell_tools._app", return_value=app):
            result = maxwell_tools.create_motor_geometry(
                stator_outer_radius=60.0,
                stator_inner_radius=40.0,
                rotor_outer_radius=35.0,
                rotor_inner_radius=10.0,
                num_slots=12,
                num_poles=8,
                magnet_thickness=2.0,
            )
        self.assertTrue(result["success"])
        self.assertTrue(result["result"]["magnetization_configured"])
        self.assertTrue(result["result"]["motion_configured"])
        self.assertTrue(result["result"]["torque_ready"])

    def test_setup_winding_assigns_coils_per_conductor(self):
        calls = {"coils": [], "winding": None}

        class _DummyMaxwellApp:
            def __init__(self):
                self.modeler = DummyMaxwellModeler({"Conductor_1", "Conductor_2"})

            def assign_coil(self, **kwargs):
                calls["coils"].append(kwargs)
                index = len(calls["coils"])
                return types.SimpleNamespace(name=f"Coil_{index}")

            def assign_winding(self, **kwargs):
                calls["winding"] = kwargs

        with patch("tools.maxwell_tools._app", return_value=_DummyMaxwellApp()):
            result = maxwell_tools.setup_winding(
                "PhaseA",
                10.0,
                ["Conductor_1", "Conductor_2"],
                frequency=50.0,
                turns=12,
                parallel_branches=2,
                reverse_polarity=True,
            )
        self.assertTrue(result["success"])
        self.assertEqual(len(calls["coils"]), 2)
        self.assertEqual(calls["winding"]["coil_terminals"], ["Coil_1", "Coil_2"])
        self.assertEqual(result["result"]["turns"], 12)
        self.assertEqual(result["result"]["parallel_branches"], 2)
        self.assertTrue(result["result"]["reverse_polarity"])

    def test_setup_winding_updates_model_state(self):
        app = types.SimpleNamespace(
            modeler=DummyMaxwellModeler({"Conductor_1"}),
            assign_coil=lambda **kwargs: types.SimpleNamespace(name="Coil_1"),
            assign_winding=lambda **kwargs: None,
        )
        with patch("tools.maxwell_tools._app", return_value=app):
            result = maxwell_tools.setup_winding("PhaseA", 5.0, ["Conductor_1"])
        self.assertTrue(result["success"])
        state = maxwell_tools._get_model_state(app)
        self.assertTrue(state["winding_defined"])
        self.assertEqual(state["windings"]["PhaseA"]["turns"], 1)

    def test_setup_winding_can_infer_phase_conductors_from_geometry(self):
        app = types.SimpleNamespace(
            modeler=DummyMaxwellModeler(
                {"Conductor_1", "Conductor_4", "Conductor_7", "Conductor_10"}
            ),
            assign_coil=lambda **kwargs: types.SimpleNamespace(name=kwargs["input_object"][0].replace("Conductor", "Coil")),
            assign_winding=lambda **kwargs: None,
        )
        state = maxwell_tools._get_model_state(app)
        state["geometry"] = {"num_slots": 12}
        with patch("tools.maxwell_tools._app", return_value=app):
            result = maxwell_tools.setup_winding("PhaseA", 8.0, None)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["conductor_names"], ["Conductor_1", "Conductor_4", "Conductor_7", "Conductor_10"])
        self.assertIn("warnings", result["result"])

    def test_setup_winding_inference_fails_without_compatible_geometry(self):
        app = types.SimpleNamespace(
            modeler=DummyMaxwellModeler({"Conductor_1"}),
            assign_coil=lambda **kwargs: types.SimpleNamespace(name="Coil_1"),
            assign_winding=lambda **kwargs: None,
        )
        state = maxwell_tools._get_model_state(app)
        state["geometry"] = {"num_slots": 10}
        with patch("tools.maxwell_tools._app", return_value=app):
            result = maxwell_tools.setup_winding("PhaseA", 5.0, None)
        self.assertFalse(result["success"])
        self.assertIn("不足以自动推断", result["error"])

    def test_add_solution_setup_uses_explicit_setup_name(self):
        created = {}

        class _DummySetup:
            def __init__(self):
                self.props = {}

            def update(self):
                return None

        class _DummyMaxwellApp:
            def create_setup(self, name=None):
                created["name"] = name
                created["setup"] = _DummySetup()
                return created["setup"]

        with patch("tools.maxwell_tools._app", return_value=_DummyMaxwellApp()):
            result = maxwell_tools.add_solution_setup(
                setup_name="MySetup",
                solver_type="Transient",
                stop_time=0.02,
                time_step=0.001,
            )
        self.assertTrue(result["success"])
        self.assertEqual(created["name"], "MySetup")
        self.assertEqual(result["result"]["setup_name"], "MySetup")

    def test_add_solution_setup_updates_model_state(self):
        class _DummySetup:
            def __init__(self):
                self.props = {}

            def update(self):
                return None

        app = types.SimpleNamespace(create_setup=lambda name=None: _DummySetup())
        with patch("tools.maxwell_tools._app", return_value=app):
            result = maxwell_tools.add_solution_setup(
                setup_name="Eddy1",
                solver_type="EddyCurrent",
                frequency_Hz=400.0,
            )
        self.assertTrue(result["success"])
        state = maxwell_tools._get_model_state(app)
        self.assertEqual(state["setups"]["Eddy1"]["solver_type"], "EddyCurrent")

    def test_get_vibration_results_returns_error_when_script_reports_error(self):
        app = types.SimpleNamespace(run_python_script=lambda script: '{"error":"modal failed"}')
        with patch("tools.mechanical_tools._app", return_value=app):
            result = mechanical_tools.get_vibration_results()
        self.assertFalse(result["success"])
        self.assertIn("modal failed", result["error"])

    def test_run_modal_analysis_returns_structured_result(self):
        app = types.SimpleNamespace(run_python_script=lambda script: None)
        with patch("tools.mechanical_tools._app", return_value=app):
            result = mechanical_tools.run_modal_analysis()
        self.assertTrue(result["success"])
        self.assertIn("message", result["result"])
        self.assertEqual(result["result"]["analysis_name"], "Modal")

    def test_import_maxwell_forces_uses_design_name_and_setup_name_separately(self):
        app = DummyMechanicalScriptApp()
        with patch("tools.mechanical_tools._app", return_value=app):
            result = mechanical_tools.import_maxwell_forces(
                "/tmp/demo.aedt",
                design_name="MotorA",
                setup_name="Setup1",
            )
        self.assertTrue(result["success"])
        script = app.scripts[-1]
        self.assertIn('_design_name = "MotorA"', script)
        self.assertIn('Properties["Source File"].Value = r"/tmp/demo.aedt"', script)
        self.assertIn('Properties[_key].Value = "Setup1"', script)

    def test_export_report_rejects_pdf_with_html_backend(self):
        dynamic_reporting_tools._report_session = {
            "type": "html",
            "title": "Demo",
            "output_dir": "/tmp",
            "sections": [],
        }
        dynamic_reporting_tools._report_items = []
        result = dynamic_reporting_tools.export_report(format="pdf")
        self.assertFalse(result["success"])
        self.assertIn("不支持 PDF 导出", result["error"])

    def test_create_report_session_surfaces_fallback_warning(self):
        sys.modules.pop("ansys.dynamicreporting.core", None)
        result = dynamic_reporting_tools.create_report_session(use_adr=True)
        self.assertTrue(result["success"])
        self.assertIn("warnings", result["result"])

    def test_add_report_section_returns_structured_result(self):
        dynamic_reporting_tools._report_session = {
            "type": "html",
            "title": "Demo",
            "output_dir": "/tmp",
            "sections": [],
        }
        dynamic_reporting_tools._report_items = []
        result = dynamic_reporting_tools.add_report_section("Intro", "hello")
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["type"], "section")

    def test_generate_report_returns_structured_result(self):
        output_path = "/tmp/generated_motor_report"
        result = report_tools.generate_report(output_path=output_path, format="html")
        self.assertTrue(result["success"])
        self.assertTrue(result["result"]["output_path"].endswith(".html"))

    def test_set_motorcad_geometry_rejects_invalid_dimensions(self):
        result = motorcad_tools.set_motorcad_geometry(
            stator_outer_diam=100.0,
            stator_inner_diam=90.0,
            rotor_outer_diam=95.0,
            shaft_diam=20.0,
            stack_length=50.0,
            num_poles=7,
            num_slots=12,
        )
        self.assertFalse(result["success"])
        self.assertIn("转子外径必须小于定子内径", result["error"])

    def test_set_motorcad_geometry_surfaces_warnings(self):
        class _DummyMotorCAD:
            def set_variable(self, name, value):
                if name == "MachineType":
                    raise RuntimeError("unsupported variable")

        with patch("tools.motorcad_tools._app", return_value=_DummyMotorCAD()):
            result = motorcad_tools.set_motorcad_geometry(
                stator_outer_diam=120.0,
                stator_inner_diam=80.0,
                rotor_outer_diam=70.0,
                shaft_diam=20.0,
                stack_length=40.0,
                num_poles=8,
                num_slots=12,
            )
        self.assertTrue(result["success"])
        self.assertIn("warnings", result["result"])

    def test_export_motorcad_to_maxwell_surfaces_warning_when_export_path_unsupported(self):
        captured = {}

        class _DummyMotorCAD:
            def set_variable(self, name, value):
                if name == "ExportPath":
                    raise RuntimeError("unsupported export path")

            def create_model(self, name):
                captured["model_name"] = name
                return None

        with patch("tools.motorcad_tools._app", return_value=_DummyMotorCAD()):
            result = motorcad_tools.export_motorcad_to_maxwell(output_dir="/tmp/mcad-export")
        self.assertTrue(result["success"])
        self.assertIn("warnings", result["result"])
        self.assertEqual(captured["model_name"], "Maxwell2D")

    def test_run_motorcad_nvh_analysis_requires_real_nvh_solver(self):
        class _DummyMotorCAD:
            def set_variable(self, name, value):
                return None

        with patch("tools.motorcad_tools._app", return_value=_DummyMotorCAD()):
            result = motorcad_tools.run_motorcad_nvh_analysis()
        self.assertFalse(result["success"])
        self.assertIn("未暴露可用的 NVH 求解方法", result["error"])

    def test_run_motorcad_nvh_analysis_runs_explicit_nvh_method(self):
        class _DummyMotorCAD:
            def __init__(self):
                self.nvh_called = False

            def set_variable(self, name, value):
                return None

            def do_nvh_calculation(self):
                self.nvh_called = True

            def get_variable(self, name):
                values = {
                    "RadialForce_Max": 10.0,
                    "Cogging_Torque_Peak": 1.5,
                    "Torque_Ripple_Factor": 3.2,
                    "DominantForceOrder": 12,
                }
                return values.get(name)

        app = _DummyMotorCAD()
        with patch("tools.motorcad_tools._app", return_value=app):
            result = motorcad_tools.run_motorcad_nvh_analysis()
        self.assertTrue(result["success"])
        self.assertTrue(app.nvh_called)
        self.assertEqual(result["result"]["dominant_force_order"], 12)

    def test_connect_motorcad_returns_structured_result(self):
        ansys_mod = types.ModuleType("ansys")
        motorcad_pkg = types.ModuleType("ansys.motorcad")
        motorcad_mod = types.ModuleType("ansys.motorcad.core")

        class _DummyMotorCAD:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def set_variable(self, name, value):
                raise RuntimeError("silent mode unsupported")

            def get_variable(self, name):
                return "2024.1"

        motorcad_mod.MotorCAD = _DummyMotorCAD
        sys.modules["ansys"] = ansys_mod
        sys.modules["ansys.motorcad"] = motorcad_pkg
        sys.modules["ansys.motorcad.core"] = motorcad_mod
        try:
            result = motorcad_tools.connect_motorcad()
        finally:
            sys.modules.pop("ansys.motorcad.core", None)
            sys.modules.pop("ansys.motorcad", None)
            sys.modules.pop("ansys", None)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["version"], "2024.1")
        self.assertIn("warnings", result["result"])

    def test_export_aedt_report_surfaces_png_warning(self):
        app = types.SimpleNamespace(post=DummyReportExportPost())
        result = report_tools.export_aedt_report(output_dir="/tmp/report-export", aedt_app=app)
        self.assertTrue(result["success"])
        self.assertIn("warnings", result["result"])

    def test_connect_circuit_returns_structured_result(self):
        circuit_mod = types.ModuleType("ansys.aedt.core")

        class _DummyCircuit:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        circuit_mod.Circuit = _DummyCircuit
        sys.modules["ansys"] = types.ModuleType("ansys")
        sys.modules["ansys.aedt"] = types.ModuleType("ansys.aedt")
        sys.modules["ansys.aedt.core"] = circuit_mod
        try:
            result = circuit_tools.connect_circuit()
        finally:
            sys.modules.pop("ansys.aedt.core", None)
            sys.modules.pop("ansys.aedt", None)
            sys.modules.pop("ansys", None)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["version"], "2024.1")

    def test_connect_mapdl_returns_structured_result(self):
        mapdl_mod = types.ModuleType("ansys.mapdl.core")

        class _DummyMapdl:
            version = "24.1"

        mapdl_mod.launch_mapdl = lambda **kwargs: _DummyMapdl()
        mapdl_mod.MapdlGrpc = lambda ip=None, port=None: _DummyMapdl()
        sys.modules["ansys"] = types.ModuleType("ansys")
        sys.modules["ansys.mapdl"] = types.ModuleType("ansys.mapdl")
        sys.modules["ansys.mapdl.core"] = mapdl_mod
        try:
            result = mapdl_tools.connect_mapdl()
        finally:
            sys.modules.pop("ansys.mapdl.core", None)
            sys.modules.pop("ansys.mapdl", None)
            sys.modules.pop("ansys", None)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["version"], "24.1")

    def test_add_parametric_variable_returns_structured_result(self):
        app = types.SimpleNamespace(variable_manager=types.SimpleNamespace(set_variable=lambda n, v: None))
        with patch("tools.sweep_tools._app", return_value=app):
            result = sweep_tools.add_parametric_variable("gap", 1.2)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["name"], "gap")

    def test_create_parametric_sweep_rejects_zero_step(self):
        with patch("tools.sweep_tools._app", return_value=types.SimpleNamespace()):
            result = sweep_tools.create_parametric_sweep("gap", 1.0, 2.0, 0.0)
        self.assertFalse(result["success"])
        self.assertIn("step 不能为 0", result["error"])

    def test_get_sweep_results_maps_torque_to_moving1_torque(self):
        captured = {}

        class _DummyPost:
            def get_solution_data(self, expressions=None, setup_sweep_name=None, primary_sweep_variable=None):
                captured["expressions"] = expressions
                captured["setup_sweep_name"] = setup_sweep_name
                captured["primary_sweep_variable"] = primary_sweep_variable
                return DummySweepSolutionData(
                    {"Moving1.Torque": [1.0, 2.0]},
                    primary_sweep_values=[0.5, 1.0],
                )

        app = types.SimpleNamespace(post=_DummyPost())
        with patch("tools.sweep_tools._app", return_value=app):
            result = sweep_tools.get_sweep_results("gap", "Torque", "Sweep1")
        self.assertTrue(result["success"])
        self.assertEqual(captured["expressions"], ["Moving1.Torque"])
        self.assertEqual(result["result"]["queried_expression"], "Moving1.Torque")

    def test_get_efficiency_map_parses_values_with_units(self):
        variations = [
            {
                "Speed": "3000rpm",
                "Current": "10A",
                "Moving1.Torque": "5.5NewtonMeter",
                "CoreLoss": "20W",
                "OhmicLoss": "30W",
            }
        ]
        app = types.SimpleNamespace(parametrics=types.SimpleNamespace(
            get_variation_values=lambda setup_name=None, sweep_name=None: variations
        ))
        with patch("tools.result_tools._app", return_value=app):
            result = result_tools.get_efficiency_map()
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["num_operating_points"], 1)
        self.assertEqual(result["result"]["skipped_points"], 0)

    def test_get_inductance_marks_dq_values_as_approximate(self):
        data = DummyReportData(
            {"L(PhaseA,PhaseA)": [0.1], "L(PhaseB,PhaseB)": [0.2], "L(PhaseC,PhaseC)": [0.3]}
        )
        app = types.SimpleNamespace(post=DummyPost(data))
        with patch("tools.result_tools._app", return_value=app):
            result = result_tools.get_inductance()
        self.assertTrue(result["success"])
        self.assertTrue(result["result"]["dq_inductance_is_approximate"])

    def test_get_flux_linkage_marks_dq_values_as_snapshot_only(self):
        data = DummyReportData(
            {
                "FluxLinkage(PhaseA)": [0.1, 0.2],
                "FluxLinkage(PhaseB)": [-0.05, -0.1],
                "FluxLinkage(PhaseC)": [-0.05, -0.1],
            },
            sweep_values=[0.0, 0.1],
        )
        app = types.SimpleNamespace(post=DummyPost(data), solution_type="Transient")
        with patch("tools.result_tools._app", return_value=app):
            result = result_tools.get_flux_linkage()
        self.assertTrue(result["success"])
        self.assertTrue(result["result"]["dq_snapshot_only"])

    def test_add_design_variable_surfaces_when_initial_value_cannot_be_applied(self):
        class _DummyParameter:
            def __init__(self, **kwargs):
                self.name = kwargs["name"]
                self.reference_value = kwargs["reference_value"]
                self.lower_bound = kwargs["lower_bound"]
                self.upper_bound = kwargs["upper_bound"]

        class _DummyParameterManager:
            def add_parameter(self, param):
                self.param = param

        root_system = types.SimpleNamespace(parameter_manager=_DummyParameterManager())
        osl = types.SimpleNamespace(application=types.SimpleNamespace(project=types.SimpleNamespace(root_system=root_system)))

        project_parametric_mod = types.ModuleType("ansys.optislang.core.project_parametric")
        project_parametric_mod.OptimizationParameter = _DummyParameter
        sys.modules["ansys"] = types.ModuleType("ansys")
        sys.modules["ansys.optislang"] = types.ModuleType("ansys.optislang")
        sys.modules["ansys.optislang.core"] = types.ModuleType("ansys.optislang.core")
        sys.modules["ansys.optislang.core.project_parametric"] = project_parametric_mod
        try:
            with patch("tools.optislang_tools._get_osl", return_value=osl):
                from tools import optislang_tools
                result = optislang_tools.add_design_variable("gap", 1.0, 2.0, initial_value=1.2)
        finally:
            sys.modules.pop("ansys.optislang.core.project_parametric", None)
            sys.modules.pop("ansys.optislang.core", None)
            sys.modules.pop("ansys.optislang", None)
            sys.modules.pop("ansys", None)
        self.assertTrue(result["success"])
        self.assertIn("warnings", result["result"])

    def test_run_optimization_requires_variables_and_responses(self):
        from tools import optislang_tools
        optislang_tools._osl_config.clear()
        osl = types.SimpleNamespace(application=types.SimpleNamespace(project=types.SimpleNamespace(start=lambda: None)))
        with patch("tools.optislang_tools._get_osl", return_value=osl):
            result = optislang_tools.run_optimization()
        self.assertFalse(result["success"])
        self.assertIn("尚未配置任何设计变量", result["error"])

    def test_run_sensitivity_study_requires_responses(self):
        from tools import optislang_tools
        optislang_tools._osl_config.clear()
        optislang_tools._osl_config["design_variables"] = {"gap"}
        osl = types.SimpleNamespace(application=types.SimpleNamespace(project=types.SimpleNamespace(start=lambda: None)))
        with patch("tools.optislang_tools._get_osl", return_value=osl):
            result = optislang_tools.run_sensitivity_study()
        self.assertFalse(result["success"])
        self.assertIn("尚未配置任何响应", result["error"])

    def test_get_optimization_results_marks_reference_design_fallback(self):
        class _DummyParam:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        class _DummyResponse:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        design = types.SimpleNamespace(
            parameters=[_DummyParam("gap", 1.2)],
            responses=[_DummyResponse("torque", 5.0)],
        )
        root_system = types.SimpleNamespace(
            get_reference_design=lambda: design,
            num_evaluations=12,
        )
        osl = types.SimpleNamespace(application=types.SimpleNamespace(project=types.SimpleNamespace(root_system=root_system)))
        with patch("tools.optislang_tools._get_osl", return_value=osl):
            from tools import optislang_tools
            result = optislang_tools.get_optimization_results()
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["result_source"], "get_reference_design")
        self.assertEqual(result["result"]["num_evaluations"], 12)
        self.assertIn("warnings", result["result"])

    def test_run_simulation_rejects_missing_setup_name_when_list_available(self):
        app = types.SimpleNamespace(
            existing_analysis_setups=["SetupA"],
            analyze_setup=lambda name: None,
        )
        with patch("tools.maxwell_tools._app", return_value=app):
            result = maxwell_tools.run_simulation("SetupB")
        self.assertFalse(result["success"])
        self.assertIn("求解设置不存在", result["error"])

    def test_connect_rmxprt_returns_structured_result(self):
        rmxprt_mod = types.ModuleType("ansys.aedt.core")

        class _DummyRmxprt:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        rmxprt_mod.Rmxprt = _DummyRmxprt
        sys.modules["ansys"] = types.ModuleType("ansys")
        sys.modules["ansys.aedt"] = types.ModuleType("ansys.aedt")
        sys.modules["ansys.aedt.core"] = rmxprt_mod
        try:
            result = rmxprt_tools.connect_rmxprt()
        finally:
            sys.modules.pop("ansys.aedt.core", None)
            sys.modules.pop("ansys.aedt", None)
            sys.modules.pop("ansys", None)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["version"], "2024.1")

    def test_create_motor_from_template_fails_when_key_parameters_are_not_written(self):
        class _DummyODesign:
            def SetDesignSettings(self, settings):
                raise RuntimeError("unsupported")

            def ChangeProperty(self, settings):
                raise RuntimeError("unsupported")

        class _DummyRMXprtApp:
            def __init__(self):
                self.odesign = _DummyODesign()

            def new_design(self, design_name=None, solution_type=None):
                return None

        with patch("tools.rmxprt_tools._app", return_value=_DummyRMXprtApp()):
            result = rmxprt_tools.create_motor_from_template(
                stator_outer_diameter=120.0,
                stator_inner_diameter=80.0,
                rotor_outer_diameter=70.0,
                shaft_diameter=20.0,
                stack_length=50.0,
                num_poles=8,
                num_slots=12,
            )
        self.assertFalse(result["success"])
        self.assertIn("关键几何/极槽参数均未成功写入", result["error"])

    def test_define_boundary_conditions_rejects_unimplemented_types(self):
        session = types.SimpleNamespace(setup=types.SimpleNamespace(boundary_conditions=types.SimpleNamespace()))
        with patch("tools.fluent_tools._session", return_value=session):
            result = fluent_tools.define_boundary_conditions("sym1", "symmetry")
        self.assertFalse(result["success"])
        self.assertIn("当前工具仅支持", result["error"])

    def test_run_thermal_stress_analysis_rejects_nonuniform_temperature_map(self):
        csv_path = "/tmp/nonuniform_temperature.csv"
        Path(csv_path).write_text("x,y,z,temp\n0,0,0,20\n1,0,0,30\n", encoding="utf-8")
        with patch("tools.mapdl_tools._app", return_value=types.SimpleNamespace()):
            result = mapdl_tools.run_thermal_stress_analysis(csv_path)
        self.assertFalse(result["success"])
        self.assertIn("非均匀温度分布", result["error"])

    def test_tool_definitions_match_public_function_signatures(self):
        definition_params = {
            item["function"]["name"]: list(item["function"].get("parameters", {}).get("properties", {}).keys())
            for item in tool_definitions.TOOL_DEFINITIONS
        }
        ignored_internal_params = {
            "export_aedt_report": {"aedt_app"},
        }
        mismatches = []

        for name, func in tool_definitions.TOOL_REGISTRY.items():
            signature = inspect.signature(func)
            ignored = ignored_internal_params.get(name, set())
            public_params = [
                param.name
                for param in signature.parameters.values()
                if param.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
                and not param.name.startswith("_")
                and param.name not in ignored
            ]
            declared_params = definition_params.get(name)
            if declared_params is None:
                mismatches.append((name, public_params, None))
                continue
            if public_params != declared_params:
                mismatches.append((name, public_params, declared_params))

        self.assertEqual([], mismatches)

    def test_tool_definitions_include_mechanical_analysis_name(self):
        text = Path("/Users/fittenwby/AnsysAgent/agent/tool_definitions.py").read_text()
        self.assertIn('"name": "run_modal_analysis"', text)
        self.assertIn('"analysis_name": {"type": "string", "description": "Mechanical 中的目标分析名称，默认 Modal"}', text)
        self.assertIn('"name": "get_vibration_results"', text)
        self.assertIn('"frequency_Hz": {"type": "number", "description": "涡流求解频率（Hz，EddyCurrent 专用）"}', text)
        self.assertIn('"setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"}', text)
        self.assertIn('"design_name": {"type": "string", "description": "Maxwell 设计名称；留空则使用导入对象默认设计"}', text)
        self.assertIn('"reference_value": {"type": "number", "description": "参考值；留空则跟随 initial_value"}', text)
        self.assertIn('"turbulent_length_scale": {"type": "number", "description": "湍流长度尺度（m）；留空则自动估算"}', text)

    def test_export_field_image_surfaces_unknown_orientation_warning(self):
        app = DummyVisualizationApp()
        output_path = "/tmp/field_plot_test.png"
        if os.path.exists(output_path):
            os.remove(output_path)
        with patch("tools.visualization_tools._app", return_value=app):
            result = visualization_tools.export_field_image(
                plot_name="Plot1",
                output_path=output_path,
                orientation="BAD",
            )
        self.assertTrue(result["success"])
        self.assertIn("warnings", result["result"])


if __name__ == "__main__":
    unittest.main()
