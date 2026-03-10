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
}

# ---------------------------------------------------------------------------
# 工具定义（OpenAI function calling 格式，DeepSeek 兼容）
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
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
            "description": "在 Maxwell 2D 中建立 PMSM 电机几何模型（定子、转子、永磁体、气隙）。",
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
            "description": "配置绕组相激励。",
            "parameters": {
                "type": "object",
                "properties": {
                    "phase_name": {"type": "string", "description": "相名称，如 PhaseA"},
                    "conductor_names": {"type": "array", "items": {"type": "string"}, "description": "导体对象名称列表"},
                    "current_amplitude": {"type": "number", "description": "峰值电流（A）"},
                    "frequency": {"type": "number", "description": "电频率（Hz），磁静态置 0"},
                    "phase_angle": {"type": "number", "description": "相位角（度）"},
                },
                "required": ["phase_name", "conductor_names", "current_amplitude"],
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
                    "solver_type": {"type": "string", "enum": ["Transient", "Magnetostatic", "EddyCurrent"], "description": "求解器类型"},
                    "stop_time": {"type": "number", "description": "仿真结束时间（秒，瞬态专用）"},
                    "time_step": {"type": "number", "description": "时间步长（秒，瞬态专用）"},
                    "num_passes": {"type": "integer", "description": "自适应网格剖分最大迭代次数"},
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
            "description": "添加优化设计变量，设定取值范围。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "变量名（与 AEDT 参数名一致）"},
                    "lower_bound": {"type": "number", "description": "下限"},
                    "upper_bound": {"type": "number", "description": "上限"},
                    "initial_value": {"type": "number", "description": "初始值"},
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
            "description": "获取优化完成后的最优设计参数和目标值。",
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
            "parameters": {"type": "object", "properties": {"version": {"type": "string"}}},
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
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vibration_results",
            "description": "获取固有频率列表和振动结果。",
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
            "description": "创建单参数线性扫描（start 到 stop，步长 step）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "param_name": {"type": "string"},
                    "start": {"type": "number"},
                    "stop": {"type": "number"},
                    "step": {"type": "number"},
                    "setup_name": {"type": "string"},
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
            "description": "创建二维参数扫描（两个参数的笛卡尔积），适合效率 MAP。",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1_name": {"type": "string"},
                    "param1_values": {"type": "array", "items": {"type": "number"}},
                    "param2_name": {"type": "string"},
                    "param2_values": {"type": "array", "items": {"type": "number"}},
                    "setup_name": {"type": "string"},
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
                        "enum": ["velocity-inlet", "pressure-inlet", "pressure-outlet", "wall", "symmetry"],
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
]
