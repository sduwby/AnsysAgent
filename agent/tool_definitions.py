"""
工具注册表与工具定义（OpenAI function calling 格式）。
从 chat_agent.py 中抽离，便于独立维护和测试。
"""

from __future__ import annotations

from tools import (
    maxwell_tools,
    result_tools,
    optislang_tools,
    icepak_tools,
    circuit_tools,
    mechanical_tools,
    sweep_tools,
    report_tools,
    fluent_tools,
    project_tools,
    mesh_tools,
    coupling_tools,
    rmxprt_tools,
    visualization_tools,
    motorcad_tools,
    mapdl_tools,
    dpf_tools,
    dynamic_reporting_tools,
    knowledge_tools,
    skill_tools,
    memory_tools,
    material_tools,
    database_tools,
    ev_powertrain_tools,
    nvh_tools,
    cost_tools,
    crash_tools,
    vehicle_cfd_tools,
    fatigue_tools,
    vehicle_dynamics_tools,
    vehicle_structural_tools,
    advanced_meshing_tools,
    vehicle_nvh_tools,
    test_data_tools,
    webgl_viewer_tools,
    cad_import_tools,
    workflow_template_tools,
    cloud_tools,
    diagnostic_tools,
    ansys_error_collector,
    embedding_config_tool,
)

