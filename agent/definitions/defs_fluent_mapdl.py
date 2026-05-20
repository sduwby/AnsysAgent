"""
Fluent CFD、Meshing、项目管理、网格控制、Motor-CAD 工具定义（OpenAI function calling JSON schema）。
"""

DEFINITIONS_FLUENT_MAPDL = [
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
]
