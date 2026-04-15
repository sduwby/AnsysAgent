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
    # PyMAPDL 结构强度 / NVH 工具
    "connect_mapdl": mapdl_tools.connect_mapdl,
    "run_rotor_stress_analysis": mapdl_tools.run_rotor_stress_analysis,
    "run_thermal_stress_analysis": mapdl_tools.run_thermal_stress_analysis,
    "run_nvh_harmonic_analysis": mapdl_tools.run_nvh_harmonic_analysis,
    "get_mapdl_structural_results": mapdl_tools.get_mapdl_structural_results,
    "disconnect_mapdl": mapdl_tools.disconnect_mapdl,
    # PyDPF-Post 结果后处理工具
    "load_dpf_result": dpf_tools.load_dpf_result,
    "get_dpf_stress": dpf_tools.get_dpf_stress,
    "get_dpf_temperature": dpf_tools.get_dpf_temperature,
    "get_dpf_displacement": dpf_tools.get_dpf_displacement,
    "get_dpf_field_statistics": dpf_tools.get_dpf_field_statistics,
    "export_dpf_results_to_csv": dpf_tools.export_dpf_results_to_csv,
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
                        "enum": ["user", "feedback", "project", "reference"],
                        "description": "memory 类型",
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
                    "rotor_outer_radius": {"type": "number", "description": "转子外径（mm）"},
                    "rotor_inner_radius": {"type": "number", "description": "转子内径（mm）"},
                    "num_slots": {"type": "integer", "description": "定子槽数"},
                    "num_poles": {"type": "integer", "description": "极数"},
                    "magnet_thickness": {"type": "number", "description": "永磁体厚度（mm）"},
                    "stack_length": {"type": "number", "description": "轴向叠片长度（mm）"},
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
            "description": "添加求解设置（瞬态 / 磁静态 / 涡流）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string", "description": "求解设置名称，默认 Setup1"},
                    "solver_type": {"type": "string", "enum": ["Transient", "Magnetostatic", "EddyCurrent"], "description": "求解器类型"},
                    "stop_time": {"type": "number", "description": "仿真结束时间（秒，瞬态专用）"},
                    "time_step": {"type": "number", "description": "时间步长（秒，瞬态专用）"},
                    "num_passes": {"type": "integer", "description": "自适应网格剖分最大迭代次数"},
                    "frequency_Hz": {"type": "number", "description": "涡流求解频率（Hz，EddyCurrent 专用）"},
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
            "description": "提取平均转矩和转矩波形。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string"},
                    "sweep_name": {"type": "string"},
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
                    "phase_name": {"type": "string", "description": "相名称，如 PhaseA"},
                    "setup_name": {"type": "string"},
                    "sweep_name": {"type": "string", "description": "扫描/时间步名称，如 LastAdaptive"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_flux_density",
            "description": "获取指定点的磁通密度幅值。",
            "parameters": {
                "type": "object",
                "properties": {
                    "setup_name": {"type": "string"},
                    "point": {"type": "array", "items": {"type": "number"}, "description": "[x, y, z]（mm）"},
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
                    "setup_name": {"type": "string"},
                    "sweep_name": {"type": "string", "description": "扫描/时间步名称，如 LastAdaptive"},
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
                    "non_graphical": {"type": "boolean"},
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
            "parameters": {"type": "object", "properties": {"version": {"type": "string"}}},
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
                    "num_modes": {"type": "integer", "description": "提取模态阶数"},
                    "freq_range_hz": {"type": "array", "items": {"type": "number"}, "description": "[f_min, f_max] Hz"},
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
                    "freq_range_hz": {"type": "array", "items": {"type": "number"}, "description": "[f_min, f_max] Hz"},
                    "num_steps": {"type": "integer"},
                    "damping_ratio": {"type": "number"},
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
                    "name": {"type": "string", "description": "变量名"},
                    "value": {"type": "number", "description": "初始值"},
                    "unit": {"type": "string", "description": "单位，如 mm、deg、A"},
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
                    "result_expression": {"type": "string", "description": "结果表达式，如 Torque、CoreLoss"},
                    "sweep_name": {"type": "string"},
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
                    "iterations": {"type": "integer", "description": "最大迭代步数，默认 300"},
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
                    "operating_temperature_C": {"type": "number", "description": "工作温度（°C），用于矫顽力温度修正，默认 120"},
                    "safety_margin": {"type": "number", "description": "退磁安全裕量阈值（0~1），低于此值报警，默认 0.1"},
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
                    "is_2d": {"type": "boolean", "description": "True 导出 Maxwell 2D（快），False 导出 Maxwell 3D（含端部效应）"},
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
                    "server": {"type": "string", "description": "MAPDL 服务器地址，本地启动时忽略"},
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
                    "result_type": {"type": "string", "description": "stress（应力）/ deformation（变形）/ frequency（固有频率），默认 stress"},
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
            "description": "将当前报告导出为 HTML 或 PDF 文件，汇总所有仿真结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {"type": "string", "description": "输出格式：html 或 pdf，默认 html"},
                    "filename": {"type": "string", "description": "输出文件名（不含扩展名），默认 motor_analysis_report"},
                },
            },
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
    # 외부 CAD 导入
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
})