# ---------------------------------------------------------------------------
# 工具注册表：工具名 -> 可调用函数
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, callable] = {
    "connect_aedt": maxwell_tools.connect_aedt,
    "create_maxwell_project": maxwell_tools.create_maxwell_project,
    "create_motor_geometry": maxwell_tools.create_motor_geometry,
    "assign_material": maxwell_tools.assign_material,
    "setup_winding": maxwell_tools.setup_winding,
    "add_solution_setup": maxwell_tools.add_solution_setup,
    "run_simulation": maxwell_tools.run_simulation,
    "get_torque": result_tools.get_torque,
    "get_back_emf": result_tools.get_back_emf,
    "get_flux_density": result_tools.get_flux_density,
    "get_losses": result_tools.get_losses,
    "export_results": result_tools.export_results,
    # optiSLang 工具
    "connect_optislang": optislang_tools.connect_optislang,
    "create_optimization_project": optislang_tools.create_optimization_project,
    "add_design_variable": optislang_tools.add_design_variable,
    "add_response": optislang_tools.add_response,
    "run_sensitivity_study": optislang_tools.run_sensitivity_study,
    "run_optimization": optislang_tools.run_optimization,
    "get_optimization_results": optislang_tools.get_optimization_results,
    "get_sensitivity_results": optislang_tools.get_sensitivity_results,
    "disconnect_optislang": optislang_tools.disconnect_optislang,
    # Icepak 热分析工具
    "connect_icepak": icepak_tools.connect_icepak,
    "setup_motor_thermal": icepak_tools.setup_motor_thermal,
    "run_thermal_simulation": icepak_tools.run_thermal_simulation,
    "get_temperature_results": icepak_tools.get_temperature_results,
    # Maxwell Circuit 驱动器联仿工具
    "connect_circuit": circuit_tools.connect_circuit,
    "create_inverter_circuit": circuit_tools.create_inverter_circuit,
    "link_maxwell_to_circuit": circuit_tools.link_maxwell_to_circuit,
    "run_circuit_simulation": circuit_tools.run_circuit_simulation,
    "get_circuit_results": circuit_tools.get_circuit_results,
    # Mechanical 结构振动工具
    "connect_mechanical": mechanical_tools.connect_mechanical,
    "import_maxwell_forces": mechanical_tools.import_maxwell_forces,
    "run_modal_analysis": mechanical_tools.run_modal_analysis,
    "run_harmonic_analysis": mechanical_tools.run_harmonic_analysis,
    "get_vibration_results": mechanical_tools.get_vibration_results,
    # 参数化扫描工具
    "add_parametric_variable": sweep_tools.add_parametric_variable,
    "create_parametric_sweep": sweep_tools.create_parametric_sweep,
    "run_parametric_sweep": sweep_tools.run_parametric_sweep,
    "get_sweep_results": sweep_tools.get_sweep_results,
    "create_2d_sweep": sweep_tools.create_2d_sweep,
    # 报告生成工具
    "generate_report": report_tools.generate_report,
    "export_aedt_report": report_tools.export_aedt_report,
    # Fluent 流体分析工具
    "connect_fluent": fluent_tools.connect_fluent,
    "read_fluent_mesh": fluent_tools.read_fluent_mesh,
    "setup_fluid_models": fluent_tools.setup_fluid_models,
    "define_boundary_conditions": fluent_tools.define_boundary_conditions,
    "setup_fluent_solver": fluent_tools.setup_fluent_solver,
    "initialize_fluent": fluent_tools.initialize_fluent,
    "run_fluent_simulation": fluent_tools.run_fluent_simulation,
    "get_fluent_results": fluent_tools.get_fluent_results,
    "export_fluent_data": fluent_tools.export_fluent_data,
    "setup_fluid_material": fluent_tools.setup_fluid_material,
    # Fluent Meshing & 参数化多工况工具
    "launch_fluent_meshing": fluent_tools.launch_fluent_meshing,
    "run_watertight_meshing_workflow": fluent_tools.run_watertight_meshing_workflow,
    "create_named_expression": fluent_tools.create_named_expression,
    "assign_cell_zone_material": fluent_tools.assign_cell_zone_material,
    "update_named_expression": fluent_tools.update_named_expression,
    "export_surface_data_ascii": fluent_tools.export_surface_data_ascii,
    "run_multi_condition_simulation": fluent_tools.run_multi_condition_simulation,
    "close_fluent": fluent_tools.close_fluent,
    # 自定义材料工具（Maxwell）
    "create_custom_material": maxwell_tools.create_custom_material,
    "import_bh_curve": maxwell_tools.import_bh_curve,
    # 外部 CAD 几何导入工具（Maxwell）
    "import_cad_geometry": maxwell_tools.import_cad_geometry,
    "import_dxf": maxwell_tools.import_dxf,
    # 项目管理工具
    "save_project": project_tools.save_project,
    "open_project": project_tools.open_project,
    "close_project": project_tools.close_project,
    "list_designs": project_tools.list_designs,
    "copy_design": project_tools.copy_design,
    # 网格控制工具
    "setup_length_mesh": mesh_tools.setup_length_mesh,
    "setup_skin_depth_mesh": mesh_tools.setup_skin_depth_mesh,
    "setup_surface_mesh": mesh_tools.setup_surface_mesh,
    "get_mesh_stats": mesh_tools.get_mesh_stats,
    # 电磁-热耦合工具
    "link_maxwell_to_icepak": coupling_tools.link_maxwell_to_icepak,
    "run_em_thermal_iteration": coupling_tools.run_em_thermal_iteration,
    # P2 高级结果工具
    "get_inductance": result_tools.get_inductance,
    "get_flux_linkage": result_tools.get_flux_linkage,
    "get_cogging_torque": result_tools.get_cogging_torque,
    "get_efficiency_map": result_tools.get_efficiency_map,
    "check_demagnetization": result_tools.check_demagnetization,
    # P3 RMXprt 初设计工具
    "connect_rmxprt": rmxprt_tools.connect_rmxprt,
    "create_motor_from_template": rmxprt_tools.create_motor_from_template,
    "run_rmxprt_analysis": rmxprt_tools.run_rmxprt_analysis,
    "export_to_maxwell": rmxprt_tools.export_to_maxwell,
    # P3 热-结构耦合工具
    "import_thermal_to_mechanical": coupling_tools.import_thermal_to_mechanical,
    # P3 场量可视化工具
    "create_field_plot": visualization_tools.create_field_plot,
    "export_field_image": visualization_tools.export_field_image,
    "list_field_plots": visualization_tools.list_field_plots,
    # Motor-CAD 解析法初设计工具
    "connect_motorcad": motorcad_tools.connect_motorcad,
    "set_motorcad_geometry": motorcad_tools.set_motorcad_geometry,
    "run_motorcad_em_analysis": motorcad_tools.run_motorcad_em_analysis,
    "run_motorcad_thermal_analysis": motorcad_tools.run_motorcad_thermal_analysis,
    "run_motorcad_nvh_analysis": motorcad_tools.run_motorcad_nvh_analysis,
    "get_motorcad_performance_map": motorcad_tools.get_motorcad_performance_map,
    "export_motorcad_to_maxwell": motorcad_tools.export_motorcad_to_maxwell,
    "disconnect_motorcad": motorcad_tools.disconnect_motorcad,
    # Mechanical 独立批处理模式工具
    "launch_mechanical_standalone": mechanical_tools.launch_mechanical_standalone,
    "mechanical_run_script": mechanical_tools.mechanical_run_script,
    "mechanical_upload_file": mechanical_tools.mechanical_upload_file,
    "mechanical_download_file": mechanical_tools.mechanical_download_file,
    "run_steady_state_thermal": mechanical_tools.run_steady_state_thermal,
    "import_fluent_htc_to_mechanical": mechanical_tools.import_fluent_htc_to_mechanical,
    "mechanical_exit": mechanical_tools.mechanical_exit,
    # PyMAPDL 结构强度 / NVH 工具
    "connect_mapdl": mapdl_tools.connect_mapdl,
    "run_rotor_stress_analysis": mapdl_tools.run_rotor_stress_analysis,
    "run_thermal_stress_analysis": mapdl_tools.run_thermal_stress_analysis,
    "run_nvh_harmonic_analysis": mapdl_tools.run_nvh_harmonic_analysis,
    "get_mapdl_structural_results": mapdl_tools.get_mapdl_structural_results,
    "disconnect_mapdl": mapdl_tools.disconnect_mapdl,
    # MapdlPool 子模型工具
    "connect_mapdl_pool": mapdl_tools.connect_mapdl_pool,
    "load_mapdl_pool_model": mapdl_tools.load_mapdl_pool_model,
    "run_mapdl_pool_submodel": mapdl_tools.run_mapdl_pool_submodel,
    "disconnect_mapdl_pool": mapdl_tools.disconnect_mapdl_pool,
    # PyDPF-Post 结果后处理工具
    "load_dpf_result": dpf_tools.load_dpf_result,
    "get_dpf_stress": dpf_tools.get_dpf_stress,
    "get_dpf_temperature": dpf_tools.get_dpf_temperature,
    "get_dpf_displacement": dpf_tools.get_dpf_displacement,
    "get_dpf_field_statistics": dpf_tools.get_dpf_field_statistics,
    "export_dpf_results_to_csv": dpf_tools.export_dpf_results_to_csv,
    # DPF-Core 底层工具（子模型插值、热分析 .rth）
    "connect_dpf_server": dpf_tools.connect_dpf_server,
    "load_dpf_core_model": dpf_tools.load_dpf_core_model,
    "get_dpf_core_temperature": dpf_tools.get_dpf_core_temperature,
    "find_result_files": dpf_tools.find_result_files,
    "create_dpf_interpolator": dpf_tools.create_dpf_interpolator,
    "interpolate_boundary_displacements": dpf_tools.interpolate_boundary_displacements,
    # 自动化报告生成工具
    "create_report_session": dynamic_reporting_tools.create_report_session,
    "add_report_section": dynamic_reporting_tools.add_report_section,
    "add_table_to_report": dynamic_reporting_tools.add_table_to_report,
    "add_image_to_report": dynamic_reporting_tools.add_image_to_report,
    "export_report": dynamic_reporting_tools.export_report,
    # 本地知识检索工具
    "build_knowledge_index": knowledge_tools.build_knowledge_index,
    "search_official_docs": knowledge_tools.search_official_docs,
    # 技能加载工具
    "use_skill": skill_tools.use_skill,
    # 持久记忆工具
    "list_memories": memory_tools.list_memories,
    "read_memory": memory_tools.read_memory,
    "save_memory": memory_tools.save_memory,
    "delete_memory": memory_tools.delete_memory,
    # 仿真案例沉淀工具
    "save_simulation_case": memory_tools.save_simulation_case,
    "search_simulation_cases": memory_tools.search_simulation_cases,
    # 材料库管理工具
    "add_material": material_tools.add_material,
    "list_materials": material_tools.list_materials,
    "get_material": material_tools.get_material,
    "delete_material": material_tools.delete_material,
    "import_bh_from_csv": material_tools.import_bh_from_csv,
    "export_material_for_aedt": material_tools.export_material_for_aedt,
    "update_material_metadata": material_tools.update_material_metadata,
    # P4 高级 Maxwell 结果分析工具
    "get_iron_loss_breakdown": result_tools.get_iron_loss_breakdown,
    "get_cogging_torque_harmonics": result_tools.get_cogging_torque_harmonics,
    "get_winding_factor": result_tools.get_winding_factor,
    # P4 DOE / RSM 扫描工具
    "create_lhs_doe": sweep_tools.create_lhs_doe,
    "build_rsm": sweep_tools.build_rsm,
    # 设计结果数据库工具
    "save_design_result": database_tools.save_design_result,
    "list_design_results": database_tools.list_design_results,
    "get_design_result": database_tools.get_design_result,
    "compare_design_results": database_tools.compare_design_results,
    # EV 整车电驱系统联仿工具
    "connect_ev_circuit": ev_powertrain_tools.connect_ev_circuit,
    "create_battery_model": ev_powertrain_tools.create_battery_model,
    "create_controller_model": ev_powertrain_tools.create_controller_model,
    "link_motor_to_powertrain": ev_powertrain_tools.link_motor_to_powertrain,
    "run_powertrain_simulation": ev_powertrain_tools.run_powertrain_simulation,
    "get_powertrain_results": ev_powertrain_tools.get_powertrain_results,
    "get_powertrain_config": ev_powertrain_tools.get_powertrain_config,
    # NVH 噪声振动分析工具
    "connect_nvh_mechanical": nvh_tools.connect_nvh_mechanical,
    "connect_nvh_mapdl": nvh_tools.connect_nvh_mapdl,
    "extract_maxwell_electromagnetic_forces": nvh_tools.extract_maxwell_electromagnetic_forces,
    "import_forces_to_structural": nvh_tools.import_forces_to_structural,
    "run_nvh_modal_analysis": nvh_tools.run_nvh_modal_analysis,
    "run_nvh_harmonic_response": nvh_tools.run_nvh_harmonic_response,
    "extract_vibration_noise_results": nvh_tools.extract_vibration_noise_results,
    "run_nvh_full_chain": nvh_tools.run_nvh_full_chain,
    # 成本估算工具
    "estimate_motor_cost": cost_tools.estimate_motor_cost,
    "get_default_material_prices": cost_tools.get_default_material_prices,
    "compare_magnet_cost": cost_tools.compare_magnet_cost,
    # LS-DYNA 整车碰撞安全仿真工具（PyDyna）
    "create_crash_deck": crash_tools.create_crash_deck,
    "load_vehicle_model": crash_tools.load_vehicle_model,
    "add_crash_material": crash_tools.add_crash_material,
    "add_crash_section": crash_tools.add_crash_section,
    "add_crash_part": crash_tools.add_crash_part,
    "add_crash_contact": crash_tools.add_crash_contact,
    "add_rigid_wall": crash_tools.add_rigid_wall,
    "setup_frontal_crash": crash_tools.setup_frontal_crash,
    "setup_side_crash": crash_tools.setup_side_crash,
    "setup_rear_crash": crash_tools.setup_rear_crash,
    "setup_pedestrian_protection": crash_tools.setup_pedestrian_protection,
    "add_initial_velocity": crash_tools.add_initial_velocity,
    "add_gravity_load": crash_tools.add_gravity_load,
    "list_deck_keywords": crash_tools.list_deck_keywords,
    "export_crash_model": crash_tools.export_crash_model,
    "run_crash_simulation": crash_tools.run_crash_simulation,
    "get_crash_results": crash_tools.get_crash_results,
    "get_dummy_injury_criteria": crash_tools.get_dummy_injury_criteria,
    "disconnect_crash_solver": crash_tools.disconnect_crash_solver,
    "parse_glstat": crash_tools.parse_glstat,
    "parse_nodout": crash_tools.parse_nodout,
    "parse_rcforc": crash_tools.parse_rcforc,
    "parse_bndout": crash_tools.parse_bndout,
    "compute_hic": crash_tools.compute_hic,
    "compute_chest_3ms": crash_tools.compute_chest_3ms,
    "compute_nij": crash_tools.compute_nij,
    "check_energy_balance": crash_tools.check_energy_balance,
    "get_intrusion_at_node": crash_tools.get_intrusion_at_node,
    "add_node_set": crash_tools.add_node_set,
    "add_segment_set": crash_tools.add_segment_set,
    "add_part_set": crash_tools.add_part_set,
    "add_constrained_rigid_bodies": crash_tools.add_constrained_rigid_bodies,
    "define_curve": crash_tools.define_curve,
    "add_joint": crash_tools.add_joint,
    "add_seatbelt": crash_tools.add_seatbelt,
    "place_rigid_wall_occ": crash_tools.place_rigid_wall_occ,
    "import_barrier_model": crash_tools.import_barrier_model,
    "place_dummy_model": crash_tools.place_dummy_model,
    "setup_airbag": crash_tools.setup_airbag,
    "add_pretensioner": crash_tools.add_pretensioner,
    "evaluate_ncap_frontal": crash_tools.evaluate_ncap_frontal,
    "generate_crash_report": crash_tools.generate_crash_report,
    # 整车 CFD 仿真工具（PyFluent）
    "connect_vehicle_cfd": vehicle_cfd_tools.connect_vehicle_cfd,
    "load_vehicle_cfd_mesh": vehicle_cfd_tools.load_vehicle_cfd_mesh,
    "setup_external_aero": vehicle_cfd_tools.setup_external_aero,
    "setup_battery_thermal_cfd": vehicle_cfd_tools.setup_battery_thermal_cfd,
    "setup_engine_bay_thermal": vehicle_cfd_tools.setup_engine_bay_thermal,
    "define_vehicle_cfd_boundaries": vehicle_cfd_tools.define_vehicle_cfd_boundaries,
    "run_vehicle_cfd_simulation": vehicle_cfd_tools.run_vehicle_cfd_simulation,
    "get_aero_coefficients": vehicle_cfd_tools.get_aero_coefficients,
    "get_thermal_results": vehicle_cfd_tools.get_thermal_results,
    "export_vehicle_cfd_results": vehicle_cfd_tools.export_vehicle_cfd_results,
    "close_vehicle_cfd": vehicle_cfd_tools.close_vehicle_cfd,
    # 疲劳耐久仿真工具
    "connect_fatigue_solver": fatigue_tools.connect_fatigue_solver,
    "load_fatigue_model": fatigue_tools.load_fatigue_model,
    "load_structural_results": fatigue_tools.load_structural_results,
    "define_sn_curve": fatigue_tools.define_sn_curve,
    "define_en_curve": fatigue_tools.define_en_curve,
    "define_load_spectrum": fatigue_tools.define_load_spectrum,
    "setup_mean_stress_correction": fatigue_tools.setup_mean_stress_correction,
    "run_fatigue_analysis": fatigue_tools.run_fatigue_analysis,
    "get_fatigue_results": fatigue_tools.get_fatigue_results,
    "disconnect_fatigue_solver": fatigue_tools.disconnect_fatigue_solver,
    # 整车动力学 VD 仿真工具
    "connect_vd_solver": vehicle_dynamics_tools.connect_vd_solver,
    "define_vehicle_params": vehicle_dynamics_tools.define_vehicle_params,
    "setup_steady_state_cornering": vehicle_dynamics_tools.setup_steady_state_cornering,
    "setup_step_steering": vehicle_dynamics_tools.setup_step_steering,
    "setup_random_road": vehicle_dynamics_tools.setup_random_road,
    "setup_braking_analysis": vehicle_dynamics_tools.setup_braking_analysis,
    "setup_suspension_kinematics": vehicle_dynamics_tools.setup_suspension_kinematics,
    "run_vd_simulation": vehicle_dynamics_tools.run_vd_simulation,
    "get_vd_results": vehicle_dynamics_tools.get_vd_results,
    "disconnect_vd_solver": vehicle_dynamics_tools.disconnect_vd_solver,
    # 整车结构强度仿真工具
    "connect_structural_solver": vehicle_structural_tools.connect_structural_solver,
    "load_structural_model": vehicle_structural_tools.load_structural_model,
    "define_structural_material": vehicle_structural_tools.define_structural_material,
    "setup_boundary_conditions": vehicle_structural_tools.setup_boundary_conditions,
    "apply_bending_load": vehicle_structural_tools.apply_bending_load,
    "apply_torsion_load": vehicle_structural_tools.apply_torsion_load,
    "apply_quasi_static_loads": vehicle_structural_tools.apply_quasi_static_loads,
    "run_structural_analysis": vehicle_structural_tools.run_structural_analysis,
    "get_structural_results": vehicle_structural_tools.get_structural_results,
    "disconnect_structural_solver": vehicle_structural_tools.disconnect_structural_solver,
    # 高级网格划分工具
    "launch_meshing_session": advanced_meshing_tools.launch_meshing_session,
    "import_geometry_for_meshing": advanced_meshing_tools.import_geometry_for_meshing,
    "generate_tetrahedral_mesh": advanced_meshing_tools.generate_tetrahedral_mesh,
    "generate_hex_mesh": advanced_meshing_tools.generate_hex_mesh,
    "generate_polyhedral_mesh": advanced_meshing_tools.generate_polyhedral_mesh,
    "check_mesh_quality": advanced_meshing_tools.check_mesh_quality,
    "refine_mesh_locally": advanced_meshing_tools.refine_mesh_locally,
    "export_mesh": advanced_meshing_tools.export_mesh,
    "close_meshing_session": advanced_meshing_tools.close_meshing_session,
    # 整车 NVH 仿真工具
    "connect_vehicle_nvh_solver": vehicle_nvh_tools.connect_vehicle_nvh_solver,
    "load_vehicle_nvh_model": vehicle_nvh_tools.load_vehicle_nvh_model,
    "define_nvh_materials": vehicle_nvh_tools.define_nvh_materials,
    "setup_vehicle_modal_analysis": vehicle_nvh_tools.setup_vehicle_modal_analysis,
    "setup_frequency_response": vehicle_nvh_tools.setup_frequency_response,
    "setup_acoustic_analysis": vehicle_nvh_tools.setup_acoustic_analysis,
    "run_vehicle_nvh_simulation": vehicle_nvh_tools.run_vehicle_nvh_simulation,
    "get_vehicle_nvh_results": vehicle_nvh_tools.get_vehicle_nvh_results,
    "disconnect_vehicle_nvh_solver": vehicle_nvh_tools.disconnect_vehicle_nvh_solver,
    # 试验数据管理工具
    "create_test_project": test_data_tools.create_test_project,
    "import_test_data": test_data_tools.import_test_data,
    "describe_nvh_test": test_data_tools.describe_nvh_test,
    "describe_vd_test": test_data_tools.describe_vd_test,
    "describe_durability_test": test_data_tools.describe_durability_test,
    "correlate_cae_test": test_data_tools.correlate_cae_test,
    "list_test_data": test_data_tools.list_test_data,
    "list_test_projects": test_data_tools.list_test_projects,
    "export_test_report": test_data_tools.export_test_report,
    # WebGL 3D可视化工具
    "start_webgl_viewer": webgl_viewer_tools.start_webgl_viewer,
    "stop_webgl_viewer": webgl_viewer_tools.stop_webgl_viewer,
    "export_model_to_gltf": webgl_viewer_tools.export_model_to_gltf,
    "create_simulation_animation": webgl_viewer_tools.create_simulation_animation,
    "get_viewer_status": webgl_viewer_tools.get_viewer_status,
    # CAD导入工具
    "import_cad_file": cad_import_tools.import_cad_file,
    "import_step_file": cad_import_tools.import_step_file,
    "import_stl_file": cad_import_tools.import_stl_file,
    "convert_cad_format": cad_import_tools.convert_cad_format,
    "list_supported_cad_formats": cad_import_tools.list_supported_cad_formats,
    "check_cad_file": cad_import_tools.check_cad_file,
    "batch_import_cad_files": cad_import_tools.batch_import_cad_files,
    # 仿真流程模板工具
    "list_templates": workflow_template_tools.list_templates,
    "get_template": workflow_template_tools.get_template,
    "save_template": workflow_template_tools.save_template,
    "delete_template": workflow_template_tools.delete_template,
    "validate_template": workflow_template_tools.validate_template,
    "execute_template": workflow_template_tools.execute_template,
    "create_template_from_history": workflow_template_tools.create_template_from_history,
    # 云平台集成工具
    "list_cloud_providers": cloud_tools.list_cloud_providers,
    "configure_cloud": cloud_tools.configure_cloud,
    "get_cloud_status": cloud_tools.get_cloud_status,
    "launch_hpc_instance": cloud_tools.launch_hpc_instance,
    "list_hpc_instances": cloud_tools.list_hpc_instances,
    "terminate_hpc_instances": cloud_tools.terminate_hpc_instances,
    "submit_cloud_job": cloud_tools.submit_cloud_job,
    "get_cloud_job_status": cloud_tools.get_cloud_job_status,
    "upload_to_cloud_storage": cloud_tools.upload_to_cloud_storage,
    "download_from_cloud_storage": cloud_tools.download_from_cloud_storage,
    "estimate_cloud_cost": cloud_tools.estimate_cloud_cost,
    # 智能诊断与异常检测工具
    "diagnose_error": diagnostic_tools.diagnose_error,
    "validate_simulation_setup": diagnostic_tools.validate_simulation_setup,
    "analyze_sensitivity": diagnostic_tools.analyze_sensitivity,
    "detect_anomalies": diagnostic_tools.detect_anomalies,
    "get_diagnostic_error_history": diagnostic_tools.get_error_history,
    # Ansys 错误收集器
    "get_ansi_error_history": ansys_error_collector.get_error_history,
    "clear_ansi_error_history": ansys_error_collector.clear_error_history,
    "diagnose_ansi_error": ansys_error_collector.diagnose_ansi_error,
    "get_ansi_error_statistics": ansys_error_collector.get_error_statistics,
}

