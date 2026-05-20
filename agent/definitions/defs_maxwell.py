"""
Maxwell 电磁建模、RMXprt、电路、材料、CAD 导入、结果、耦合、可视化 工具定义（OpenAI function calling JSON schema）。
"""

DEFINITIONS_MAXWELL = [
    {
        "type": "function",
        "function": {
            "name": "build_knowledge_index",
            "description": "构建本地知识索引，供 RAG 检索使用；可索引 docs/api 和后续补充的 knowledge 文档。支持向量嵌入以提升语义检索能力。",
            "parameters": {
                "type": "object",
                "properties": {
                    "doc_paths": {"type": "array", "items": {"type": "string"}, "description": "要索引的目录或文件路径列表；留空则使用默认知识目录"},
                    "force_rebuild": {"type": "boolean", "description": "是否强制重建索引，默认 True"},
                    "with_embeddings": {"type": "boolean", "description": "是否生成向量嵌入，启用后支持语义检索，默认 True"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_official_docs",
            "description": "在本地知识索引中检索官方或内部文档片段，适合 API 用法、报错解释和推荐 workflow 问题。支持向量检索、关键词检索和混合模式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索问题或关键词"},
                    "top_k": {"type": "integer", "description": "返回结果条数，默认 5"},
                    "source_type": {"type": "string", "description": "可选过滤类型，如 api/manual/faq/workflow"},
                    "retrieval_mode": {"type": "string", "enum": ["vector", "keyword", "hybrid"], "description": "检索模式：vector(语义检索)、keyword(关键词匹配)、hybrid(混合模式，默认)"},
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
]