_ICEPAK_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_icepak", "setup_motor_thermal", "run_thermal_simulation", "get_temperature_results",
})

_FLUENT_TOOL_NAMES: frozenset[str] = frozenset({
    "connect_fluent", "read_fluent_mesh", "setup_fluid_models", "define_boundary_conditions",
    "setup_fluent_solver", "initialize_fluent", "run_fluent_simulation",
    "get_fluent_results", "export_fluent_data", "setup_fluid_material",
})

_MAPDL_TOOL_NAMES: frozenset[str] = frozenset({
    # Mechanical 结构振动
    "connect_mechanical", "import_maxwell_forces", "run_modal_analysis",
    "run_harmonic_analysis", "get_vibration_results",
    # PyMAPDL 结构强度
    "connect_mapdl", "run_rotor_stress_analysis", "run_thermal_stress_analysis",
    "run_nvh_harmonic_analysis", "get_mapdl_structural_results", "disconnect_mapdl",
    # PyDPF 后处理
    "load_dpf_result", "get_dpf_stress", "get_dpf_temperature",
    "get_dpf_displacement", "get_dpf_field_statistics", "export_dpf_results_to_csv",
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
})

_REPORTING_TOOL_NAMES: frozenset[str] = frozenset({
    "generate_report", "export_aedt_report",
    "create_report_session", "add_report_section", "add_table_to_report",
    "add_image_to_report", "export_report",
})

# Main-Agent 保留的工具（跨软件协调 + 知识检索 + 技能加载）
_MAIN_TOOL_NAMES: frozenset[str] = frozenset({
    "link_maxwell_to_icepak", "run_em_thermal_iteration", "import_thermal_to_mechanical",
    "save_project", "open_project", "close_project", "list_designs", "copy_design",
    "build_knowledge_index", "search_official_docs",
    "list_memories", "read_memory", "save_memory", "delete_memory",
    "use_skill",
})


def _filter_definitions(names: frozenset[str]) -> list[dict]:
    return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in names]


def _filter_registry(names: frozenset[str]) -> dict:
    return {k: v for k, v in TOOL_REGISTRY.items() if k in names}


# 每个 Sub-Agent 的工具定义和注册表
MAXWELL_TOOL_DEFINITIONS = _filter_definitions(_MAXWELL_TOOL_NAMES)
MAXWELL_TOOL_REGISTRY = _filter_registry(_MAXWELL_TOOL_NAMES)

ICEPAK_TOOL_DEFINITIONS = _filter_definitions(_ICEPAK_TOOL_NAMES)
ICEPAK_TOOL_REGISTRY = _filter_registry(_ICEPAK_TOOL_NAMES)

FLUENT_TOOL_DEFINITIONS = _filter_definitions(_FLUENT_TOOL_NAMES)
FLUENT_TOOL_REGISTRY = _filter_registry(_FLUENT_TOOL_NAMES)

MAPDL_TOOL_DEFINITIONS = _filter_definitions(_MAPDL_TOOL_NAMES)
MAPDL_TOOL_REGISTRY = _filter_registry(_MAPDL_TOOL_NAMES)

MOTORCAD_TOOL_DEFINITIONS = _filter_definitions(_MOTORCAD_TOOL_NAMES)
MOTORCAD_TOOL_REGISTRY = _filter_registry(_MOTORCAD_TOOL_NAMES)

OPTIMIZATION_TOOL_DEFINITIONS = _filter_definitions(_OPTIMIZATION_TOOL_NAMES)
OPTIMIZATION_TOOL_REGISTRY = _filter_registry(_OPTIMIZATION_TOOL_NAMES)

REPORTING_TOOL_DEFINITIONS = _filter_definitions(_REPORTING_TOOL_NAMES)
REPORTING_TOOL_REGISTRY = _filter_registry(_REPORTING_TOOL_NAMES)

MAIN_TOOL_DEFINITIONS = _filter_definitions(_MAIN_TOOL_NAMES)
MAIN_TOOL_REGISTRY = _filter_registry(_MAIN_TOOL_NAMES)


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
            "icepak（热分析）、fluent（CFD 流体）、mapdl（结构/NVH/DPF后处理）、"
            "motorcad（Motor-CAD 解析初设计）、optimization（optiSLang优化/参数扫描）、"
            "reporting（报告生成）。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "enum": [
                        "maxwell", "icepak", "fluent", "mapdl",
                        "motorcad", "optimization", "reporting",
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