# ---------------------------------------------------------------------------
# 工具定义（OpenAI function calling 格式，DeepSeek 兼容）
# 各域定义已拆分到 agent/definitions/ 子包，在此合并为单一列表
# ---------------------------------------------------------------------------
from agent.definitions.defs_maxwell import DEFINITIONS_MAXWELL
from agent.definitions.defs_icepak_fluent import DEFINITIONS_ICEPAK_FLUENT
from agent.definitions.defs_fluent_mapdl import DEFINITIONS_FLUENT_MAPDL
from agent.definitions.defs_mapdl_dpf import DEFINITIONS_MAPDL_DPF
from agent.definitions.defs_crash_vehicle import DEFINITIONS_CRASH_VEHICLE

TOOL_DEFINITIONS = (
    DEFINITIONS_MAXWELL
    + DEFINITIONS_ICEPAK_FLUENT
    + DEFINITIONS_FLUENT_MAPDL
    + DEFINITIONS_MAPDL_DPF
    + DEFINITIONS_CRASH_VEHICLE
)

# ---------------------------------------------------------------------------
# 按 Sub-Agent 分组的工具名集合
# ---------------------------------------------------------------------------

_MAXWELL_TOOL_NAMES: frozenset[str] = frozenset({
    # AEDT 连接 & 建模
    "connect_aedt", "create_maxwell_project", "create_motor_geometry",
    "assign_material", "setup_winding", "add_solution_setup", "run_simulation",
    # 结果提取
    "get_torque", "get_back_emf", "get_flux_density", "get_losses", "export_results",
    "get_inductance", "get_flux_linkage", "get_cogging_torque", "get_efficiency_map",
    "check_demagnetization",
    # 自定义材料
    "create_custom_material", "import_bh_curve",
    # 外部 CAD 导入
    "import_cad_geometry", "import_dxf",
    # 网格控制
    "setup_length_mesh", "setup_skin_depth_mesh", "setup_surface_mesh", "get_mesh_stats",
    # RMXprt 初设计
    "connect_rmxprt", "create_motor_from_template", "run_rmxprt_analysis", "export_to_maxwell",
    # 场量可视化
    "create_field_plot", "export_field_image", "list_field_plots",
    # Circuit 驱动器联仿
    "connect_circuit", "create_inverter_circuit", "link_maxwell_to_circuit",
    "run_circuit_simulation", "get_circuit_results",
    # 结果分析
    "get_iron_loss_breakdown", "get_cogging_torque_harmonics", "get_winding_factor",
    # 材料库管理
    "add_material", "list_materials", "get_material", "delete_material",
    "import_bh_from_csv", "export_material_for_aedt", "update_material_metadata",
})

