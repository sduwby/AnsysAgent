"""
Icepak 热分析、optiSLang 优化、参数扫描、报告生成（前段） 工具定义（OpenAI function calling JSON schema）。
"""

DEFINITIONS_ICEPAK_FLUENT = [
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
]
