"""
PyMAPDL、MapdlPool、DPF、自动化报告、EV、NVH、Cost 工具定义（OpenAI function calling JSON schema）。
"""

DEFINITIONS_MAPDL_DPF = [
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
]