_ICEPAK_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_icepak", "setup_motor_thermal", "run_thermal_simulation", "get_temperature_results",
})

_FLUENT_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_fluent", "read_fluent_mesh", "setup_fluid_models", "define_boundary_conditions",
    "setup_fluent_solver", "initialize_fluent", "run_fluent_simulation",
    "get_fluent_results", "export_fluent_data", "setup_fluid_material",
    # Fluent Meshing & 参数化多工况
    "launch_fluent_meshing", "run_watertight_meshing_workflow",
    "create_named_expression", "assign_cell_zone_material",
    "update_named_expression", "export_surface_data_ascii",
    "run_multi_condition_simulation", "close_fluent",
})

_MAPDL_TOOL_NAMES: frozenset[str] = frozenset({
    # Mechanical 结构振动
    "connect_mechanical", "import_maxwell_forces", "run_modal_analysis",
    "run_harmonic_analysis", "get_vibration_results",
    # Mechanical 独立批处理模式
    "launch_mechanical_standalone", "mechanical_run_script",
    "mechanical_upload_file", "mechanical_download_file",
    "run_steady_state_thermal", "import_fluent_htc_to_mechanical", "mechanical_exit",
    # PyMAPDL 结构强度
    "connect_mapdl", "run_rotor_stress_analysis", "run_thermal_stress_analysis",
    "run_nvh_harmonic_analysis", "get_mapdl_structural_results", "disconnect_mapdl",
    # MapdlPool 子模型
    "connect_mapdl_pool", "load_mapdl_pool_model",
    "run_mapdl_pool_submodel", "disconnect_mapdl_pool",
    # PyDPF-Post 后处理
    "load_dpf_result", "get_dpf_stress", "get_dpf_temperature",
    "get_dpf_displacement", "get_dpf_field_statistics", "export_dpf_results_to_csv",
    # DPF-Core 底层工具
    "connect_dpf_server", "load_dpf_core_model", "get_dpf_core_temperature",
    "find_result_files", "create_dpf_interpolator", "interpolate_boundary_displacements",
})

