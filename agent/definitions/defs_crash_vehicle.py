"""
碰撞、整车 CFD/疲劳/VD/结构/网格/NVH/试验数据 工具定义（OpenAI function calling JSON schema）。
"""

DEFINITIONS_CRASH_VEHICLE = [
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
    {
        "type": "function",
        "function": {
            "name": "parse_glstat",
            "description": "解析 LS-DYNA ASCII GLSTAT 文件，提取全局能量历程（动能/内能/沙漏能/总能量）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "glstat_path": {"type": "string", "description": "GLSTAT 文件路径"},
                    "output_path": {"type": "string", "description": "导出 JSON 路径（可选）"},
                },
                "required": ["glstat_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_nodout",
            "description": "解析 LS-DYNA ASCII NODOUT 文件，提取指定节点的加速度/速度/位移时间历程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "nodout_path": {"type": "string", "description": "NODOUT 文件路径"},
                    "node_ids": {"type": "array", "items": {"type": "integer"}, "description": "需要提取的节点 ID 列表，null 表示全部"},
                    "channels": {"type": "array", "items": {"type": "string"}, "description": "通道列表，如 ['ax','ay','az','vx','vy','vz','dx','dy','dz']"},
                    "output_path": {"type": "string", "description": "导出 JSON 路径（可选）"},
                },
                "required": ["nodout_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_rcforc",
            "description": "解析 LS-DYNA ASCII RCFORC 文件，提取接触面反力时间历程（壁障反力）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "rcforc_path": {"type": "string", "description": "RCFORC 文件路径"},
                    "interface_ids": {"type": "array", "items": {"type": "integer"}, "description": "接触面 ID 列表，null 表示全部"},
                    "output_path": {"type": "string", "description": "导出 JSON 路径（可选）"},
                },
                "required": ["rcforc_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "parse_bndout",
            "description": "解析 LS-DYNA ASCII BNDOUT 文件，提取边界约束反力时间历程。",
            "parameters": {
                "type": "object",
                "properties": {
                    "bndout_path": {"type": "string", "description": "BNDOUT 文件路径"},
                    "output_path": {"type": "string", "description": "导出 JSON 路径（可选）"},
                },
                "required": ["bndout_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_hic",
            "description": "从头部加速度时间历程计算头部损伤准则 HIC15/HIC36（FMVSS 208 / Euro NCAP）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_s": {"type": "array", "items": {"type": "number"}, "description": "时间序列（单位：s）"},
                    "acceleration_g": {"type": "array", "items": {"type": "number"}, "description": "合成加速度时间历程（单位：g）"},
                    "window_ms": {"type": "number", "description": "积分时间窗口（ms），15 或 36，默认 36"},
                    "output_path": {"type": "string", "description": "导出 JSON 路径（可选）"},
                },
                "required": ["time_s", "acceleration_g"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_chest_3ms",
            "description": "计算胸部 3ms 截止加速度（Chest 3ms Clip Criterion），FMVSS 208 限值 60 g。",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_s": {"type": "array", "items": {"type": "number"}, "description": "时间序列（单位：s）"},
                    "acceleration_g": {"type": "array", "items": {"type": "number"}, "description": "胸部合成加速度时间历程（单位：g）"},
                    "output_path": {"type": "string", "description": "导出 JSON 路径（可选）"},
                },
                "required": ["time_s", "acceleration_g"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_nij",
            "description": "计算颈部损伤准则 Nij（Neck Injury Criterion），主要用于后碰鞭打评估，限值 1.0（FMVSS 202a）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "fz_N": {"type": "array", "items": {"type": "number"}, "description": "颈部轴向力时间历程（N），拉伸为正"},
                    "my_Nm": {"type": "array", "items": {"type": "number"}, "description": "颈部弯矩时间历程（Nm），前屈为正"},
                    "dummy_size": {"type": "string", "enum": ["50th", "5th"], "description": "假人尺寸，默认 50th"},
                    "output_path": {"type": "string", "description": "导出 JSON 路径（可选）"},
                },
                "required": ["fz_N", "my_Nm"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_energy_balance",
            "description": "检验 LS-DYNA 碰撞仿真能量守恒：沙漏能/内能 ≤ 5%，总能量误差 ≤ 5%。",
            "parameters": {
                "type": "object",
                "properties": {
                    "glstat_path": {"type": "string", "description": "GLSTAT 文件路径（与直接传入列表二选一）"},
                    "internal_energy": {"type": "array", "items": {"type": "number"}, "description": "内能时间历程"},
                    "kinetic_energy": {"type": "array", "items": {"type": "number"}, "description": "动能时间历程"},
                    "hourglass_energy": {"type": "array", "items": {"type": "number"}, "description": "沙漏能时间历程"},
                    "total_energy": {"type": "array", "items": {"type": "number"}, "description": "总能量时间历程"},
                    "hourglass_ratio_limit": {"type": "number", "description": "沙漏能/内能允许最大比例，默认 0.05"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_intrusion_at_node",
            "description": "从 NODOUT 文件提取指定节点的位移作为结构侵入量（正面碰撞取 X 方向，侧面取 Y 方向）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "nodout_path": {"type": "string", "description": "NODOUT 文件路径"},
                    "node_id": {"type": "integer", "description": "目标节点 ID（如前围板关键节点）"},
                    "direction": {"type": "string", "enum": ["x", "y", "z"], "description": "位移方向，默认 x"},
                    "reference_node_id": {"type": "integer", "description": "参考节点 ID（用于计算相对侵入量，可选）"},
                    "output_path": {"type": "string", "description": "导出 JSON 路径（可选）"},
                },
                "required": ["nodout_path", "node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_node_set",
            "description": "向碰撞 Deck 添加节点集合（*SET_NODE），用于假人传感器约束、安全带附着点等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sid": {"type": "integer", "description": "节点集 ID"},
                    "node_ids": {"type": "array", "items": {"type": "integer"}, "description": "节点 ID 列表"},
                    "title": {"type": "string", "description": "节点集标题（可选）"},
                },
                "required": ["sid", "node_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_segment_set",
            "description": "向碰撞 Deck 添加段集合（*SET_SEGMENT），用于接触面精确分组。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sid": {"type": "integer", "description": "段集 ID"},
                    "segments": {"type": "array", "items": {"type": "array", "items": {"type": "integer"}}, "description": "段列表，每个段为 [n1,n2,n3,n4]"},
                    "title": {"type": "string", "description": "段集标题（可选）"},
                },
                "required": ["sid", "segments"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_part_set",
            "description": "向碰撞 Deck 添加部件集合（*SET_PART），用于施加整体初速、重力或接触分组。",
            "parameters": {
                "type": "object",
                "properties": {
                    "sid": {"type": "integer", "description": "部件集 ID"},
                    "part_ids": {"type": "array", "items": {"type": "integer"}, "description": "部件 ID 列表"},
                    "title": {"type": "string", "description": "部件集标题（可选）"},
                },
                "required": ["sid", "part_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_constrained_rigid_bodies",
            "description": "向碰撞 Deck 添加刚体连接约束（*CONSTRAINED_RIGID_BODIES），模拟焊点/螺栓连接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "master_pid": {"type": "integer", "description": "主刚体部件 ID"},
                    "slave_pids": {"type": "array", "items": {"type": "integer"}, "description": "从刚体部件 ID 列表"},
                },
                "required": ["master_pid", "slave_pids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "define_curve",
            "description": "向碰撞 Deck 添加载荷曲线（*DEFINE_CURVE），用于应力-应变、速度时间历程、气囊充气曲线等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "lcid": {"type": "integer", "description": "载荷曲线 ID"},
                    "abscissa": {"type": "array", "items": {"type": "number"}, "description": "横坐标值列表（时间 s 或应变）"},
                    "ordinate": {"type": "array", "items": {"type": "number"}, "description": "纵坐标值列表（力 N 或应力 MPa）"},
                    "title": {"type": "string", "description": "曲线标题（可选）"},
                    "sfa": {"type": "number", "description": "横坐标缩放因子，默认 1.0"},
                    "sfo": {"type": "number", "description": "纵坐标缩放因子，默认 1.0"},
                },
                "required": ["lcid", "abscissa", "ordinate"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_joint",
            "description": "向碰撞 Deck 添加运动副约束（*CONSTRAINED_JOINT_*），模拟车门铰链、座椅滑轨等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "joint_type": {"type": "string", "enum": ["revolute", "spherical", "translational", "rigid"], "description": "运动副类型"},
                    "node_a": {"type": "integer", "description": "约束节点 A"},
                    "node_b": {"type": "integer", "description": "参考节点 B"},
                    "node_c": {"type": "integer", "description": "转轴方向节点 C（revolute 有效）"},
                },
                "required": ["node_a", "node_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_seatbelt",
            "description": "向碰撞 Deck 添加安全带一维单元（*ELEMENT_SEATBELT + *SECTION_SEATBELT）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "belt_id": {"type": "integer", "description": "安全带单元起始 ID"},
                    "node_ids": {"type": "array", "items": {"type": "integer"}, "description": "安全带路径节点 ID 列表（卷收器→锁扣）"},
                    "section_id": {"type": "integer", "description": "截面 ID，默认 1"},
                    "material_id": {"type": "integer", "description": "材料 ID，默认 1"},
                    "pretension_force_N": {"type": "number", "description": "预张紧力（N），0 表示无预张紧"},
                    "retractor_node": {"type": "integer", "description": "卷收器节点 ID，0 表示无卷收器"},
                    "slip_ring_nodes": {"type": "array", "items": {"type": "integer"}, "description": "导向环节点 ID 列表（可选）"},
                },
                "required": ["belt_id", "node_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "place_rigid_wall_occ",
            "description": "在碰撞 Deck 中放置 OCC 正面刚性壁障（*RIGIDWALL_PLANAR），用于 FMVSS 208 Full Frontal 100% 正碰。",
            "parameters": {
                "type": "object",
                "properties": {
                    "wall_id": {"type": "integer", "description": "壁障 ID，默认 1"},
                    "x_mm": {"type": "number", "description": "壁障面中心 X 坐标（mm）"},
                    "y_mm": {"type": "number", "description": "壁障面中心 Y 坐标（mm）"},
                    "z_mm": {"type": "number", "description": "壁障面中心 Z 坐标（mm）"},
                    "normal_x": {"type": "number", "description": "壁障法向量 X 分量，默认 1.0"},
                    "normal_y": {"type": "number", "description": "壁障法向量 Y 分量，默认 0.0"},
                    "normal_z": {"type": "number", "description": "壁障法向量 Z 分量，默认 0.0"},
                    "friction": {"type": "number", "description": "壁障摩擦系数，默认 0.3"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "import_barrier_model",
            "description": "导入并配置移动可变形壁障模型（MDB/AE-MDB），用于侧面/前置偏置碰撞。",
            "parameters": {
                "type": "object",
                "properties": {
                    "barrier_path": {"type": "string", "description": "壁障 .k 文件路径"},
                    "barrier_type": {"type": "string", "enum": ["mdb", "ae_mdb", "offset"], "description": "壁障类型"},
                    "initial_speed_kmh": {"type": "number", "description": "壁障初始速度（km/h），默认 50"},
                    "speed_direction": {"type": "string", "enum": ["x", "y", "-x", "-y"], "description": "速度方向"},
                    "offset_x_mm": {"type": "number", "description": "X 方向偏移（mm）"},
                    "offset_y_mm": {"type": "number", "description": "Y 方向偏移（mm）"},
                },
                "required": ["barrier_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "place_dummy_model",
            "description": "导入假人（Hybrid III / THOR / WorldSID）模型并配置头/胸/颈/大腿传感器节点组。",
            "parameters": {
                "type": "object",
                "properties": {
                    "dummy_path": {"type": "string", "description": "假人 .k 文件路径"},
                    "dummy_type": {"type": "string", "enum": ["hybrid3_50th", "hybrid3_5th", "thor", "worldsid"], "description": "假人类型"},
                    "seat_position": {"type": "string", "enum": ["driver", "passenger", "rear_left", "rear_right"], "description": "座位位置"},
                    "x_mm": {"type": "number", "description": "假人质心 X 坐标（mm）"},
                    "y_mm": {"type": "number", "description": "假人质心 Y 坐标（mm）"},
                    "z_mm": {"type": "number", "description": "假人质心 Z 坐标（mm）"},
                    "head_sensor_node": {"type": "integer", "description": "头部 CG 传感器节点 ID（用于 HIC 计算）"},
                    "chest_sensor_node": {"type": "integer", "description": "胸部传感器节点 ID"},
                    "neck_sensor_node": {"type": "integer", "description": "颈部传感器节点 ID"},
                    "femur_sensor_nodes": {"type": "array", "items": {"type": "integer"}, "description": "大腿传感器节点 ID 列表"},
                },
                "required": ["dummy_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "setup_airbag",
            "description": "向碰撞 Deck 添加气囊模型（*AIRBAG_SIMPLE_PRESSURE_VOLUME 或 *AIRBAG_HYBRID）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "airbag_id": {"type": "integer", "description": "气囊 ID，默认 1"},
                    "airbag_type": {"type": "string", "enum": ["simple_pressure_volume", "hybrid"], "description": "气囊模型类型"},
                    "part_sid": {"type": "integer", "description": "气囊壳单元部件集 ID（*SET_PART）"},
                    "inflator_lcid": {"type": "integer", "description": "充气器质量流率-时间曲线 ID"},
                    "vent_area_m2": {"type": "number", "description": "排气孔总面积（m²）"},
                },
                "required": ["part_sid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_pretensioner",
            "description": "向碰撞 Deck 添加安全带预张紧器与限力器（*ELEMENT_SEATBELT_PRETENSIONER）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "retractor_id": {"type": "integer", "description": "对应的卷收器单元 ID（由 add_seatbelt 创建）"},
                    "pretension_force_N": {"type": "number", "description": "预张紧力（N），典型 3500 N"},
                    "pretension_time_ms": {"type": "number", "description": "预张紧作用时间（ms），典型 15 ms"},
                    "load_limiter_force_N": {"type": "number", "description": "限力器限制力（N），典型 4000 N"},
                    "load_limiter_lcid": {"type": "integer", "description": "限力器力-位移曲线 ID（0 使用常数限制力）"},
                },
                "required": ["retractor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_ncap_frontal",
            "description": "根据 Euro NCAP / FMVSS 208 / C-NCAP 限值对正面碰撞假人损伤指标进行合规评估与评分。",
            "parameters": {
                "type": "object",
                "properties": {
                    "hic36": {"type": "number", "description": "头部损伤准则 HIC36（无量纲，限值 700）"},
                    "chest_3ms_clip_g": {"type": "number", "description": "胸部 3ms 截止加速度（g，限值 60）"},
                    "chest_deflection_mm": {"type": "number", "description": "胸部最大压缩量（mm，限值 42）"},
                    "femur_force_kN": {"type": "number", "description": "大腿轴向最大力（kN，限值 10）"},
                    "neck_tension_N": {"type": "number", "description": "颈部最大张力（N）"},
                    "neck_compression_N": {"type": "number", "description": "颈部最大压力（N）"},
                    "standard": {"type": "string", "enum": ["euro_ncap", "fmvss208", "cncap"], "description": "评估标准，默认 euro_ncap"},
                    "output_path": {"type": "string", "description": "导出 JSON 路径（可选）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_crash_report",
            "description": "汇总碰撞仿真所有结果（能量守恒、结构侵入量、假人损伤、合规评估），生成结构化 JSON 综合报告。",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_path": {"type": "string", "description": "报告输出路径（.json）"},
                    "crash_type": {"type": "string", "description": "碰撞类型描述，如 frontal / side / rear"},
                    "simulation_info": {"type": "object", "description": "仿真基本信息（模型、工况、求解时间等）"},
                    "energy_balance": {"type": "object", "description": "能量守恒检验结果（来自 check_energy_balance）"},
                    "intrusion_results": {"type": "object", "description": "结构侵入量结果（来自 get_intrusion_at_node）"},
                    "dummy_results": {"type": "object", "description": "假人损伤指标原始值"},
                    "compliance_results": {"type": "object", "description": "合规评估结果（来自 evaluate_ncap_frontal）"},
                    "glstat_path": {"type": "string", "description": "GLSTAT 文件路径（自动解析能量守恒）"},
                },
                "required": ["report_path"],
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
