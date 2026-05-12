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
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "build_knowledge_index",
            "description": "构建本地知识索引，供 RAG 检索使用；可索引 docs/api 和后续补充的 knowledge 文档。",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_paths": {"type": "array", "items": {"type": "string"}, "description": "要索引的目录或文件路径列表；留空则使用默认知识目录"},
                    "force_rebuild": {"type": "boolean", "description": "是否强制重建索引，默认 True"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_official_docs",
            "description": "在本地知识索引中检索官方或内部文档片段，适合 API 用法、报错解释和推荐 workflow 问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索问题或关键词"},
                    "top_k": {"type": "integer", "description": "返回结果条数，默认 5"},
                    "source_type": {"type": "string", "description": "可选过滤类型，如 api/manual/faq/workflow"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "use_skill",
            "description": "加载专业领域技能指南，获取特定仿真任务的详细操作步骤和工作流程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "要加载的技能名称"},
                },
                "required": ["skill_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_memories",
            "description": "列出持久记忆；若提供 query，则优先返回与当前问题最相关的 memory。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "当前问题或上下文，用于筛选相关记忆"},
                    "top_k": {"type": "integer", "description": "返回数量，默认 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": "读取某条持久记忆的完整内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "memory 名称"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "保存或更新一条持久记忆，并自动更新 MEMORY.md 入口索引。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "memory 名称"},
                    "memory_type": {
                        "type": "string",
                        "enum": ["user", "feedback", "project", "reference", "simulation_case"],
                        "description": "memory 类型（simulation_case 用于自动沉淀仿真案例）",
                    },
                    "description": {"type": "string", "description": "一行摘要，用于 MEMORY.md 和相关性检索"},
                    "content": {"type": "string", "description": "memory 正文内容"},
                    "update_index": {"type": "boolean", "description": "是否同步更新 MEMORY.md，默认 true"},
                },
                "required": ["name", "memory_type", "description", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": "删除一条持久记忆，并可同步移除 MEMORY.md 中的入口索引。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "memory 名称"},
                    "remove_from_index": {"type": "boolean", "description": "是否同步移除 MEMORY.md 索引，默认 true"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_simulation_case",
            "description": (
                "仿真完成后，将任务描述、关键参数、核心结果和经验教训沉淀为仿真案例，"
                "写入 Memory 形成可检索的历史案例库。"
                "适合在每次仿真结束时自动或手动调用，积累项目知识。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "案例名称，例如 'PMSM-48s8p-转矩优化'"},
                    "task_description": {"type": "string", "description": "仿真任务的自然语言描述"},
                    "key_params": {"type": "object", "description": "关键设计参数，例如 {极对数: 8, 槽数: 48, 磁钢厚度_mm: 5}"},
                    "key_results": {"type": "object", "description": "核心仿真结果，例如 {平均转矩_Nm: 12.5, 齿槽转矩_Nm: 0.3}"},
                    "lessons_learned": {"type": "string", "description": "经验教训或结论（可选）"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表，用于辅助分类检索（可选）"},
                },
                "required": ["name", "task_description", "key_params", "key_results"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_simulation_cases",
            "description": (
                "从历史仿真案例库中检索与当前任务相关的案例。"
                "返回案例名称、描述和内容摘要，帮助复用经验、避免重复犯错。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索关键词，例如 'PMSM 转矩优化' 或 '热分析 温度'"},
                    "top_k": {"type": "integer", "description": "返回最相关的案例数量，默认 5"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # 材料库管理工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "add_material",
            "description": (
                "向本地材料库添加一条新材料（或覆盖已有材料）。"
                "独立于 AEDT，数据持久存储在本地 JSON 库中，可随时通过 export_material_for_aedt 推送到 Maxwell。"
                "适合保存自测数据、厂商规格书、标定结果等。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "材料名称（唯一标识，如 'M270-35A' 或 '武钢B27AV1400'）"},
                    "category": {
                        "type": "string",
                        "enum": ["silicon_steel", "permanent_magnet", "conductor", "other"],
                        "description": "材料分类：硅钢片/永磁体/导体/其他",
                    },
                    "description": {"type": "string", "description": "材料描述（产地、规格等）"},
                    "conductivity": {"type": "number", "description": "电导率 (S/m)"},
                    "mass_density": {"type": "number", "description": "密度 (kg/m³)"},
                    "bh_curve": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "B-H 曲线点列表 [[H1,B1],[H2,B2],...] (H:A/m, B:T)",
                    },
                    "core_loss_kh": {"type": "number", "description": "磁滞损耗系数 Kh（Steinmetz 模型）"},
                    "core_loss_kc": {"type": "number", "description": "涡流损耗系数 Kc（Steinmetz 模型）"},
                    "core_loss_ke": {"type": "number", "description": "附加损耗系数 Ke（Steinmetz 模型）"},
                    "remanence_br": {"type": "number", "description": "剩余磁感应强度 Br (T)，永磁材料专用"},
                    "coercivity_hcb": {"type": "number", "description": "矫顽力 Hcb (A/m)，永磁材料专用"},
                    "energy_product": {"type": "number", "description": "最大磁能积 BHmax (kJ/m³)，永磁材料专用"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "自定义标签列表，便于搜索"},
                    "overwrite": {"type": "boolean", "description": "若材料已存在是否覆盖，默认 false"},
                },
                "required": ["name", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_materials",
            "description": "列出本地材料库中的材料，支持按分类过滤和关键词模糊搜索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["silicon_steel", "permanent_magnet", "conductor", "other", ""],
                        "description": "按分类筛选，留空则返回全部",
                    },
                    "query": {"type": "string", "description": "按名称/描述/标签模糊搜索，留空则不过滤"},
                    "top_k": {"type": "integer", "description": "最大返回数量，默认 20"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_material",
            "description": "获取指定材料的完整详情，包括 B-H 曲线和铁耗系数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "材料名称（精确或大小写不敏感匹配）"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_material",
            "description": "从本地材料库删除一条材料（内置材料默认受保护）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "材料名称"},
                    "force": {"type": "boolean", "description": "是否强制删除内置材料，默认 false"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_bh_from_csv",
            "description": (
                "从 CSV 文件批量导入 B-H 曲线数据到本地材料库中的指定材料。"
                "CSV 格式：两列（H列和B列），支持自定义列索引，可选跳过标题行。"
                "导入后自动按 H 值升序排列，可选在材料不存在时自动创建新条目。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "material_name": {"type": "string", "description": "目标材料名称"},
                    "csv_path": {"type": "string", "description": "CSV 文件绝对路径"},
                    "h_column": {"type": "integer", "description": "H 值所在列索引（从 0 开始），默认 0"},
                    "b_column": {"type": "integer", "description": "B 值所在列索引（从 0 开始），默认 1"},
                    "skip_header": {"type": "boolean", "description": "是否跳过第一行标题，默认 true"},
                    "create_if_missing": {"type": "boolean", "description": "材料不存在时自动创建，默认 false"},
                    "category": {
                        "type": "string",
                        "enum": ["silicon_steel", "permanent_magnet", "conductor", "other"],
                        "description": "自动创建时使用的分类，默认 silicon_steel",
                    },
                },
                "required": ["material_name", "csv_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_material_for_aedt",
            "description": (
                "将本地材料库中的材料导出为 create_custom_material 工具所需的参数格式，"
                "可直接解包传入 Maxwell 工具完成材料推送。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "材料名称"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_material_metadata",
            "description": "更新材料库中已有材料的元数据字段（描述、标签、铁耗系数等），不会替换已有的 B-H 曲线。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "材料名称"},
                    "description": {"type": "string", "description": "新描述"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "新标签列表"},
                    "core_loss_kh": {"type": "number", "description": "更新磁滞损耗系数 Kh"},
                    "core_loss_kc": {"type": "number", "description": "更新涡流损耗系数 Kc"},
                    "core_loss_ke": {"type": "number", "description": "更新附加损耗系数 Ke"},
                    "conductivity": {"type": "number", "description": "更新电导率 (S/m)"},
                    "mass_density": {"type": "number", "description": "更新密度 (kg/m³)"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "connect_aedt",
            "description": "连接到运行中的 AEDT 实例或启动新实例。",
            "parameters": {
                "type": "object",
                "properties": {
                    "version": {"type": "string", "description": "AEDT 版本号，如 '2024.1'"},
                    "is_3d": {"type": "boolean", "description": "True 使用 Maxwell 3D，False 使用 Maxwell 2D"},
                    "non_graphical": {"type": "boolean", "description": "是否无界面运行（批处理模式）"},
                    "project_path": {"type": "string", "description": "项目路径或项目名；留空则连接当前活动项目"},
                    "design_name": {"type": "string", "description": "目标设计名；留空则使用当前活动设计"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_maxwell_project",
            "description": "创建新的 Maxwell 2D/3D 项目和设计。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "项目名称"},
                    "design_name": {"type": "string", "description": "设计名称"},
                },
                "required": ["project_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_motor_geometry",
            "description": "在 Maxwell 2D 中建立简化 PMSM 电机几何模型（定子、转子、永磁体、气隙）；连续尺寸会绑定为设计变量以支持扫描/优化，但 num_slots/num_poles 仍属于拓扑参数，修改后需重建几何。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stator_outer_radius": {"type": "number", "description": "定子外径（mm）"},
                    "stator_inner_radius": {"type": "number", "description": "定子内径（mm）"},
                    "rotor_outer_radius": {"type": "number", "description": "转子铁芯外径（mm，不含磁铁；磁铁贴在其外表面，需满足 rotor_outer_radius + magnet_thickness < stator_inner_radius）"},
                    "rotor_inner_radius": {"type": "number", "description": "转子内径/轴孔半径（mm）"},
                    "num_slots": {"type": "integer", "description": "定子槽数"},
                    "num_poles": {"type": "integer", "description": "极数（必须为偶数）"},
                    "magnet_thickness": {"type": "number", "description": "表贴永磁体厚度（mm），必须 < stator_inner_radius - rotor_outer_radius"},
                    "stack_length": {"type": "number", "description": "轴向叠片长度（mm），默认 50.0"},
                },
                "required": [
                    "stator_outer_radius", "stator_inner_radius",
                    "rotor_outer_radius", "rotor_inner_radius",
                    "num_slots", "num_poles", "magnet_thickness",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_material",
            "description": "为几何体对象赋予材料。",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "几何体名称"},
                    "material_name": {"type": "string", "description": "材料名称（需在 AEDT 材料库中存在）"},
                },
                "required": ["object_name", "material_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_winding",
            "description": "配置绕组相激励；未显式提供导体列表时，默认按标准三相等间隔槽位自动分组，也可切换为仅手工分组。",
            "parameters": {
                "type": "object",
                "properties": {
                    "phase_name": {"type": "string", "description": "相名称，如 PhaseA"},
                    "current_amplitude": {"type": "number", "description": "峰值电流（A）"},
                    "conductor_names": {"type": "array", "items": {"type": "string"}, "description": "导体对象名称列表；留空时将按 grouping_strategy 决定是否自动推断"},
                    "grouping_strategy": {
                        "type": "string",
                        "enum": ["three_phase_equal_spacing", "manual_only"],
                        "description": "自动槽分组策略；默认 three_phase_equal_spacing，manual_only 表示必须显式提供 conductor_names",
                    },
                    "frequency": {"type": "number", "description": "电频率（Hz），磁静态置 0"},
                    "phase_angle": {"type": "number", "description": "相位角（度）"},
                    "turns": {"type": "integer", "description": "绕组匝数，默认 1"},
                    "parallel_branches": {"type": "integer", "description": "并联支路数，默认 1"},
                    "reverse_polarity": {"type": "boolean", "description": "是否反向极性，默认 False"},
                },
                "required": ["phase_name", "current_amplitude"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_solution_setup",
            "description": "添加求解设置（瞬态 / 磁静态 / 涡流）。默认使用 Transient 瞬态求解器。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "solver_type": {"type": "string", "enum": ["Transient", "Magnetostatic", "EddyCurrent"], "description": "求解器类型，默认 Transient；提取转矩/反电动势用 Transient，提取电感/磁链用 Magnetostatic，提取涡流损耗用 EddyCurrent"},
                    "stop_time": {"type": "number", "description": "仿真结束时间（秒），solver_type=Transient 时必填，默认 0.02（一个电周期约 20ms/50Hz）"},
                    "time_step": {"type": "number", "description": "时间步长（秒），solver_type=Transient 时必填，默认 0.0001；建议为 stop_time/200 量级"},
                    "num_passes": {"type": "integer", "description": "自适应网格剖分最大迭代次数，默认 10"},
                    "frequency_Hz": {"type": "number", "description": "涡流激励频率（Hz），solver_type=EddyCurrent 时必填，默认 50"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_simulation",
            "description": "运行（求解）仿真。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_torque",
            "description": "提取平均转矩和转矩波形。需先完成 Transient 或 Magnetostatic 求解。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "sweep_name": {"type": "string", "description": "扫描/时间步名称，瞬态仿真用 'LastAdaptive'，参数扫描用对应扫描名，默认 LastAdaptive"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_back_emf",
            "description": "提取指定相的反电动势波形。",
            "parameters": {
                "type": "object",
                "properties": {
                    "phase_name": {"type": "string", "description": "相名称，如 PhaseA；需与 setup_winding 中 phase_name 一致"},
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1；必须为 Transient 类型"},
                    "sweep_name": {"type": "string", "description": "扫描/时间步名称，如 LastAdaptive"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flux_density",
            "description": "获取指定点的磁通密度幅值（Mag_B，单位 T）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "point": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3, "description": "[x, y, z] 坐标（mm），默认 [0, 0, 0]（模型原点/气隙中心）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_losses",
            "description": "获取平均铁耗和铜耗。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "sweep_name": {"type": "string", "description": "扫描/时间步名称，默认 LastAdaptive；Transient 仿真通常用 LastAdaptive"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_results",
            "description": "将仿真结果导出为 CSV 文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "输出文件路径"},
                    "result_type": {"type": "string", "enum": ["torque", "back_emf", "losses"], "description": "结果类型"},
                },
                "required": ["output_path"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # optiSLang 工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_optislang",
            "description": "连接到运行中的 optiSLang 实例。",
            "parameters": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "主机名，默认 localhost"},
                    "port": {"type": "integer", "description": "gRPC 端口，默认 5310"},
                    "timeout": {"type": "integer", "description": "连接超时（秒）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_optimization_project",
            "description": "创建新的 optiSLang 优化项目，选择优化算法。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "项目名称"},
                    "algorithm": {"type": "string", "enum": ["ARSM", "NLPQL", "EA", "OMSTSP"], "description": "优化算法"},
                    "max_iterations": {"type": "integer", "description": "最大迭代次数"},
                },
                "required": ["project_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_design_variable",
            "description": "添加优化设计变量，设定取值范围；会尽量验证该变量已绑定到当前 Maxwell 设计，且不允许把 num_slots/num_poles 这类拓扑参数误当成连续变量。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "变量名（需与当前 Maxwell 设计中已存在的连续参数一致）"},
                    "lower_bound": {"type": "number", "description": "下限"},
                    "upper_bound": {"type": "number", "description": "上限"},
                    "initial_value": {"type": "number", "description": "初始值"},
                    "reference_value": {"type": "number", "description": "参考值；留空则跟随 initial_value"},
                },
                "required": ["name", "lower_bound", "upper_bound"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_response",
            "description": "添加优化响应（目标函数或约束条件）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "响应名称（仿真输出变量名）"},
                    "response_type": {"type": "string", "enum": ["objective", "constraint"], "description": "类型"},
                    "target": {"type": "string", "enum": ["minimize", "maximize"], "description": "优化方向（仅 objective）"},
                    "limit": {"type": "number", "description": "约束限值（仅 constraint）"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sensitivity_study",
            "description": "运行参数敏感性分析，识别关键设计变量。",
            "parameters": {
                "type": "object",
                "properties": {
                    "num_designs": {"type": "integer", "description": "采样设计点数量"},
                    "method": {"type": "string", "enum": ["MOP", "LHS", "SOBOL"], "description": "敏感性方法"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_optimization",
            "description": "启动参数优化运行。",
            "parameters": {
                "type": "object",
                "properties": {
                    "algorithm": {"type": "string", "enum": ["ARSM", "NLPQL", "EA", "OMSTSP"], "description": "优化算法"},
                    "max_iterations": {"type": "integer", "description": "最大迭代次数"},
                    "num_parallel_runs": {"type": "integer", "description": "并行仿真数量"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_optimization_results",
            "description": "获取优化完成后的最优设计参数和目标值，并尽量返回项目/工作流来源以及与最近一次优化上下文的一致性提示。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sensitivity_results",
            "description": "获取敏感性分析结果，返回各参数对响应的影响系数。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disconnect_optislang",
            "description": "断开与 optiSLang 的连接并释放资源。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # Icepak 热分析工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_icepak",
            "description": "连接到 AEDT Icepak 热仿真实例。",
            "parameters": {
                "type": "object",
                "properties": {
                    "version": {"type": "string", "description": "AEDT 版本，如 '2024.1'"},
                    "non_graphical": {"type": "boolean", "description": "是否以无界面批处理模式运行，默认 False"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_motor_thermal",
            "description": "设置电机热分析边界条件（铜耗/铁耗热源和冷却方式）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "copper_loss_W": {"type": "number", "description": "绕组铜耗（W）"},
                    "iron_loss_W": {"type": "number", "description": "铁芯铁耗（W）"},
                    "ambient_temp_C": {"type": "number", "description": "环境温度（°C）"},
                    "cooling_type": {"type": "string", "enum": ["natural_convection", "forced_convection", "water_jacket"]},
                },
                "required": ["copper_loss_W", "iron_loss_W"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_thermal_simulation",
            "description": "运行 Icepak 稳态热仿真。",
            "parameters": {"type": "object", "properties": {"setup_name": {"type": "string"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_temperature_results",
            "description": "获取各部件（绕组/定子/转子）的最高和平均温度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_names": {"type": "array", "items": {"type": "string"}, "description": "几何体名称列表"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # Maxwell Circuit 驱动器联仿工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_circuit",
            "description": "连接到 Maxwell Circuit Editor。",
            "parameters": {
                "type": "object",
                "properties": {
                    "version": {"type": "string"},
                    "non_graphical": {"type": "boolean", "description": "是否无界面运行（批处理模式）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_inverter_circuit",
            "description": "创建三相两电平 IGBT 逆变器拓扑电路。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dc_voltage_V": {"type": "number", "description": "直流母线电压（V）"},
                    "switching_freq_Hz": {"type": "number", "description": "开关频率（Hz）"},
                    "dead_time_us": {"type": "number", "description": "死区时间（μs）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "link_maxwell_to_circuit",
            "description": "将 Maxwell 电机设计动态链接到 Circuit，实现驱动器+电机联合仿真。",
            "parameters": {
                "type": "object",
                "properties": {
                    "maxwell_design_name": {"type": "string", "description": "Maxwell 设计名称"},
                },
                "required": ["maxwell_design_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_circuit_simulation",
            "description": "运行驱动器+电机联合瞬态仿真。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_time_ms": {"type": "number", "description": "总仿真时间（ms）"},
                    "time_step_us": {"type": "number", "description": "时间步（μs）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_circuit_results",
            "description": "提取电路仿真波形（相电流、母线电压等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "signals": {"type": "array", "items": {"type": "string"}, "description": "信号名列表"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # Mechanical 结构振动工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_mechanical",
            "description": "连接到 Ansys Mechanical 实例。",
            "parameters": {"type": "object", "properties": {"version": {"type": "string", "description": "Ansys 版本号，三位整数字符串，如 '242'（2024 R2）、'241'（2024 R1）、'251'（2025 R1），默认 '242'"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_maxwell_forces",
            "description": "将 Maxwell 电磁力导入 Mechanical 作为激励（用于 NVH 分析）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "maxwell_project_path": {"type": "string", "description": "Maxwell 项目路径（.aedt）"},
                    "design_name": {"type": "string", "description": "Maxwell 设计名称；留空则使用导入对象默认设计"},
                    "setup_name": {"type": "string"},
                },
                "required": ["maxwell_project_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_modal_analysis",
            "description": "运行电机模态分析，提取固有频率和振型。",
            "parameters": {
                "type": "object",
                "properties": {
                    "num_modes": {"type": "integer", "description": "提取模态阶数，默认 12"},
                    "freq_range_hz": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "description": "[f_min, f_max] 频率范围（Hz），默认 [0, 10000]，例如 [0, 5000]"},
                    "analysis_name": {"type": "string", "description": "Mechanical 中的目标分析名称，默认 Modal"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_harmonic_analysis",
            "description": "运行谐响应分析（NVH），评估电机振动噪声。",
            "parameters": {
                "type": "object",
                "properties": {
                    "freq_range_hz": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "description": "[f_min, f_max] 频率扫描范围（Hz），默认 [0, 5000]，例如 [0, 3000]"},
                    "num_steps": {"type": "integer", "description": "频率步数，默认 100"},
                    "damping_ratio": {"type": "number", "description": "结构阻尼比（无量纲），钢结构约 0.01~0.03，默认 0.02"},
                    "analysis_name": {"type": "string", "description": "Mechanical 中的目标分析名称，默认 Harmonic Response"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vibration_results",
            "description": "获取固有频率列表和振动结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_name": {"type": "string", "description": "Mechanical 中的分析名称；留空则使用第一个分析"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # Mechanical 独立批处理模式工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "launch_mechanical_standalone",
            "description": "以独立批处理模式启动 Ansys Mechanical（通过 ansys-mechanical-core），适用于不依赖 AEDT 的 PCB 热分析、排气歧管热力耦合等完整 Mechanical 工作流。",
            "parameters": {
                "type": "object",
                "properties": {
                    "batch": {"type": "boolean", "description": "True 以批处理模式运行（无图形界面），默认 True"},
                    "cleanup_on_exit": {"type": "boolean", "description": "退出时自动清理临时文件，默认 False"},
                    "version": {"type": "string", "description": "Ansys 版本号，如 '251'（2025 R1）；None 使用默认安装版本"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mechanical_run_script",
            "description": "在当前 Mechanical 会话中执行任意 Python/ACT 脚本，返回脚本输出，适用于独立批处理模式下精细控制 Mechanical 操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {"type": "string", "description": "要在 Mechanical 中执行的 Python 脚本字符串"},
                },
                "required": ["script"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mechanical_upload_file",
            "description": "将本地文件上传到 Mechanical 服务器项目目录（独立批处理模式专用），用于传递几何文件、材料 XML、CFD 结果 CSV 等输入文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "local_file_path": {"type": "string", "description": "本地文件的绝对路径"},
                },
                "required": ["local_file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mechanical_download_file",
            "description": "从 Mechanical 服务器项目目录下载结果文件（图片、数据等）到本地。",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_file_path": {"type": "string", "description": "服务器上的文件完整路径"},
                    "local_target_dir": {"type": "string", "description": "本地目标目录"},
                },
                "required": ["server_file_path", "local_target_dir"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_steady_state_thermal",
            "description": "在独立 Mechanical 中执行稳态热分析：导入几何 → 设置内热源 → 设置对流边界 → 求解 → 导出结果图。适用于 PCB/芯片热设计工作流。",
            "parameters": {
                "type": "object",
                "properties": {
                    "geometry_file_var": {"type": "string", "description": "Mechanical 会话中已定义的几何文件路径变量名，默认 'geometry_path'"},
                    "internal_heat_gen_w_m3": {"type": "number", "description": "内热生成率（W/m³），默认 5e7"},
                    "heated_component_ns": {"type": "string", "description": "施加内热的命名选择名称，默认 'ic-6'"},
                    "convection_film_coeff": {"type": "number", "description": "对流换热系数（W/m²·°C），默认 5.0"},
                    "convection_ns": {"type": "string", "description": "施加对流的命名选择名称，默认 'all_bodies'"},
                    "output_dir": {"type": "string", "description": "结果图导出目录；None 则使用 Mechanical 项目目录"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_fluent_htc_to_mechanical",
            "description": "将 Fluent CHT 分析导出的 HTC/温度 CSV 文件作为外部数据导入 Mechanical，用于瞬态热分析的对流边界条件映射（排气歧管热力耦合工作流）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "csv_file_vars": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Mechanical 会话中已定义的 CSV 文件路径变量名列表（如 ['temp_htc_data_high_path', 'temp_htc_data_med_path']）",
                    },
                    "csv_labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "每个文件对应的标签（如 ['High', 'Med', 'Low']），用于时间步映射",
                    },
                    "target_ns": {"type": "string", "description": "施加导入对流的命名选择名称（Mechanical 中的 interface 面），默认 'interface_surface'"},
                },
                "required": ["csv_file_vars", "csv_labels"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mechanical_exit",
            "description": "退出当前 Mechanical 会话并释放资源（独立批处理模式专用），每次完成分析后应调用以避免进程残留。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # 参数化扫描工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "add_parametric_variable",
            "description": "在 Maxwell 设计中添加参数化变量。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "变量名，需符合 AEDT 变量命名规则（字母/数字/下划线，不以数字开头），如 'air_gap'、'magnet_thickness'"},
                    "value": {"type": "number", "description": "初始值（数值部分，单位由 unit 参数指定）"},
                    "unit": {"type": "string", "description": "AEDT 单位字符串，默认 'mm'；几何尺寸用 'mm'，角度用 'deg'，电流用 'A'，转速用 'rpm'，时间用 's'；必须与 AEDT 单位系统兼容"},
                },
                "required": ["name", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_parametric_sweep",
            "description": "创建单参数线性扫描（start 到 stop，步长 step），并校验变量、setup 与结果表达式是否匹配当前模型状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "param_name": {"type": "string"},
                    "start": {"type": "number"},
                    "stop": {"type": "number"},
                    "step": {"type": "number"},
                    "setup_name": {"type": "string"},
                    "result_expressions": {"type": "array", "items": {"type": "string"}, "description": "扫描时要计算的结果表达式列表；留空则自动推断"},
                },
                "required": ["param_name", "start", "stop", "step"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_parametric_sweep",
            "description": "执行参数化扫描仿真。",
            "parameters": {
                "type": "object",
                "properties": {"sweep_name": {"type": "string", "description": "扫描名称，空则运行全部"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sweep_results",
            "description": "提取参数扫描结果，返回参数-结果映射及最优点。",
            "parameters": {
                "type": "object",
                "properties": {
                    "param_name": {"type": "string"},
                    "result_expression": {"type": "string", "description": "结果表达式，支持别名：'Torque'（自动映射为 Moving1.Torque）、'CoreLoss'、'OhmicLoss'；必须与 create_parametric_sweep 中 result_expressions 所配置的表达式一致"},
                    "sweep_name": {"type": "string", "description": "扫描名称，留空则使用最近一次参数扫描"},
                },
                "required": ["param_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_2d_sweep",
            "description": "创建二维参数扫描（两个参数的笛卡尔积），适合效率 MAP，并校验变量、setup 与结果表达式是否匹配当前模型状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1_name": {"type": "string"},
                    "param1_values": {"type": "array", "items": {"type": "number"}},
                    "param2_name": {"type": "string"},
                    "param2_values": {"type": "array", "items": {"type": "number"}},
                    "setup_name": {"type": "string"},
                    "result_expressions": {"type": "array", "items": {"type": "string"}, "description": "扫描时要计算的结果表达式列表；留空则自动推断"},
                },
                "required": ["param1_name", "param1_values", "param2_name", "param2_values"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # 报告生成工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "生成电机仿真 HTML/Markdown 报告，汇总所有结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "报告输出路径"},
                    "motor_name": {"type": "string", "description": "电机名称"},
                    "results": {"type": "object", "description": "仿真结果字典（转矩/损耗/温度等）"},
                    "format": {"type": "string", "enum": ["html", "markdown"], "description": "报告格式"},
                },
                "required": ["output_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_aedt_report",
            "description": "将 AEDT 中已有的所有 Report 导出为 CSV 和图片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_dir": {"type": "string", "description": "输出目录"},
                    "report_names": {"type": "array", "items": {"type": "string"}, "description": "指定报告名，None 则导出全部"},
                },
                "required": ["output_dir"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # Fluent 流体分析工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_fluent",
            "description": "启动 Ansys Fluent 求解器会话（通过 ansys-fluent-core）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "version": {"type": "string", "description": "Fluent 版本号，如 '23.2'（2023 R2）、'24.1'（2024 R1）"},
                    "precision": {"type": "string", "enum": ["double", "single"], "description": "计算精度，double 推荐"},
                    "processors": {"type": "integer", "description": "并行进程数（CPU 核心数），默认 4"},
                    "mode": {"type": "string", "enum": ["solver", "meshing"], "description": "运行模式，默认 solver"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_fluent_mesh",
            "description": "读取网格或 Case 文件到 Fluent（支持 .msh、.msh.gz、.cas、.cas.gz）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mesh_file_path": {"type": "string", "description": "网格/Case 文件的完整路径"},
                },
                "required": ["mesh_file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_fluid_models",
            "description": "配置 Fluent 流体物理模型，包括湍流模型和能量方程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "viscous_model": {
                        "type": "string",
                        "enum": ["laminar", "k-epsilon", "k-omega", "sst", "realizable-ke", "rng-ke"],
                        "description": "湍流模型：laminar/k-epsilon/k-omega/sst/realizable-ke/rng-ke",
                    },
                    "k_epsilon_variant": {
                        "type": "string",
                        "enum": ["standard", "rng", "realizable"],
                        "description": "k-epsilon 子模型，viscous_model=k-epsilon 时有效",
                    },
                    "energy_on": {"type": "boolean", "description": "是否开启能量方程（温度计算），默认 false"},
                    "turbulence_intensity": {"type": "number", "description": "湍流强度（0~1），默认 0.05（5%）"},
                    "turbulent_length_scale": {"type": "number", "description": "湍流长度尺度（m）；留空则自动估算"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "define_boundary_conditions",
            "description": "为指定边界面设定边界条件（速度入口、压力入口/出口、壁面等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "boundary_name": {"type": "string", "description": "边界名称，与网格定义一致，如 'inlet'、'outlet'"},
                    "bc_type": {
                        "type": "string",
                        "enum": ["velocity-inlet", "pressure-inlet", "pressure-outlet", "wall"],
                        "description": "边界类型",
                    },
                    "velocity_magnitude": {"type": "number", "description": "速度大小（m/s），velocity-inlet 必填"},
                    "pressure_value": {"type": "number", "description": "表压（Pa），pressure-inlet/outlet 使用"},
                    "temperature": {"type": "number", "description": "温度（K），开启能量方程时设置"},
                    "turbulence_intensity": {"type": "number", "description": "湍流强度（0~1），默认 0.05"},
                    "hydraulic_diameter": {"type": "number", "description": "水力直径（m），用于湍流参数估算"},
                },
                "required": ["boundary_name", "bc_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_fluent_solver",
            "description": "配置 Fluent 求解算法和收敛参数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "scheme": {
                        "type": "string",
                        "enum": ["coupled", "simple"],
                        "description": "求解算法：coupled（耦合，推荐）或 simple（分离）",
                    },
                    "convergence_absolute": {"type": "number", "description": "收敛绝对残差标准，默认 1e-4"},
                    "max_iterations": {"type": "integer", "description": "最大迭代步数，默认 500"},
                    "under_relaxation_velocity": {"type": "number", "description": "速度亚松弛因子（SIMPLE 专用），默认 0.7"},
                    "under_relaxation_pressure": {"type": "number", "description": "压力亚松弛因子（SIMPLE 专用），默认 0.3"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "initialize_fluent",
            "description": "初始化 Fluent 流场（混合初始化或标准初始化）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["hybrid", "standard"],
                        "description": "初始化方法：hybrid（推荐）或 standard",
                    },
                    "reference_velocity": {"type": "number", "description": "参考速度（m/s），standard 方法用"},
                    "reference_pressure": {"type": "number", "description": "参考压力（Pa），standard 方法用"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_fluent_simulation",
            "description": "执行 Fluent 稳态迭代计算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "iterations": {"type": "integer", "description": "最大迭代步数，默认 300；留空则复用 setup_fluent_solver 中设置的 max_iterations"},
                    "report_interval": {"type": "integer", "description": "残差报告输出间隔（步数），默认 10"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fluent_results",
            "description": "提取指定边界面的流场结果（面积加权平均值），自动计算压降。",
            "parameters": {
                "type": "object",
                "properties": {
                    "surfaces": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要提取结果的面名称列表，如 ['inlet', 'outlet']；None 则使用默认",
                    },
                    "quantities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "物理量列表，如 ['pressure', 'velocity-magnitude', 'temperature', 'wall-shear-stress']",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_fluent_data",
            "description": "将 Fluent 仿真结果导出为 CSV 文件或保存 Case+Data 文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "输出文件路径（不含扩展名则自动追加）"},
                    "surfaces": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要导出的边界面列表；None 则使用 inlet/outlet",
                    },
                    "quantities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要导出的物理量列表；None 则使用默认量",
                    },
                    "export_format": {
                        "type": "string",
                        "enum": ["csv", "case-data"],
                        "description": "导出格式：csv（表格）或 case-data（保存 .cas.gz+.dat.gz）",
                    },
                },
                "required": ["output_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_fluid_material",
            "description": "配置 Fluent 流体域的物性参数（密度、动力黏度、导热系数、比热容）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_name": {
                        "type": "string",
                        "description": "材料名称，默认 'air'；支持 'water-liquid'、'water-vapor' 等内置材料",
                    },
                    "density": {"type": "number", "description": "密度（kg/m³），None 保持默认值"},
                    "viscosity": {"type": "number", "description": "动力黏度（Pa·s），None 保持默认值"},
                    "thermal_conductivity": {"type": "number", "description": "导热系数（W/(m·K)），开启能量方程时生效"},
                    "specific_heat": {"type": "number", "description": "比热容（J/(kg·K)），开启能量方程时生效"},
                    "density_model": {
                        "type": "string",
                        "enum": ["constant", "ideal-gas", "boussinesq"],
                        "description": "密度模型：constant（常数）、ideal-gas（理想气体）、boussinesq（自然对流近似）",
                    },
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # Fluent Meshing & 参数化多工况工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "launch_fluent_meshing",
            "description": "启动 Fluent Meshing 模式，用于 Watertight Geometry 或 Fault-tolerant 工作流网格划分，与 connect_fluent（solver 模式）互相独立。",
            "parameters": {
                "type": "object",
                "properties": {
                    "precision": {"type": "string", "enum": ["double", "single"], "description": "浮点精度，推荐 double"},
                    "processors": {"type": "integer", "description": "并行进程数，默认 4"},
                    "cwd": {"type": "string", "description": "工作目录，网格文件写入此目录；None 则使用当前目录"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_watertight_meshing_workflow",
            "description": "在 Fluent Meshing 模式下执行完整的 Watertight Geometry 网格工作流：导入几何 → 曲面网格 → 描述几何 → 更新边界/区域 → 边界层 → 体网格 → 写出网格。",
            "parameters": {
                "type": "object",
                "properties": {
                    "geometry_file": {"type": "string", "description": "几何文件路径（PMDB、FMD 等）"},
                    "output_mesh_file": {"type": "string", "description": "输出网格文件路径（.msh.h5）"},
                    "surface_min_size": {"type": "number", "description": "曲面网格最小尺寸，默认 2.0"},
                    "surface_max_size": {"type": "number", "description": "曲面网格最大尺寸，默认 1000.0"},
                    "volume_fill_type": {"type": "string", "enum": ["poly-hexcore", "tetrahedral"], "description": "体网格填充类型，默认 poly-hexcore"},
                    "num_boundary_layers": {"type": "integer", "description": "边界层层数，默认 12"},
                    "hex_max_cell_length": {"type": "number", "description": "poly-hexcore 最大六面体单元尺寸，默认 512.0"},
                },
                "required": ["geometry_file", "output_mesh_file"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_named_expression",
            "description": "在 Fluent 中创建命名表达式（Named Expression），可在边界条件中引用，适用于参数化仿真（如 CHT 多工况分析）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "表达式名称（英文，无空格）"},
                    "definition": {"type": "string", "description": "表达式定义字符串，例如 '1023.15 [K]'"},
                    "is_input_parameter": {"type": "boolean", "description": "是否标记为输入参数（可在参数研究中扫描），默认 False"},
                },
                "required": ["name", "definition"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_cell_zone_material",
            "description": "为 Fluent 中的流体或固体 Cell Zone 指定材料，自动适配 Fluent 2024 R2 前后的 API 变化。",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_name": {"type": "string", "description": "Cell Zone 名称，支持通配符（如 '*fluid*'）"},
                    "material_name": {"type": "string", "description": "材料名称（已在 Fluent 材料库中存在）"},
                    "zone_type": {"type": "string", "enum": ["fluid", "solid"], "description": "区域类型，默认 fluid"},
                },
                "required": ["zone_name", "material_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_named_expression",
            "description": "更新已有命名表达式的定义值，用于多工况参数化仿真循环（如逐工况更新入口温度）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "已存在的表达式名称"},
                    "new_definition": {"type": "string", "description": "新的表达式定义字符串，例如 '683.15 [K]'"},
                },
                "required": ["name", "new_definition"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_surface_data_ascii",
            "description": "将指定边界面的仿真数据导出为 ASCII/CSV 文件，供 Mechanical 热力耦合映射使用（如导出 HTC 和温度）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_file": {"type": "string", "description": "输出文件名（含扩展名，如 'htc_temp.csv'）"},
                    "surface_names": {"type": "array", "items": {"type": "string"}, "description": "要导出的边界面名称列表"},
                    "quantities": {"type": "array", "items": {"type": "string"}, "description": "要导出的物理量列表；None 则默认导出 temperature 和 heat-transfer-coef-wall"},
                    "location": {"type": "string", "enum": ["node", "cell"], "description": "数据位置，默认 node"},
                    "delimiter": {"type": "string", "enum": ["comma", "tab"], "description": "分隔符，默认 comma"},
                },
                "required": ["output_file", "surface_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_multi_condition_simulation",
            "description": "批量运行多个工况的 Fluent 仿真，每个工况更新一个命名表达式参数后迭代求解，并将 case+data 文件保存至指定目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "parameter_name": {"type": "string", "description": "要在各工况中更新的命名表达式名称（如 'in_temperature'）"},
                    "condition_list": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string", "description": "工况标签（用于文件命名）"},
                                "value": {"type": "string", "description": "该工况的参数值字符串，如 '1023.15 [K]'"},
                            },
                            "required": ["label", "value"],
                        },
                        "description": "工况列表",
                    },
                    "output_dir": {"type": "string", "description": "结果文件保存目录，默认 '.'"},
                    "iterations_per_case": {"type": "integer", "description": "每个工况的迭代步数，默认 200"},
                },
                "required": ["parameter_name", "condition_list"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_fluent",
            "description": "退出当前 Fluent 会话（solver 或 meshing 模式），释放进程资源。每次完成仿真后应调用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # 自定义材料工具定义（Maxwell）
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_custom_material",
            "description": "在 AEDT 材料库中创建自定义电磁材料，支持 B-H 曲线和铁耗系数（Steinmetz 模型）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_name": {"type": "string", "description": "材料名称；若已存在则覆盖修改"},
                    "conductivity": {"type": "number", "description": "电导率（S/m），硅钢片典型值 1.9e6~2.0e6"},
                    "mass_density": {"type": "number", "description": "质量密度（kg/m³），默认 7650"},
                    "permeability": {"type": "number", "description": "相对磁导率（常数）；提供 bh_curve 时忽略"},
                    "bh_curve": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "number"}},
                        "description": "B-H 曲线数据点列表 [[H1,B1],[H2,B2],...]，H 单位 A/m，B 单位 T",
                    },
                    "core_loss_kh": {"type": "number", "description": "磁滞损耗系数 Kh（Steinmetz 模型）"},
                    "core_loss_kc": {"type": "number", "description": "涡流损耗系数 Kc（Steinmetz 模型）"},
                    "core_loss_ke": {"type": "number", "description": "附加损耗系数 Ke（Steinmetz 模型）"},
                },
                "required": ["material_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_bh_curve",
            "description": "从 CSV 文件导入 B-H 数据到已有自定义材料（覆盖非线性磁导率）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_name": {"type": "string", "description": "目标材料名称（须已通过 create_custom_material 创建）"},
                    "csv_path": {"type": "string", "description": "CSV 文件绝对路径"},
                    "h_column": {"type": "integer", "description": "H 值所在列索引（从0开始），默认 0"},
                    "b_column": {"type": "integer", "description": "B 值所在列索引（从0开始），默认 1"},
                    "skip_header": {"type": "boolean", "description": "是否跳过首行标题，默认 true"},
                },
                "required": ["material_name", "csv_path"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # 外部 CAD 几何导入工具定义（Maxwell）
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "import_cad_geometry",
            "description": (
                "将外部 3D CAD 文件（STEP / IGES / SAT）导入到当前 Maxwell 或 Maxwell3D 设计中。"
                "支持来自 NX、SolidWorks、Creo、SpaceClaim 等 CAD 软件导出的标准中性格式。"
                "导入后需使用 assign_material 为各部件赋予材料属性。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "CAD 文件绝对路径（支持 .step / .stp / .iges / .igs / .sat）",
                    },
                    "design_name": {
                        "type": "string",
                        "description": "目标设计名称；留空则使用当前活跃设计",
                    },
                    "scale_factor": {
                        "type": "number",
                        "description": "几何缩放系数，默认 1.0（不缩放）。若 CAD 单位为 mm 而仿真单位为 m，则填 0.001",
                    },
                    "merge_objects": {
                        "type": "boolean",
                        "description": "是否将导入的各子部件合并为单一实体，默认 false（保留各子部件以便分别赋材料）",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_dxf",
            "description": (
                "将 AutoCAD DXF 文件导入到当前 Maxwell2D 设计中，作为 2D 截面几何。"
                "适用于在 AutoCAD/其他 CAD 中绘制的电机横截面轮廓。"
                "注意：不支持直接导入 .dwg，需在 AutoCAD 中先另存为 DXF 格式。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "DXF 文件绝对路径（.dxf）",
                    },
                    "layers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要导入的图层名称列表；留空则导入 DXF 中全部图层",
                    },
                    "auto_cover": {
                        "type": "boolean",
                        "description": "是否自动将封闭多段线转为覆盖区域（Cover surface），默认 true。建议保持 true 以便直接赋材料和网格",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # 项目管理工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "save_project",
            "description": "保存当前 AEDT 项目（原路径覆盖或另存为新路径）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "另存路径（含 .aedt 扩展名），留空则原路径保存"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_project",
            "description": "在当前 AEDT 会话中打开已有项目文件（.aedt）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "项目 .aedt 文件绝对路径"},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_project",
            "description": "关闭指定项目（或当前活动项目），可选关闭前保存。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "项目名称，留空则关闭当前项目"},
                    "save_first": {"type": "boolean", "description": "关闭前是否保存，默认 true"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_designs",
            "description": "列出当前项目中所有设计的名称、数量及当前活动设计。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "copy_design",
            "description": "在当前项目中复制一个设计，适用于多方案对比和参数研究。",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_design": {"type": "string", "description": "源设计名称"},
                    "new_name": {"type": "string", "description": "新设计名称"},
                },
                "required": ["source_design", "new_name"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # 网格控制工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "setup_length_mesh",
            "description": "对指定几何体分配基于长度的网格细化操作（通用精度控制）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_names": {"type": "array", "items": {"type": "string"}, "description": "几何体名称列表"},
                    "max_element_length": {"type": "number", "description": "最大单元边长（mm）"},
                    "max_elements": {"type": "integer", "description": "最大单元数上限，None 不限制"},
                    "operation_name": {"type": "string", "description": "网格操作名称，默认 LengthBased"},
                },
                "required": ["object_names", "max_element_length"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_skin_depth_mesh",
            "description": "为导体/导磁体表面分配集肤深度细化（涡流/高频仿真必备）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_names": {"type": "array", "items": {"type": "string"}, "description": "几何体名称列表"},
                    "skin_depth_mm": {"type": "number", "description": "集肤深度（mm）"},
                    "max_triangle_length_mm": {"type": "number", "description": "表面三角形最大边长（mm），建议取 skin_depth 的 2~5 倍"},
                    "num_layers": {"type": "integer", "description": "集肤深度内细化层数，默认 2"},
                    "operation_name": {"type": "string", "description": "网格操作名称，默认 SkinDepth"},
                },
                "required": ["object_names", "skin_depth_mm", "max_triangle_length_mm"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_surface_mesh",
            "description": "为圆弧/曲面几何（气隙、磁极弧面）分配曲面近似网格操作。",
            "parameters": {
                "type": "object",
                "properties": {
                    "object_names": {"type": "array", "items": {"type": "string"}, "description": "几何体名称列表"},
                    "surface_quality": {"type": "integer", "description": "曲面质量等级 1~10，默认 8"},
                    "operation_name": {"type": "string", "description": "网格操作名称，默认 SurfaceApprox"},
                },
                "required": ["object_names"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mesh_stats",
            "description": "获取指定求解设置的网格统计信息（单元数、节点数等），需在求解后调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # 电磁-热耦合工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "link_maxwell_to_icepak",
            "description": "将 Maxwell 仿真损耗（铁耗+铜耗）自动映射到 Icepak 热分析模型，替代手动填值，是全自动 EM-Thermal 耦合的关键步骤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "maxwell_design_name": {"type": "string", "description": "Maxwell 设计名称；留空则使用当前活动设计"},
                    "setup_name": {"type": "string", "description": "Maxwell 求解设置名称，默认 Setup1"},
                    "use_spatial_distribution": {
                        "type": "boolean",
                        "description": "True 使用空间分布损耗映射（精度高，3D 推荐）；False 使用均匀平均值（速度快，2D 适用）",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_em_thermal_iteration",
            "description": "运行 Maxwell-Icepak 耦合迭代：电磁→损耗映射→热仿真→温度反馈→重复，直至温度收敛。",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_iterations": {"type": "integer", "description": "最大耦合迭代次数，推荐 2~5，默认 3"},
                    "convergence_temp_delta": {"type": "number", "description": "收敛判据：相邻两轮最高温度差（°C），默认 1.0"},
                    "maxwell_setup_name": {"type": "string", "description": "Maxwell 求解设置名称，默认 Setup1"},
                    "icepak_setup_name": {"type": "string", "description": "Icepak 求解设置名称，默认 SetupThermal"},
                    "feedback_mode": {
                        "type": "string",
                        "enum": ["one_way", "two_way"],
                        "description": "耦合模式：one_way 为单向热迭代；two_way 为严格双向温度反馈",
                    },
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # P2 高级结果工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_inductance",
            "description": "提取 PMSM d 轴电感 Ld 和 q 轴电感 Lq（通过相自感近似），返回各相自感及 Ld/Lq 估算值。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "sweep_name": {"type": "string", "description": "扫描/时间步名称，默认 LastAdaptive"},
                    "phases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "三相名称列表，默认 ['PhaseA','PhaseB','PhaseC']",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flux_linkage",
            "description": "提取各相绕组磁链波形（ψA/ψB/ψC），并计算峰值和 dq 磁链分量（ψd、ψq）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "sweep_name": {"type": "string", "description": "扫描名称，默认 LastAdaptive"},
                    "phases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "三相名称列表，默认 ['PhaseA','PhaseB','PhaseC']",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cogging_torque",
            "description": "提取 PMSM 齿槽转矩波形及峰峰值，需在零电流参数化磁静态仿真完成后调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "sweep_name": {"type": "string", "description": "参数扫描名称（转子位置扫描），默认 LastAdaptive"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_efficiency_map",
            "description": "从二维参数扫描（转速×电流）结果聚合生成效率 MAP，返回各工况效率和最高效率点。",
            "parameters": {
                "type": "object",
                "properties": {
                    "speed_param": {"type": "string", "description": "转速参数变量名，默认 'Speed'"},
                    "current_param": {"type": "string", "description": "电流参数变量名，默认 'Current'"},
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "sweep_name": {"type": "string", "description": "参数扫描名称，空则使用全部"},
                    "rated_voltage": {"type": "number", "description": "额定直流母线电压（V），默认 400"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_demagnetization",
            "description": "校核永磁体在极端工况下的退磁安全裕量，自动识别磁体对象并计算温度修正后的 H-Hcb 安全系数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称（应为短路/过载工况），默认 Setup1"},
                    "sweep_name": {"type": "string", "description": "扫描名称，默认 LastAdaptive"},
                    "magnet_objects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "永磁体几何体名称列表；None 则自动搜索含 'Magnet'/'PM' 的对象",
                    },
                    "operating_temperature_C": {"type": "number", "description": "永磁体工作温度（°C），用于 NdFe35 矫顽力温度修正（线性系数 -0.6%/°C），默认 120；有效范围 0~185°C，超过 186°C 线性模型失效工具会拒绝计算"},
                    "safety_margin": {"type": "number", "description": "退磁安全裕量阈值（0~1），低于此值报警，默认 0.1（10%）；0 表示不报警，0.2 表示要求 20% 安全裕量"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # P3 RMXprt 快速初设计工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_rmxprt",
            "description": "连接到 Ansys RMXprt 解析法电机设计模块，用于快速初始参数估算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "version": {"type": "string", "description": "AEDT 版本号，如 '2024.1'"},
                    "non_graphical": {"type": "boolean", "description": "是否无界面运行"},
                    "motor_type": {
                        "type": "string",
                        "enum": ["PMSM", "BLDC", "IM", "SRM", "PMDC", "SYN", "SYNRM", "GRM"],
                        "description": "电机类型，决定 RMXprt 的 solution_type：PMSM（三相永磁同步，最常用）、BLDC（无刷直流）、IM（三相感应）、SRM（开关磁阻）、PMDC（永磁直流）、SYN（三相同步）、SYNRM（线启动同步磁阻）、GRM（通用旋转电机，默认）；应与后续 create_motor_from_template 的 motor_type 保持一致",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_motor_from_template",
            "description": "在 RMXprt 中使用解析法模板快速建立电机初始设计，获取性能预估（效率、转矩、电感等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "motor_type": {
                        "type": "string",
                        "enum": ["PMSM", "BLDC", "IM", "SRM", "PMDC", "SYN", "SYNRM"],
                        "description": "电机类型：PMSM（永磁同步）、BLDC（无刷直流）、IM（感应）、SRM（开关磁阻）",
                    },
                    "stator_outer_diameter": {"type": "number", "description": "定子外径（mm）"},
                    "stator_inner_diameter": {"type": "number", "description": "定子内径（mm）"},
                    "rotor_outer_diameter": {"type": "number", "description": "转子外径（mm）"},
                    "shaft_diameter": {"type": "number", "description": "轴径（mm）"},
                    "stack_length": {"type": "number", "description": "铁芯轴向长度（mm）"},
                    "num_poles": {"type": "integer", "description": "极数"},
                    "num_slots": {"type": "integer", "description": "定子槽数"},
                    "rated_speed": {"type": "number", "description": "额定转速（rpm）"},
                    "rated_voltage": {"type": "number", "description": "额定线电压（V）"},
                    "rated_power": {"type": "number", "description": "额定功率（W）"},
                    "design_name": {"type": "string", "description": "设计名称"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_rmxprt_analysis",
            "description": "运行 RMXprt 解析法仿真，快速获取效率、转矩、电感等性能预估值。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_to_maxwell",
            "description": "将 RMXprt 初始设计导出为 Maxwell 2D/3D 精确 FEM 仿真模型（自动建立几何和激励）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "RMXprt 求解设置名称，默认 Setup1"},
                    "is_2d": {"type": "boolean", "description": "True 导出 Maxwell 2D（推荐），False 导出 Maxwell 3D"},
                    "maxwell_design_name": {"type": "string", "description": "Maxwell 中的设计名称；留空则自动命名"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # P3 热-结构耦合工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "import_thermal_to_mechanical",
            "description": "将 Icepak 温度场结果导入 Mechanical 作为热载荷，用于计算热应力和热变形（需先运行热仿真）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "icepak_project_path": {"type": "string", "description": "Icepak 项目文件路径（.aedt）；留空则从当前项目推导"},
                    "setup_name": {"type": "string", "description": "Icepak 求解设置名称，默认 SetupThermal"},
                    "analysis_name": {"type": "string", "description": "Mechanical 分析名称，默认 'Static Structural'"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # P3 场量可视化工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_field_plot",
            "description": "在 AEDT 后处理中创建场量彩色云图（B 磁通密度、H 磁场强度、J 电流密度、CoreLoss 铁耗密度等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "quantity": {
                        "type": "string",
                        "enum": ["B", "Bx", "By", "H", "J", "CoreLoss", "OhmicLoss", "Temperature", "StressX", "StressY"],
                        "description": "场量名称；B 最常用（默认）",
                    },
                    "plot_name": {"type": "string", "description": "云图名称；留空则自动命名"},
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "sweep_name": {"type": "string", "description": "扫描步名称，默认 LastAdaptive"},
                    "object_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要绘制云图的几何体列表；None 则在所有对象上绘制",
                    },
                    "plot_on_surface": {"type": "boolean", "description": "True 为表面云图（默认），False 为体积云图（3D）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_field_image",
            "description": "将场量云图导出为 PNG 图像文件（用于报告和文档）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "plot_name": {"type": "string", "description": "云图名称（由 create_field_plot 创建）"},
                    "output_path": {"type": "string", "description": "输出 PNG 文件路径"},
                    "width": {"type": "integer", "description": "图像宽度（像素），默认 1920"},
                    "height": {"type": "integer", "description": "图像高度（像素），默认 1080"},
                    "orientation": {"type": "string", "description": "视角方向：XY/XZ/YZ/ISO；留空为当前视角"},
                },
                "required": ["plot_name", "output_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_field_plots",
            "description": "列出当前设计中所有已创建的场量云图名称和场量类型。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # Motor-CAD 解析法初设计工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_motorcad",
            "description": "连接到 Ansys Motor-CAD 实例，用于快速解析法电机初设计（EM/热/NVH）。在使用所有 motorcad_* 工具之前必须先调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "Motor-CAD RPC 端口；0 表示自动（推荐）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_motorcad_geometry",
            "description": "在 Motor-CAD 中设置电机几何参数（外径、内径、叠长、极槽数等），适用于 PMSM/BLDC/IM。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stator_outer_diam": {"type": "number", "description": "定子外径（mm）"},
                    "stator_inner_diam": {"type": "number", "description": "定子内径（mm）"},
                    "rotor_outer_diam": {"type": "number", "description": "转子外径（mm）"},
                    "shaft_diam": {"type": "number", "description": "转轴直径（mm）"},
                    "stack_length": {"type": "number", "description": "轴向叠片长度（mm）"},
                    "num_poles": {"type": "integer", "description": "极数（偶数）"},
                    "num_slots": {"type": "integer", "description": "定子槽数"},
                    "motor_type": {"type": "string", "description": "电机类型：PMSM / BLDC / IM，默认 PMSM"},
                },
                "required": ["stator_outer_diam", "stator_inner_diam", "rotor_outer_diam",
                             "shaft_diam", "stack_length", "num_poles", "num_slots"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_motorcad_em_analysis",
            "description": "在 Motor-CAD 中运行电磁（Emag）解析仿真，快速获取转矩、效率、反电动势、铁耗铜耗等性能指标。",
            "parameters": {
                "type": "object",
                "properties": {
                    "rated_speed_rpm": {"type": "number", "description": "额定转速（rpm），默认 3000"},
                    "rated_current_A": {"type": "number", "description": "相电流峰值（A），默认 10"},
                    "current_angle_deg": {"type": "number", "description": "电流超前角（度），默认 45"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_motorcad_thermal_analysis",
            "description": "在 Motor-CAD 热网络模块中运行稳态热分析，评估绕组、铁芯、磁体各部件温升。",
            "parameters": {
                "type": "object",
                "properties": {
                    "cooling_type": {"type": "string", "description": "冷却方式：TEFC（自冷）/ WJ（水套）/ OilSpray（喷油），默认 TEFC"},
                    "ambient_temp_C": {"type": "number", "description": "环境温度（°C），默认 25"},
                    "coolant_flow_rate": {"type": "number", "description": "冷却液流量（L/min），水套冷却时有效"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_motorcad_nvh_analysis",
            "description": "在 Motor-CAD 中运行 NVH 分析，预测电磁径向力、齿槽转矩峰值和主要力波次数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "speed_rpm": {"type": "number", "description": "分析转速（rpm），默认 3000"},
                    "freq_max_Hz": {"type": "number", "description": "最高分析频率（Hz），默认 5000"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_motorcad_performance_map",
            "description": "在 Motor-CAD Lab 模块中计算全工况效率 MAP，返回转速-转矩-效率三维数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "speed_points": {"type": "integer", "description": "转速扫描点数，默认 10"},
                    "torque_points": {"type": "integer", "description": "转矩扫描点数，默认 10"},
                    "max_speed_rpm": {"type": "number", "description": "最高转速（rpm），默认 6000"},
                    "max_torque_Nm": {"type": "number", "description": "最大转矩（Nm），默认 50"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_motorcad_to_maxwell",
            "description": "将 Motor-CAD 当前设计导出为 Maxwell 2D/3D FEM 模型，实现解析初设计 → 精确仿真工作流。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_dir": {"type": "string", "description": "导出目录（空则用 Motor-CAD 默认目录）"},
                    "is_2d": {"type": "boolean", "description": "True 导出 Maxwell 2D（速度快，推荐，默认），False 导出 Maxwell 3D（含端部效应，耗时更长）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disconnect_motorcad",
            "description": "断开 Motor-CAD 连接并释放许可证。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # PyMAPDL 结构强度 / NVH 工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_mapdl",
            "description": "连接到 MAPDL 求解器（本地启动或远程连接），用于电机结构强度、热应力和 NVH 谐响应分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "gRPC 端口号，默认 50052"},
                    "server": {"type": "string", "description": "MAPDL 服务器 IP 地址，默认 '127.0.0.1'；launch_local=True 时忽略此参数"},
                    "launch_local": {"type": "boolean", "description": "True 本地启动，False 连接远程，默认 True"},
                    "nproc": {"type": "integer", "description": "并行核心数（本地启动有效），默认 4"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_rotor_stress_analysis",
            "description": "在 MAPDL 中建立轴对称转子模型，计算高转速离心应力，用于校核转子铁芯和永磁体结构安全性。",
            "parameters": {
                "type": "object",
                "properties": {
                    "rotor_outer_radius_mm": {"type": "number", "description": "转子外径（mm）"},
                    "rotor_inner_radius_mm": {"type": "number", "description": "转子内径/轴径（mm）"},
                    "stack_length_mm": {"type": "number", "description": "叠片长度（mm）"},
                    "speed_rpm": {"type": "number", "description": "转速（rpm）"},
                    "material": {"type": "string", "description": "材料名称（注释用），默认 Steel"},
                    "density_kg_m3": {"type": "number", "description": "密度（kg/m³），默认 7850"},
                    "youngs_modulus_GPa": {"type": "number", "description": "杨氏模量（GPa），默认 200"},
                    "poisson_ratio": {"type": "number", "description": "泊松比，默认 0.3"},
                },
                "required": ["rotor_outer_radius_mm", "rotor_inner_radius_mm", "stack_length_mm", "speed_rpm"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_thermal_stress_analysis",
            "description": "基于近似均匀温度载荷执行 MAPDL 热应力分析；若 CSV 含非均匀温度分布则拒绝伪装成已完成映射。",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature_csv_path": {"type": "string", "description": "温度分布 CSV 文件路径（含坐标和温度列）"},
                    "material": {"type": "string", "description": "材料名称，默认 Steel"},
                    "thermal_expansion_coeff": {"type": "number", "description": "热膨胀系数（/°C），钢约 12e-6"},
                    "youngs_modulus_GPa": {"type": "number", "description": "杨氏模量（GPa），默认 200"},
                    "ref_temp_C": {"type": "number", "description": "参考温度（°C），默认 20"},
                },
                "required": ["temperature_csv_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_nvh_harmonic_analysis",
            "description": "在 MAPDL 中运行谐响应 NVH 分析，评估电机定子在电磁激励力下的振动响应，识别共振风险。",
            "parameters": {
                "type": "object",
                "properties": {
                    "freq_start_Hz": {"type": "number", "description": "起始频率（Hz），默认 0"},
                    "freq_end_Hz": {"type": "number", "description": "终止频率（Hz），默认 5000"},
                    "freq_steps": {"type": "integer", "description": "频率步数，默认 200"},
                    "damping_ratio": {"type": "number", "description": "阻尼比，钢结构约 0.01~0.03，默认 0.02"},
                    "force_amplitude_N": {"type": "number", "description": "电磁径向力幅值（N），默认 100"},
                    "force_frequency_Hz": {"type": "number", "description": "主激励频率（Hz），通常为电气次数×电频率"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mapdl_structural_results",
            "description": "从最近一次 MAPDL 分析中提取结构结果（应力/变形/固有频率）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_type": {
                        "type": "string",
                        "enum": ["stress", "deformation", "frequency"],
                        "description": "结果类型：stress（von Mises 应力）/ deformation（合位移）/ frequency（固有频率），默认 stress",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disconnect_mapdl",
            "description": "退出 MAPDL 进程并释放资源。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # MapdlPool 子模型工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_mapdl_pool",
            "description": "启动 MapdlPool，创建多个并行 MAPDL 实例，适用于子模型（submodeling）、参数化批量仿真等多实例工作流。",
            "parameters": {
                "type": "object",
                "properties": {
                    "n_instances": {"type": "integer", "description": "Pool 中的 MAPDL 实例数，默认 2（全局+局部模型各一个）"},
                    "port_start": {"type": "integer", "description": "第一个实例的起始端口号，默认 21000"},
                    "nproc": {"type": "integer", "description": "每个实例的并行核心数，默认 2"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_mapdl_pool_model",
            "description": "为 MapdlPool 中指定索引的实例加载 CDB 几何/网格文件，并可选设置该实例的工作目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "instance_index": {"type": "integer", "description": "Pool 实例索引（0 = 全局模型，1 = 局部模型）"},
                    "cdb_file_path": {"type": "string", "description": "CDB 文件路径（含完整路径）"},
                    "working_dir": {"type": "string", "description": "实例工作目录；None 则不修改"},
                },
                "required": ["instance_index", "cdb_file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_mapdl_pool_submodel",
            "description": (
                "使用 MapdlPool 执行连续子模型仿真：对每个时间步，先求解全局模型，通过 DPF 插值获取局部模型边界位移，"
                "再施加到局部模型并求解。"
                "前提：已调用 connect_mapdl_pool + load_mapdl_pool_model + create_dpf_interpolator。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "n_timesteps": {"type": "integer", "description": "时间步总数，默认 10"},
                    "global_instance_index": {"type": "integer", "description": "Pool 中全局模型实例的索引，默认 0"},
                    "local_instance_index": {"type": "integer", "description": "Pool 中局部模型实例的索引，默认 1"},
                    "result_output_dir": {"type": "string", "description": "结果文件输出目录，默认 './outputs/mapdl-dpf'"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disconnect_mapdl_pool",
            "description": "退出 MapdlPool 中所有 MAPDL 实例并释放资源。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # PyDPF-Post 结果后处理工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "load_dpf_result",
            "description": "加载 MAPDL/Mechanical 仿真结果文件（.rst），初始化 DPF 后处理会话，返回网格信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_file_path": {"type": "string", "description": "结果文件绝对路径（.rst 格式）"},
                },
                "required": ["result_file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dpf_stress",
            "description": "从 DPF 结果中提取应力场（von Mises 或单轴分量），返回最大/最小/平均值（MPa）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_set": {"type": "integer", "description": "时间步编号，从 1 开始，默认 1"},
                    "component": {"type": "string", "description": "EQV（等效）/ X / Y / Z / XY / YZ / XZ，默认 EQV"},
                    "location": {"type": "string", "description": "Nodal（节点）或 Elemental（单元），默认 Nodal"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dpf_temperature",
            "description": "从 DPF 结果中提取温度场分布，返回最大/最小/平均温度（°C）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_set": {"type": "integer", "description": "时间步编号，从 1 开始，默认 1"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dpf_displacement",
            "description": "从 DPF 结果中提取位移/变形场，返回最大/最小/平均变形量（mm）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_set": {"type": "integer", "description": "时间步编号，默认 1"},
                    "component": {"type": "string", "description": "NORM（合位移）/ X / Y / Z，默认 NORM"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dpf_field_statistics",
            "description": "获取任意场量（应力/温度/位移/弹性应变）在指定时间步的统计汇总（最大/最小/平均）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "field_name": {"type": "string", "description": "场量名称：stress / temperature / displacement / elastic_strain"},
                    "result_set": {"type": "integer", "description": "时间步编号，默认 1"},
                },
                "required": ["field_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_dpf_results_to_csv",
            "description": "将 DPF 场量数据（应力/温度/位移）导出为 CSV 文件，便于 Excel 或 Python 进一步处理。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "输出 CSV 文件路径（含文件名）"},
                    "field_name": {"type": "string", "description": "场量名称：stress / temperature / displacement，默认 stress"},
                    "result_set": {"type": "integer", "description": "时间步编号，默认 1"},
                },
                "required": ["output_path"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # DPF-Core 底层工具定义（子模型插值、热分析 .rth）
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_dpf_server",
            "description": "连接或启动 DPF 服务器（dpf.core）。local=True 在本机启动本地 DPF Server；local=False 连接远程 DPF Server（需提供 port）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "DPF Server 端口号；local=False 时必填"},
                    "local": {"type": "boolean", "description": "True 启动本地服务（默认），False 连接远程服务"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_dpf_core_model",
            "description": "使用 DPF-Core 底层 API 加载仿真结果文件（.rst 或 .rth），支持多域（多核并行 MAPDL 结果）和单文件两种模式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_file_path": {"type": "string", "description": "主结果文件路径（.rst 或 .rth）"},
                    "domain_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "多核并行结果文件列表（如 file0.rst, file1.rst, ...）；None 则以单文件模式加载",
                    },
                },
                "required": ["result_file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dpf_core_temperature",
            "description": "通过 DPF-Core 提取热分析温度场（支持 .rth 文件），适用于 Mechanical 稳态/瞬态热分析结果后处理。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_file_path": {"type": "string", "description": ".rth 文件路径；None 则使用已加载的全局 DPF Model"},
                    "time_step": {"type": "string", "description": "'last'（最终时间步，默认）或整数字符串（如 '3'）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_result_files",
            "description": "在指定目录中递归搜索指定扩展名的仿真结果文件（.rst / .rth 等），适用于 Mechanical 项目目录下自动定位结果文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "搜索根目录"},
                    "extension": {"type": "string", "description": "文件扩展名，如 '.rth'（热分析）或 '.rst'（结构分析），默认 '.rth'"},
                },
                "required": ["directory"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_dpf_interpolator",
            "description": (
                "创建 DPF 插值算子（on_coordinates），用于子模型工作流：从全局模型结果插值计算局部模型边界节点的位移。"
                "完成后可调用 interpolate_boundary_displacements 执行插值。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "global_result_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "全局模型结果文件路径列表（支持多核并行）",
                    },
                    "local_boundary_node_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "局部模型边界节点 ID 列表",
                    },
                    "local_boundary_coordinates": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                        "description": "与节点 ID 对应的坐标列表，每项 [x, y, z]（单位：m）",
                    },
                },
                "required": ["global_result_files", "local_boundary_node_ids", "local_boundary_coordinates"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "interpolate_boundary_displacements",
            "description": (
                "使用已创建的 DPF 插值算子，从全局模型结果中插值计算局部模型边界节点在指定时间步的位移。"
                "必须先调用 create_dpf_interpolator 初始化算子。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "timestep": {"type": "integer", "description": "全局模型结果时间步编号（从 1 开始），默认 1"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # 自动化报告生成工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_report_session",
            "description": "初始化电机仿真分析报告会话，后续可向报告中添加文本、表格、图片等内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "报告标题，默认'电机仿真分析报告'"},
                    "output_dir": {"type": "string", "description": "报告输出目录；为空则使用当前目录"},
                    "use_adr": {"type": "boolean", "description": "True 尝试使用 Ansys Dynamic Reporting，False 使用内置 HTML 模板"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_report_section",
            "description": "向报告中添加一个文本节（标题+正文），用于描述仿真目的、方法或结论。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "小节标题"},
                    "content": {"type": "string", "description": "正文内容"},
                    "level": {"type": "integer", "description": "标题级别：2=H2，3=H3，默认 2"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_table_to_report",
            "description": "向报告中插入数据表格，data 为字典列表（每个字典一行，key 为列名）。适合展示仿真结果汇总。",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "表格数据，格式为 [{列名: 值, ...}, ...]",
                    },
                    "table_title": {"type": "string", "description": "表格标题，默认'数据表格'"},
                },
                "required": ["data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_image_to_report",
            "description": "向报告中插入图片（仿真云图、效率 MAP 截图等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "图片文件绝对路径（PNG/JPG/SVG）"},
                    "caption": {"type": "string", "description": "图片说明文字"},
                    "width_pct": {"type": "integer", "description": "页面宽度百分比（1~100），默认 80"},
                },
                "required": ["image_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_report",
            "description": "将当前报告导出为 HTML、PDF 或 Word (docx) 文件，汇总所有仿真结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["html", "pdf", "docx"], "description": "输出格式：html（内置模板，始终可用）、pdf（需 ADR 支持）或 docx（Word 文档，需 python-docx），默认 html"},
                    "filename": {"type": "string", "description": "输出文件名（不含扩展名），默认 motor_analysis_report"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # 结果分析工具（result_tools）
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "get_iron_loss_breakdown",
            "description": "从 Maxwell 仿真结果中提取铁损分项（磁滞损耗、涡流损耗、超量损耗），并可按转子/定子分类汇总。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解方案名称，默认 'Setup1'"},
                    "time_range": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "时间范围 [t_start, t_end]（秒），默认使用全部时间步",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cogging_torque_harmonics",
            "description": "对齿槽转矩曲线进行 FFT 分析，返回主要谐波阶次及幅值，辅助评估齿槽效应。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解方案名称，默认 'Setup1'"},
                    "n_harmonics": {"type": "integer", "description": "返回的谐波阶次数量，默认 10"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_winding_factor",
            "description": "计算绕组系数（基波分布系数 × 节距系数），用于评估绕组设计优劣。",
            "parameters": {
                "type": "object",
                "properties": {
                    "poles": {"type": "integer", "description": "极对数"},
                    "slots": {"type": "integer", "description": "槽数"},
                    "coil_pitch": {"type": "integer", "description": "线圈节距（槽数），默认整距"},
                },
                "required": ["poles", "slots"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # 参数化扫描 / DOE / RSM 工具（sweep_tools）
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_lhs_doe",
            "description": "使用拉丁超立方采样（LHS）生成设计试验（DOE）方案，输出归一化或反归一化的采样点。",
            "parameters": {
                "type": "object",
                "properties": {
                    "param_bounds": {
                        "type": "object",
                        "description": "参数边界字典，格式 {参数名: [下界, 上界]}",
                    },
                    "n_samples": {"type": "integer", "description": "采样点数量，默认 20"},
                    "seed": {"type": "integer", "description": "随机种子，默认 42"},
                },
                "required": ["param_bounds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_rsm",
            "description": "基于已有仿真数据拟合响应面模型（RSM），支持单参数（多项式）和双参数（二次曲面）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "param_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "设计变量名称列表（1 或 2 个元素）",
                    },
                    "response_name": {"type": "string", "description": "响应变量名称（如 'torque'）"},
                    "data_points": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "数据点列表，每个元素包含参数值和响应值，格式 [{param1: v, ..., response: v}, ...]",
                    },
                    "degree": {"type": "integer", "description": "多项式阶次（仅单参数时有效），默认 2"},
                },
                "required": ["param_names", "response_name", "data_points"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # 设计结果数据库工具（database_tools）
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "save_design_result",
            "description": "将一次仿真设计的关键参数与性能指标保存到本地设计数据库，便于后续比较和检索。",
            "parameters": {
                "type": "object",
                "properties": {
                    "design_name": {"type": "string", "description": "设计方案名称"},
                    "parameters": {"type": "object", "description": "设计参数字典，如 {槽宽: 3.5, 气隙: 0.8}"},
                    "results": {"type": "object", "description": "仿真结果字典，如 {转矩: 15.2, 效率: 0.94}"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "可选标签列表，用于分类检索",
                    },
                    "notes": {"type": "string", "description": "备注信息"},
                },
                "required": ["design_name", "parameters", "results"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_design_results",
            "description": "列出设计数据库中所有已保存的设计方案（仅摘要信息）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "tag_filter": {"type": "string", "description": "按标签过滤，留空则返回全部"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_design_result",
            "description": "从设计数据库中检索指定设计方案的完整详情。",
            "parameters": {
                "type": "object",
                "properties": {
                    "design_id": {"type": "string", "description": "设计方案 ID（由 save_design_result 返回）"},
                },
                "required": ["design_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_design_results",
            "description": "对比多个设计方案的参数与性能指标，生成对比表格。",
            "parameters": {
                "type": "object",
                "properties": {
                    "design_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要对比的设计方案 ID 列表（至少 2 个）",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要对比的指标字段名，留空则对比所有字段",
                    },
                },
                "required": ["design_ids"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # EV 整车电驱系统联仿工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_ev_circuit",
            "description": "连接到 AEDT Circuit 实例用于 EV 整车电驱系统联合仿真。",
            "parameters": {
                "type": "object",
                "properties": {
                    "version": {"type": "string", "description": "AEDT 版本号，如 '2024.1'"},
                    "non_graphical": {"type": "boolean", "description": "是否无界面批处理模式"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_battery_model",
            "description": "在 Circuit 中创建电池等效电路模型（Rint/Thevenin），支持 SOC-OCV 查表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "battery_type": {"type": "string", "enum": ["lithium_ion", "lifepo4", "nmc"], "description": "电池类型"},
                    "capacity_Ah": {"type": "number", "description": "电池容量（Ah）"},
                    "nominal_voltage_V": {"type": "number", "description": "标称电压（V）"},
                    "internal_resistance_mOhm": {"type": "number", "description": "内阻（mΩ）"},
                    "soc_initial": {"type": "number", "description": "初始 SOC（0~1）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_controller_model",
            "description": "在 Circuit 中创建电机控制器拓扑（逆变器+FOC/DTC 控制策略+SVPWM/SPWM 调制）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dc_voltage_V": {"type": "number", "description": "直流母线电压（V）"},
                    "switching_freq_Hz": {"type": "number", "description": "开关频率（Hz）"},
                    "dead_time_us": {"type": "number", "description": "死区时间（μs）"},
                    "control_strategy": {"type": "string", "enum": ["FOC", "DTC"], "description": "控制策略"},
                    "pwm_method": {"type": "string", "enum": ["SVPWM", "SPWM"], "description": "PWM 调制方式"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "link_motor_to_powertrain",
            "description": "将 Maxwell 电机设计链接到 EV 电驱系统（电池+控制器+电机联仿）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "maxwell_design_name": {"type": "string", "description": "Maxwell 设计名称"},
                },
                "required": ["maxwell_design_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_powertrain_simulation",
            "description": "运行电池→控制器→电机电驱系统联合瞬态仿真，支持自定义驱动工况。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stop_time_ms": {"type": "number", "description": "仿真总时间（ms）"},
                    "time_step_us": {"type": "number", "description": "时间步（μs）"},
                    "driving_cycle": {"type": "string", "enum": ["steady_state", "WLTP", "NEDC", "custom"], "description": "驱动工况"},
                    "speed_profile_rpm": {"type": "array", "items": {"type": "number"}, "description": "自定义转速曲线（rpm）"},
                    "torque_demand_Nm": {"type": "array", "items": {"type": "number"}, "description": "自定义转矩需求曲线（Nm）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_powertrain_results",
            "description": "提取电驱系统联仿结果：电池电流/电压、控制器信号、电机转矩/转速等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "signals": {"type": "array", "items": {"type": "string"}, "description": "信号名列表；None 则提取默认信号集"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_powertrain_config",
            "description": "返回当前 EV 电驱系统的完整配置（电池+控制器+电机参数）。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # NVH 噪声振动分析工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_nvh_mechanical",
            "description": "连接 Ansys Mechanical 实例用于 NVH 分析。",
            "parameters": {"type": "object", "properties": {"version": {"type": "string", "description": "Ansys 版本号，如 '242'"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "connect_nvh_mapdl",
            "description": "连接 MAPDL 求解器用于 NVH 结构分析。",
            "parameters": {"type": "object", "properties": {"version": {"type": "string", "description": "Ansys 版本号"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_maxwell_electromagnetic_forces",
            "description": "从 Maxwell 仿真提取电磁力密度分布（径向/切向），作为 NVH 链路的输入激励源。",
            "parameters": {
                "type": "object",
                "properties": {
                    "maxwell_project_path": {"type": "string", "description": "Maxwell 项目路径（.aedt）"},
                    "design_name": {"type": "string", "description": "Maxwell 设计名称"},
                    "setup_name": {"type": "string", "description": "求解设置名称"},
                    "force_type": {"type": "string", "enum": ["radial", "tangential", "both"], "description": "力类型"},
                    "export_path": {"type": "string", "description": "导出文件路径"},
                },
                "required": ["maxwell_project_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_forces_to_structural",
            "description": "将 Maxwell 电磁力密度数据导入 Mechanical/MAPDL 结构模型，作为谐响应分析载荷。",
            "parameters": {
                "type": "object",
                "properties": {
                    "force_data_path": {"type": "string", "description": "电磁力数据文件路径"},
                    "structural_project_path": {"type": "string", "description": "结构模型项目路径"},
                    "mapping_method": {"type": "string", "enum": ["node_based", "element_based"], "description": "映射方式"},
                },
                "required": ["force_data_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_nvh_modal_analysis",
            "description": "运行 NVH 模态分析，提取与电磁力频率匹配的固有频率和振型（建议 >= 20 阶）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "num_modes": {"type": "integer", "description": "模态阶数"},
                    "freq_range_hz": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "description": "[f_min, f_max] 频率范围（Hz）"},
                    "analysis_name": {"type": "string", "description": "Mechanical 中的分析名称"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_nvh_harmonic_response",
            "description": "运行 NVH 谐响应分析，计算电磁力激励下的振动响应（建议 >= 200 步）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "freq_range_hz": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "description": "频率扫描范围（Hz）"},
                    "num_steps": {"type": "integer", "description": "频率步数"},
                    "damping_ratio": {"type": "number", "description": "阻尼比"},
                    "excitation_source": {"type": "string", "description": "激励源描述"},
                    "analysis_name": {"type": "string", "description": "Mechanical 中的分析名称"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_vibration_noise_results",
            "description": "提取 NVH 分析结果：振动加速度、表面速度、估算声压级（SPL）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_name": {"type": "string", "description": "分析名称"},
                    "surface_names": {"type": "array", "items": {"type": "string"}, "description": "表面名称列表"},
                    "freq_of_interest_Hz": {"type": "array", "items": {"type": "number"}, "description": "关注的频率点"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_nvh_full_chain",
            "description": "一键运行电磁力→结构振动→噪声评估的完整 NVH 链路（5 步自动化）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "maxwell_project_path": {"type": "string", "description": "Maxwell 项目路径"},
                    "design_name": {"type": "string", "description": "Maxwell 设计名称"},
                    "setup_name": {"type": "string", "description": "求解设置名称"},
                    "num_modes": {"type": "integer", "description": "模态阶数"},
                    "freq_range_hz": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2, "description": "频率范围（Hz）"},
                    "num_harmonic_steps": {"type": "integer", "description": "谐响应步数"},
                    "damping_ratio": {"type": "number", "description": "阻尼比"},
                },
                "required": ["maxwell_project_path"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # 成本估算工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "estimate_motor_cost",
            "description": "根据电机几何参数和材料类型估算制造成本（铁芯+绕组+磁钢+结构件+绝缘+加工费），支持批量折扣和区域差异。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stator_outer_diam_mm": {"type": "number", "description": "定子外径（mm）"},
                    "stator_inner_diam_mm": {"type": "number", "description": "定子内径（mm）"},
                    "rotor_outer_diam_mm": {"type": "number", "description": "转子外径（mm）"},
                    "shaft_diam_mm": {"type": "number", "description": "转轴直径（mm）"},
                    "stack_length_mm": {"type": "number", "description": "叠片长度（mm）"},
                    "num_slots": {"type": "integer", "description": "槽数"},
                    "num_poles": {"type": "integer", "description": "极数"},
                    "magnet_type": {"type": "string", "enum": ["ndfeb", "ferrite"], "description": "磁钢类型"},
                    "winding_fill_factor": {"type": "number", "description": "槽满率（0~1）"},
                    "insulation_class": {"type": "string", "enum": ["B", "F", "H"], "description": "绝缘等级"},
                    "production_volume": {"type": "integer", "description": "生产批量（台）"},
                    "material_prices": {"type": "object", "description": "自定义材料单价覆盖（元/kg）"},
                    "manufacturing_region": {"type": "string", "enum": ["china", "eu", "us"], "description": "制造区域"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_default_material_prices",
            "description": "返回当前默认的材料单价和密度信息（硅钢/铜线/磁钢/铝/轴承钢等）。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_magnet_cost",
            "description": "对比 NdFeB 和铁氧体两种磁钢方案的成本差异，辅助选型决策。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stator_outer_diam_mm": {"type": "number", "description": "定子外径（mm）"},
                    "stator_inner_diam_mm": {"type": "number", "description": "定子内径（mm）"},
                    "rotor_outer_diam_mm": {"type": "number", "description": "转子外径（mm）"},
                    "shaft_diam_mm": {"type": "number", "description": "转轴直径（mm）"},
                    "stack_length_mm": {"type": "number", "description": "叠片长度（mm）"},
                    "production_volume": {"type": "integer", "description": "生产批量"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # LS-DYNA 整车碰撞安全仿真工具定义（PyDyna）
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_crash_deck",
            "description": "创建新的 LS-DYNA 碰撞仿真 Deck 容器，设置仿真标题和单位制。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "仿真标题"},
                    "units": {"type": "string", "enum": ["mm_ton_s", "m_kg_s", "mm_kg_s"], "description": "单位制"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_vehicle_model",
            "description": "加载已有的整车碰撞 LS-DYNA Keyword 文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_path": {"type": "string", "description": "模型文件路径"},
                    "expand_includes": {"type": "boolean", "description": "是否展开 Include 引用"},
                },
                "required": ["model_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_crash_material",
            "description": "向碰撞 Deck 添加材料模型（弹性、弹塑性、刚性等）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mid": {"type": "integer", "description": "材料 ID"},
                    "material_type": {"type": "string", "enum": ["elastic", "piecewise_linear_plasticity", "rigid", "johnson_cook"], "description": "材料类型"},
                    "density": {"type": "number", "description": "密度"},
                    "youngs_modulus": {"type": "number", "description": "杨氏模量（MPa）"},
                    "poisson_ratio": {"type": "number", "description": "泊松比"},
                },
                "required": ["mid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_crash_section",
            "description": "向碰撞 Deck 添加截面属性。",
            "parameters": {
                "type": "object",
                "properties": {
                    "secid": {"type": "integer", "description": "截面 ID"},
                    "section_type": {"type": "string", "enum": ["shell", "solid", "beam"], "description": "截面类型"},
                },
                "required": ["secid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_crash_contact",
            "description": "向碰撞 Deck 添加接触定义。",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_type": {"type": "string", "enum": ["automatic_single_surface", "automatic_surface_to_surface", "automatic_nodes_to_surface", "eroding_single_surface", "tied_surface_to_surface"], "description": "接触类型"},
                    "fs": {"type": "number", "description": "静摩擦系数"},
                    "fd": {"type": "number", "description": "动摩擦系数"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_rigid_wall",
            "description": "向碰撞 Deck 添加刚性壁障。",
            "parameters": {
                "type": "object",
                "properties": {
                    "wall_id": {"type": "integer", "description": "壁障 ID"},
                    "wall_type": {"type": "string", "enum": ["planar", "moving"], "description": "壁障类型"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_frontal_crash",
            "description": "设置正面碰撞仿真工况控制卡片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crash_type": {"type": "string", "enum": ["full_frontal", "offset", "small_overlap"], "description": "碰撞类型"},
                    "impact_speed_kmh": {"type": "number", "description": "碰撞速度（km/h）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_side_crash",
            "description": "设置侧面碰撞仿真工况控制卡片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "crash_type": {"type": "string", "enum": ["mdb", "pole"], "description": "碰撞类型"},
                    "impact_speed_kmh": {"type": "number", "description": "碰撞速度（km/h）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_rear_crash",
            "description": "设置后部碰撞仿真工况控制卡片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "impact_speed_kmh": {"type": "number", "description": "碰撞速度（km/h）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_pedestrian_protection",
            "description": "设置行人保护仿真工况控制卡片。",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_region": {"type": "string", "enum": ["headform", "legform", "upper_leg"], "description": "测试区域"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_initial_velocity",
            "description": "向碰撞 Deck 添加初始速度定义。",
            "parameters": {
                "type": "object",
                "properties": {
                    "vx": {"type": "number", "description": "X 方向速度（mm/s）"},
                    "vy": {"type": "number", "description": "Y 方向速度（mm/s）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_crash_model",
            "description": "将碰撞 Deck 导出为 LS-DYNA Keyword 文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "输出文件路径"},
                },
                "required": ["output_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_crash_simulation",
            "description": "调用 LS-DYNA 求解器运行碰撞仿真。",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_file": {"type": "string", "description": "输入 .k 文件路径"},
                    "working_dir": {"type": "string", "description": "工作目录"},
                },
                "required": ["input_file"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crash_results",
            "description": "提取碰撞仿真结果（能量、加速度、变形）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_type": {"type": "string", "enum": ["energy", "acceleration", "deformation", "force"], "description": "结果类型"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dummy_injury_criteria",
            "description": "提取碰撞仿真中假人损伤指标。",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_type": {"type": "string", "enum": ["frontal", "side", "rear", "pedestrian"], "description": "碰撞类型"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # 整车 CFD 仿真工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_vehicle_cfd",
            "description": "启动 Fluent 会话用于整车 CFD 仿真。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["solver", "meshing"], "description": "模式"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_vehicle_cfd_mesh",
            "description": "加载整车 CFD 计算域网格。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mesh_path": {"type": "string", "description": "网格文件路径"},
                },
                "required": ["mesh_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_external_aero",
            "description": "设置整车空气动力学分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "wind_speed_m_s": {"type": "number", "description": "来流风速（m/s）"},
                    "reference_area_m2": {"type": "number", "description": "参考面积（m²）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_battery_thermal_cfd",
            "description": "设置电池包液冷 CFD 热仿真。",
            "parameters": {
                "type": "object",
                "properties": {
                    "inlet_temp_C": {"type": "number", "description": "入口温度（°C）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_vehicle_cfd_simulation",
            "description": "运行整车 CFD 仿真。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_aero_coefficients",
            "description": "提取整车空气动力学系数。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # 疲劳耐久仿真工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_fatigue_solver",
            "description": "连接到疲劳分析求解器。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "define_sn_curve",
            "description": "定义 S-N 曲线用于高周疲劳分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_id": {"type": "integer", "description": "材料 ID"},
                },
                "required": ["material_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "define_load_spectrum",
            "description": "定义疲劳载荷谱。",
            "parameters": {
                "type": "object",
                "properties": {
                    "spectrum_type": {"type": "string", "enum": ["constant_amplitude", "variable_amplitude", "block"], "description": "载荷谱类型"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_fatigue_analysis",
            "description": "运行疲劳寿命分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_method": {"type": "string", "enum": ["stress_life", "strain_life"], "description": "分析方法"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fatigue_results",
            "description": "提取疲劳分析结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_type": {"type": "string", "enum": ["life", "damage", "safety_factor"], "description": "结果类型"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # 整车动力学 VD 仿真工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_vd_solver",
            "description": "连接到整车动力学仿真求解器。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "define_vehicle_params",
            "description": "定义整车动力学参数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "vehicle_mass_kg": {"type": "number", "description": "整车质量（kg）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_steady_state_cornering",
            "description": "设置稳态回转分析。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_vd_simulation",
            "description": "运行整车动力学仿真。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vd_results",
            "description": "提取整车动力学仿真结果。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # 整车结构强度仿真工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_structural_solver",
            "description": "连接到结构分析求解器。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_structural_analysis",
            "description": "运行整车结构强度分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {"type": "string", "enum": ["static", "quasi_static", "buckling"], "description": "分析类型"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_structural_results",
            "description": "提取结构分析结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "result_type": {"type": "string", "enum": ["stress", "strain", "displacement"], "description": "结果类型"},
                },
            },
        },
    },
    # -----------------------------------------------------------------------
    # 高级网格划分工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "launch_meshing_session",
            "description": "启动网格划分会话。",
            "parameters": {
                "type": "object",
                "properties": {
                    "mesher_type": {"type": "string", "enum": ["fluent_meshing", "ansys_meshing"], "description": "网格器类型"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_tetrahedral_mesh",
            "description": "生成四面体网格。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_hex_mesh",
            "description": "生成六面体网格。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_mesh_quality",
            "description": "检查网格质量。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # 整车 NVH 仿真工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "connect_vehicle_nvh_solver",
            "description": "连接到整车 NVH 仿真求解器。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_vehicle_modal_analysis",
            "description": "设置整车模态分析。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_vehicle_nvh_simulation",
            "description": "运行整车 NVH 仿真。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vehicle_nvh_results",
            "description": "提取整车 NVH 仿真结果。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # -----------------------------------------------------------------------
    # 试验数据管理工具定义
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "create_test_project",
            "description": "创建试验数据管理项目。",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "项目名称"},
                },
                "required": ["project_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_test_data",
            "description": "导入试验数据文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "数据文件路径"},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "correlate_cae_test",
            "description": "CAE 仿真结果与试验数据相关性分析。",
            "parameters": {
                "type": "object",
                "properties": {
                    "cae_result_path": {"type": "string", "description": "CAE 结果文件路径"},
                    "test_data_path": {"type": "string", "description": "试验数据文件路径"},
                },
                "required": ["cae_result_path", "test_data_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_test_report",
            "description": "导出试验数据报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "输出路径"},
                },
                "required": ["output_path"],
            },
        },
    },
    # -----------------------------------------------------------------------
    # 智能诊断与异常检测工具
    # -----------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "diagnose_error",
            "description": "根据错误消息自动诊断问题并提供解决方案。支持 CFD、结构、热分析、电磁等仿真类型。",
            "parameters": {
                "type": "object",
                "properties": {
                    "error_message": {"type": "string", "description": "错误消息"},
                    "context": {"type": "string", "description": "额外上下文信息（如仿真类型、操作步骤）"},
                    "tool_name": {"type": "string", "description": "出错的工具名称"},
                },
                "required": ["error_message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_simulation_setup",
            "description": "验证仿真设置的合理性，检查参数是否在合理范围内。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_type": {"type": "string", "description": "仿真类型（cfd/structural/thermal/emag）"},
                    "parameters": {"type": "object", "description": "仿真参数字典"},
                },
                "required": ["setup_type", "parameters"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_sensitivity",
            "description": "分析设计参数对仿真结果的敏感性，支持相关系数和龙卷风图方法。",
            "parameters": {
                "type": "object",
                "properties": {
                    "parameters": {"type": "object", "description": "设计参数及其取值列表 {param_name: [values]}"},
                    "results": {"type": "object", "description": "结果参数及其取值列表 {result_name: [values]}"},
                    "method": {"type": "string", "description": "分析方法：correlation 或 tornado"},
                },
                "required": ["parameters", "results"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_anomalies",
            "description": "检测仿真结果中的异常值，支持范围检查和统计检查两种方法。",
            "parameters": {
                "type": "object",
                "properties": {
                    "results": {"type": "object", "description": "结果数据 {result_name: [values]}"},
                    "expected_ranges": {"type": "object", "description": "期望范围 {result_name: {min, max}}"},
                    "method": {"type": "string", "description": "检测方法：range 或 statistical"},
                },
                "required": ["results"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_diagnostic_error_history",
            "description": "获取智能诊断工具的错误历史记录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "返回记录数量限制，默认 10"},
                    "error_type": {"type": "string", "description": "错误类型过滤（可选）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ansi_error_history",
            "description": "获取 Ansys 软件的错误历史记录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "返回记录数量限制，默认 10"},
                    "ansys_tool": {"type": "string", "description": "过滤特定 Ansys 工具（aedt/fluent/mapdl/icepak）"},
                    "error_type": {"type": "string", "description": "过滤特定错误类型"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clear_ansi_error_history",
            "description": "清空 Ansys 错误历史记录。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_ansi_error",
            "description": "诊断 Ansys 软件错误并提供修复建议。自动匹配 AEDT/Fluent/MAPDL/Icepak 的错误模式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "error_message": {"type": "string", "description": "错误消息"},
                    "ansys_tool": {"type": "string", "description": "Ansys 工具类型（aedt/fluent/mapdl/icepak）"},
                    "context": {"type": "string", "description": "额外上下文信息"},
                },
                "required": ["error_message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ansi_error_statistics",
            "description": "获取 Ansys 错误统计信息，按工具和错误类型分类统计。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

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
    "add_crash_section", "add_crash_contact", "add_rigid_wall",
    "setup_frontal_crash", "setup_side_crash", "setup_rear_crash",
    "setup_pedestrian_protection", "add_initial_velocity", "add_gravity_load",
    "list_deck_keywords", "export_crash_model", "run_crash_simulation",
    "get_crash_results", "get_dummy_injury_criteria", "disconnect_crash_solver",
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