_MOTORCAD_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_motorcad", "set_motorcad_geometry", "run_motorcad_em_analysis",
    "run_motorcad_thermal_analysis", "run_motorcad_nvh_analysis",
    "get_motorcad_performance_map", "export_motorcad_to_maxwell", "disconnect_motorcad",
})

_OPTIMIZATION_TOOL_NAMES: frozenset[str] = frozenset({
    # optiSLang
    "connect_optislang", "create_optimization_project", "add_design_variable",
    "add_response", "run_sensitivity_study", "run_optimization",
    "get_optimization_results", "get_sensitivity_results", "disconnect_optislang",
    # 参数化扫描
    "add_parametric_variable", "create_parametric_sweep", "run_parametric_sweep",
    "get_sweep_results", "create_2d_sweep",
    # DOE & 响应面
    "create_lhs_doe", "build_rsm",
})

_REPORTING_TOOL_NAMES: frozenset[str] = frozenset({
    "generate_report", "export_aedt_report",
    "create_report_session", "add_report_section", "add_table_to_report",
    "add_image_to_report", "export_report",
})

_EV_POWERTRAIN_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_ev_circuit", "create_battery_model", "create_controller_model",
    "link_motor_to_powertrain", "run_powertrain_simulation",
    "get_powertrain_results", "get_powertrain_config",
})

_NVH_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_nvh_mechanical", "connect_nvh_mapdl",
    "extract_maxwell_electromagnetic_forces", "import_forces_to_structural",
    "run_nvh_modal_analysis", "run_nvh_harmonic_response",
    "extract_vibration_noise_results", "run_nvh_full_chain",
})

_COST_TOOL_NAMES: frozenset[str] = frozenset({
    "estimate_motor_cost", "get_default_material_prices", "compare_magnet_cost",
})

# LS-DYNA 整车碰撞安全仿真工具
_CRASH_TOOL_NAMES: frozenset[str] = frozenset({
    "create_crash_deck", "load_vehicle_model", "add_crash_material",
    "add_crash_section", "add_crash_part", "add_crash_contact", "add_rigid_wall",
    "setup_frontal_crash", "setup_side_crash", "setup_rear_crash",
    "setup_pedestrian_protection", "add_initial_velocity", "add_gravity_load",
    "list_deck_keywords", "export_crash_model", "run_crash_simulation",
    "get_crash_results", "get_dummy_injury_criteria", "disconnect_crash_solver",
    "parse_glstat", "parse_nodout", "parse_rcforc", "parse_bndout",
    "compute_hic", "compute_chest_3ms", "compute_nij",
    "check_energy_balance", "get_intrusion_at_node",
    "add_node_set", "add_segment_set", "add_part_set",
    "add_constrained_rigid_bodies", "define_curve", "add_joint", "add_seatbelt",
    "place_rigid_wall_occ", "import_barrier_model", "place_dummy_model",
    "setup_airbag", "add_pretensioner",
    "evaluate_ncap_frontal", "generate_crash_report",
})

# 整车 CFD 仿真工具
_VEHICLE_CFD_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_vehicle_cfd", "load_vehicle_cfd_mesh", "setup_external_aero",
    "setup_battery_thermal_cfd", "setup_engine_bay_thermal",
    "define_vehicle_cfd_boundaries", "run_vehicle_cfd_simulation",
    "get_aero_coefficients", "get_thermal_results", "export_vehicle_cfd_results",
    "close_vehicle_cfd",
})

# 疲劳耐久仿真工具
_FATIGUE_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_fatigue_solver", "load_fatigue_model", "load_structural_results",
    "define_sn_curve", "define_en_curve", "define_load_spectrum",
    "setup_mean_stress_correction", "run_fatigue_analysis", "get_fatigue_results",
    "disconnect_fatigue_solver",
})

# 整车动力学 VD 仿真工具
_VD_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_vd_solver", "define_vehicle_params", "setup_steady_state_cornering",
    "setup_step_steering", "setup_random_road", "setup_braking_analysis",
    "setup_suspension_kinematics", "run_vd_simulation", "get_vd_results",
    "disconnect_vd_solver",
})

# 整车结构强度仿真工具
_VSTRUCT_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_structural_solver", "load_structural_model", "define_structural_material",
    "setup_boundary_conditions", "apply_bending_load", "apply_torsion_load",
    "apply_quasi_static_loads", "run_structural_analysis", "get_structural_results",
    "disconnect_structural_solver",
})

# 高级网格划分工具
_MESHING_TOOL_NAMES: frozenset[str] = frozenset({
    "launch_meshing_session", "import_geometry_for_meshing", "generate_tetrahedral_mesh",
    "generate_hex_mesh", "generate_polyhedral_mesh", "check_mesh_quality",
    "refine_mesh_locally", "export_mesh", "close_meshing_session",
})

# 整车 NVH 仿真工具
_VEHICLE_NVH_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_vehicle_nvh_solver", "load_vehicle_nvh_model", "define_nvh_materials",
    "setup_vehicle_modal_analysis", "setup_frequency_response", "setup_acoustic_analysis",
    "run_vehicle_nvh_simulation", "get_vehicle_nvh_results", "disconnect_vehicle_nvh_solver",
})

# 试验数据管理工具
_TEST_DATA_TOOL_NAMES: frozenset[str] = frozenset({
    "create_test_project", "import_test_data", "describe_nvh_test",
    "describe_vd_test", "describe_durability_test", "correlate_cae_test",
    "list_test_data", "list_test_projects", "export_test_report",
})

# 通用诊断工具（所有 Sub-Agent 共享）
_DIAGNOSTIC_TOOL_NAMES: frozenset[str] = frozenset({
    "diagnose_error", "validate_simulation_setup", "analyze_sensitivity",
    "detect_anomalies", "get_diagnostic_error_history",
    "get_ansi_error_history", "clear_ansi_error_history",
    "diagnose_ansi_error", "get_ansi_error_statistics",
})

# Main-Agent 保留的工具（跨软件协调 + 知识检索 + 技能加载 + 新功能）
_MAIN_TOOL_NAMES: frozenset[str] = frozenset({
    "link_maxwell_to_icepak", "run_em_thermal_iteration", "import_thermal_to_mechanical",
    "save_project", "open_project", "close_project", "list_designs", "copy_design",
    "build_knowledge_index", "search_official_docs",
    "list_memories", "read_memory", "save_memory", "delete_memory",
    "save_simulation_case", "search_simulation_cases",
    "use_skill",
    # 设计方案数据库
    "save_design_result", "list_design_results", "get_design_result", "compare_design_results",
    # WebGL 3D可视化工具
    "start_webgl_viewer", "stop_webgl_viewer", "export_model_to_gltf",
    "create_simulation_animation", "get_viewer_status",
    # CAD导入工具
    "import_cad_file", "import_step_file", "import_stl_file", "convert_cad_format",
    "list_supported_cad_formats", "check_cad_file", "batch_import_cad_files",
    # 仿真流程模板工具
    "list_templates", "get_template", "save_template", "delete_template",
    "validate_template", "execute_template", "create_template_from_history",
    # 云平台集成工具
    "list_cloud_providers", "configure_cloud", "get_cloud_status",
    "launch_hpc_instance", "list_hpc_instances", "terminate_hpc_instances",
    "submit_cloud_job", "get_cloud_job_status", "upload_to_cloud_storage",
    "download_from_cloud_storage", "estimate_cloud_cost",
})


def _filter_definitions(names: frozenset[str]) -> list[dict]:
    return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in names]


def _filter_registry(names: frozenset[str]) -> dict:
    return {k: v for k, v in TOOL_REGISTRY.items() if k in names}


def _agent_definitions(names: frozenset[str], include_diagnostic: bool = True) -> list[dict]:
    combined = names | _DIAGNOSTIC_TOOL_NAMES if include_diagnostic else names
    return _filter_definitions(combined)


def _agent_registry(names: frozenset[str], include_diagnostic: bool = True) -> dict:
    combined = names | _DIAGNOSTIC_TOOL_NAMES if include_diagnostic else names
    return _filter_registry(combined)


# 每个 Sub-Agent 的工具定义和注册表（均包含通用诊断工具）
MAXWELL_TOOL_DEFINITIONS = _agent_definitions(_MAXWELL_TOOL_NAMES)
MAXWELL_TOOL_REGISTRY = _agent_registry(_MAXWELL_TOOL_NAMES)

ICEPAK_TOOL_DEFINITIONS = _agent_definitions(_ICEPAK_TOOL_NAMES)
ICEPAK_TOOL_REGISTRY = _agent_registry(_ICEPAK_TOOL_NAMES)

FLUENT_TOOL_DEFINITIONS = _agent_definitions(_FLUENT_TOOL_NAMES)
FLUENT_TOOL_REGISTRY = _agent_registry(_FLUENT_TOOL_NAMES)

MAPDL_TOOL_DEFINITIONS = _agent_definitions(_MAPDL_TOOL_NAMES)
MAPDL_TOOL_REGISTRY = _agent_registry(_MAPDL_TOOL_NAMES)

MOTORCAD_TOOL_DEFINITIONS = _agent_definitions(_MOTORCAD_TOOL_NAMES)
MOTORCAD_TOOL_REGISTRY = _agent_registry(_MOTORCAD_TOOL_NAMES)

OPTIMIZATION_TOOL_DEFINITIONS = _agent_definitions(_OPTIMIZATION_TOOL_NAMES)
OPTIMIZATION_TOOL_REGISTRY = _agent_registry(_OPTIMIZATION_TOOL_NAMES)

REPORTING_TOOL_DEFINITIONS = _agent_definitions(_REPORTING_TOOL_NAMES)
REPORTING_TOOL_REGISTRY = _agent_registry(_REPORTING_TOOL_NAMES)

MAIN_TOOL_DEFINITIONS = _filter_definitions(_MAIN_TOOL_NAMES | _DIAGNOSTIC_TOOL_NAMES)
MAIN_TOOL_REGISTRY = _filter_registry(_MAIN_TOOL_NAMES | _DIAGNOSTIC_TOOL_NAMES)

EV_POWERTRAIN_TOOL_DEFINITIONS = _agent_definitions(_EV_POWERTRAIN_TOOL_NAMES)
EV_POWERTRAIN_TOOL_REGISTRY = _agent_registry(_EV_POWERTRAIN_TOOL_NAMES)

NVH_TOOL_DEFINITIONS = _agent_definitions(_NVH_TOOL_NAMES)
NVH_TOOL_REGISTRY = _agent_registry(_NVH_TOOL_NAMES)

COST_TOOL_DEFINITIONS = _agent_definitions(_COST_TOOL_NAMES)
COST_TOOL_REGISTRY = _agent_registry(_COST_TOOL_NAMES)

# LS-DYNA 整车碰撞安全仿真工具导出
CRASH_TOOL_DEFINITIONS = _agent_definitions(_CRASH_TOOL_NAMES)
CRASH_TOOL_REGISTRY = _agent_registry(_CRASH_TOOL_NAMES)

# 整车 CFD 仿真工具导出
VEHICLE_CFD_TOOL_DEFINITIONS = _agent_definitions(_VEHICLE_CFD_TOOL_NAMES)
VEHICLE_CFD_TOOL_REGISTRY = _agent_registry(_VEHICLE_CFD_TOOL_NAMES)

# 疲劳耐久仿真工具导出
FATIGUE_TOOL_DEFINITIONS = _agent_definitions(_FATIGUE_TOOL_NAMES)
FATIGUE_TOOL_REGISTRY = _agent_registry(_FATIGUE_TOOL_NAMES)

# 整车动力学 VD 仿真工具导出
VD_TOOL_DEFINITIONS = _agent_definitions(_VD_TOOL_NAMES)
VD_TOOL_REGISTRY = _agent_registry(_VD_TOOL_NAMES)

# 整车结构强度仿真工具导出
VSTRUCT_TOOL_DEFINITIONS = _agent_definitions(_VSTRUCT_TOOL_NAMES)
VSTRUCT_TOOL_REGISTRY = _agent_registry(_VSTRUCT_TOOL_NAMES)

# 高级网格划分工具导出
MESHING_TOOL_DEFINITIONS = _agent_definitions(_MESHING_TOOL_NAMES)
MESHING_TOOL_REGISTRY = _agent_registry(_MESHING_TOOL_NAMES)

# 整车 NVH 仿真工具导出
VEHICLE_NVH_TOOL_DEFINITIONS = _agent_definitions(_VEHICLE_NVH_TOOL_NAMES)
VEHICLE_NVH_TOOL_REGISTRY = _agent_registry(_VEHICLE_NVH_TOOL_NAMES)

# 试验数据管理工具导出
TEST_DATA_TOOL_DEFINITIONS = _agent_definitions(_TEST_DATA_TOOL_NAMES)
TEST_DATA_TOOL_REGISTRY = _agent_registry(_TEST_DATA_TOOL_NAMES)


def build_use_skill_definition() -> dict:
    """
    动态构建 use_skill 工具定义，description 中包含当前可用技能列表。
    在每次 LLM 调用前动态生成，确保 LLM 获知最新技能列表。
    """
    from agent.skill_manager import SkillManager
    manager = SkillManager.get_instance()
    manager.reload()
    skills = manager.get_available_skills()

    if not skills:
        description = (
            "加载专业领域技能指南，获取特定仿真任务的详细步骤和工作流程。"
            "当前没有可用技能。"
        )
        enum_values: list[str] = []
    else:
        skill_list = "\n".join(f"  - {s.name}: {s.description}" for s in skills)
        description = (
            "加载专业领域技能指南，获取特定仿真任务的详细操作步骤和工作流程。\n\n"
            "IMPORTANT: 只能使用下列技能，加载后严格按照技能内容执行。\n\n"
            f"当前可用技能：\n{skill_list}"
        )
        enum_values = [s.name for s in skills]

    skill_name_schema: dict = {
        "type": "string",
        "description": "要加载的技能名称",
    }
    if enum_values:
        skill_name_schema["enum"] = enum_values

    return {
        "type": "function",
        "function": {
            "name": "use_skill",
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {"skill_name": skill_name_schema},
                "required": ["skill_name"],
            },
        },
    }


# delegate_to_agent 的 OpenAI function calling 定义（由 MainAgent 使用）
DELEGATE_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "delegate_to_agent",
        "description": (
            "将仿真任务委托给对应的专业 Sub-Agent 执行。"
            "可用 agent_name：maxwell（电磁仿真/网格/结果/RMXprt/Circuit）、"
            "icepak（热分析）、fluent（CFD 流体/Meshing/多工况）、mapdl（结构/NVH/MapdlPool子模型/Mechanical独立模式/DPF后处理）、"
            "motorcad（Motor-CAD 解析初设计）、optimization（optiSLang优化/参数扫描）、"
            "reporting（报告生成）、"
            "ev_powertrain（EV电驱系统联仿：电池+控制器+电机）、"
            "nvh（NVH噪声振动：电磁力→结构→声学链路）、"
            "cost（电机成本估算）、"
            "crash（整车碰撞安全仿真：LS-DYNA正面/侧面/后部碰撞/行人保护）、"
            "vehicle_cfd（整车CFD仿真：外流场空气动力学/电池热管理/机舱热分析）、"
            "fatigue（疲劳耐久仿真：S-N曲线/E-N曲线/载荷谱分析）、"
            "vehicle_dynamics（整车动力学VD仿真：操稳性/平顺性/制动性能）、"
            "vehicle_structural（整车结构强度仿真：静力学/准静态/屈曲分析）、"
            "advanced_meshing（高级网格划分：结构网格/流体网格/质量检查）、"
            "vehicle_nvh（整车NVH仿真：模态分析/频率响应/声学分析）、"
            "test_data（试验数据管理：NVH试验/VD试验/耐久试验数据管理）。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "enum": [
                        "maxwell", "icepak", "fluent", "mapdl",
                        "motorcad", "optimization", "reporting",
                        "ev_powertrain", "nvh", "cost",
                        "crash", "vehicle_cfd", "fatigue",
                        "vehicle_dynamics", "vehicle_structural",
                        "advanced_meshing", "vehicle_nvh", "test_data",
                    ],
                    "description": "目标 Sub-Agent 名称",
                },
                "task": {
                    "type": "string",
                    "description": "具体任务描述（清晰、可操作的自然语言，包含全部必要参数）",
                },
                "context": {
                    "type": "string",
                    "description": "当前会话关键上下文摘要（已完成步骤、设计状态、关键数值等），帮助 Sub-Agent 理解任务背景",
                },
            },
            "required": ["agent_name", "task"],
        },
    },
}
