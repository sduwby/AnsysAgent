# AnsysAgent

基于多 LLM 提供商 + 多 Agent 调度 + PyAEDT / PyFluent / PyMotorCAD / PyMAPDL / PyDyna 的全领域 Ansys 仿真 AI 助手，覆盖从电机设计到整车级仿真的完整端到端自动化流水线，包括：电磁仿真、热分析、流体力学、结构强度、NVH、碰撞安全、疲劳耐久、整车动力学、网格划分和试验数据管理。

## 功能特性

- **自然语言驱动**：用中文描述需求，Main Agent 自动路由到专业 Sub-Agent 执行
- **多 LLM 提供商**：运行时通过 `/config` 切换 DeepSeek / ChatGPT / Qwen / Gemini / GLM / MiniMax，并支持自动故障回退
- **多 Agent 架构**：内置 18 个专业代理，覆盖电机设计、整车碰撞、CFD、NVH、疲劳、动力学、结构、网格、试验数据等全领域
- **多轮对话**：完整上下文保持，支持追加修改
- **流式输出**：实时显示回复内容，工具调用实时可见
- **模块化工具**：180+ 内置工具覆盖 Ansys 全领域仿真，并支持通过 MCP 动态扩展额外工具
- **本地知识增强（RAG）**：自动索引内置文档和用户扩展知识目录，支持 PDF / PPTX / Notebook / Python / Markdown 等格式
- **技能与规则**：支持 `/rules` 管理自定义系统规则，并支持 `skills/` 目录下的专业流程技能
- **持久记忆（Memory）**：支持保存用户偏好、项目背景、外部参考入口等非代码型长期上下文
- **统一数据目录**：配置、日志、规则、技能、知识索引、MCP 配置统一写入 `ANSYS_DATA_DIR`

## 完整仿真流水线

### 电机设计流程
```
Motor-CAD 解析初设计 → export_motorcad_to_maxwell
        ↓                        ↓
RMXprt 解析建模     Maxwell 电磁精化 → 材料/网格 → 结果提取
        ↓                                            ↓
  export_to_maxwell                     get_inductance / get_efficiency_map
                                                     ↓
Icepak 热分析 ←── link_maxwell_to_icepak ←── get_losses
        ↓
run_em_thermal_iteration（迭代耦合收敛）
        ↓                        ↓
MAPDL 热应力/NVH      Mechanical 结构分析 ←── import_thermal_to_mechanical
        ↓
optiSLang 多目标优化 → Fluent CFD 冷却分析
        ↓
DPF 后处理（应力/温度场提取）→ 自动化 HTML/PDF 报告
```

### 整车级仿真流程
```
高级网格划分（结构/流体）→ 整车 CFD（外流场/电池热管理）
        ↓
整车结构强度分析（静力学/准静态/屈曲）
        ↓
整车 NVH 仿真（模态/频率响应/声学）
        ↓
整车动力学 VD 仿真（操稳性/平顺性/制动）
        ↓
疲劳耐久分析（S-N/E-N 曲线/载荷谱）
        ↓
整车碰撞安全仿真（LS-DYNA 正面/侧面/后部/行人保护）
        ↓
试验数据管理（NVH/VD/耐久试验数据 + CAE 相关性分析）
        ↓
自动化 HTML/PDF 报告
```

## 工具模块

### 核心仿真（PyAEDT）

| 模块 | 文件 | 工具数 | 主要功能 |
|------|------|--------|---------|
| 电磁仿真 | `maxwell_tools.py` | 9 | 建模、材料（含 B-H 曲线）、绕组、求解 |
| 结果提取 | `result_tools.py` | 11 | 转矩、反电动势、电感、磁链、效率 MAP、退磁校核 |
| 热分析 | `icepak_tools.py` | 4 | 温升、冷却设计 |
| 驱动器联仿 | `circuit_tools.py` | 5 | 逆变器电路 + 电机联合仿真 |
| EV 电驱联仿 | `ev_powertrain_tools.py` | 7 | 电池+控制器+电机整车电驱系统联仿 |
| NVH 分析 | `nvh_tools.py` | 8 | 电磁力→结构振动→声学完整 NVH 链路 |
| 成本估算 | `cost_tools.py` | 3 | 材料用量+制造工艺成本估算 |
| 结构振动 | `mechanical_tools.py` | 5 | 固有频率、NVH、谐响应分析 |
| 参数扫描 | `sweep_tools.py` | 5 | 单参数/二维笛卡尔积扫描 |
| 参数优化 | `optislang_tools.py` | 9 | 敏感性分析、ARSM/EA 多目标优化 |
| 报告生成 | `report_tools.py` | 2 | Markdown 报告简报 |
| 流体分析 | `fluent_tools.py` | 10 | CFD 网格、物理模型、边界条件、结果提取 |
| 项目管理 | `project_tools.py` | 5 | 保存/打开/关闭项目、列出/复制设计 |
| 网格控制 | `mesh_tools.py` | 4 | 长度细化、集肤深度、曲面近似、统计查询 |
| 耦合分析 | `coupling_tools.py` | 3 | 电磁-热自动耦合、迭代收敛、热-结构耦合 |
| RMXprt 初设计 | `rmxprt_tools.py` | 4 | 解析法快速建模、解析仿真、导出到 Maxwell |
| 场云图可视化 | `visualization_tools.py` | 3 | 创建/导出磁密/温度等场量云图 |

### 扩展仿真（PyMotorCAD / PyMAPDL / PyDPF / PyDyna）

| 模块 | 文件 | 工具数 | 主要功能 |
|------|------|--------|---------|
| Motor-CAD 初设计 | `motorcad_tools.py` | 8 | 解析法 EM/热网络/NVH 分析、效率 MAP、导出到 Maxwell |
| MAPDL 结构分析 | `mapdl_tools.py` | 6 | 转子离心应力、热应力、NVH 谐响应分析 |
| DPF 后处理 | `dpf_tools.py` | 6 | 加载 .rst 文件，提取应力/温度/位移场，导出 CSV |
| 自动化报告 | `dynamic_reporting_tools.py` | 9 | 文本/表格/图片插入，ADR 或内置 HTML 双轨输出 |

### 整车级仿真（PyDyna / PyFluent / PyMAPDL）

| 模块 | 文件 | 工具数 | 主要功能 |
|------|------|--------|---------|
| 碰撞安全仿真 | `crash_tools.py` | 18 | LS-DYNA 正面/侧面/后部碰撞、行人保护、假人损伤指标 |
| 整车 CFD | `vehicle_cfd_tools.py` | 11 | 外流场空气动力学、电池热管理、机舱热分析 |
| 疲劳耐久 | `fatigue_tools.py` | 9 | S-N 曲线、E-N 曲线、载荷谱、平均应力修正 |
| 整车动力学 | `vehicle_dynamics_tools.py` | 9 | 操稳性、平顺性、制动性能、悬架运动学 |
| 整车结构强度 | `vehicle_structural_tools.py` | 9 | 静力学、准静态、屈曲分析、弯曲/扭转载荷 |
| 高级网格划分 | `advanced_meshing_tools.py` | 9 | 四面体/六面体/多面体网格、质量检查、局部细化 |
| 整车 NVH | `vehicle_nvh_tools.py` | 9 | 整车模态、频率响应、声学分析 |
| 试验数据管理 | `test_data_tools.py` | 9 | NVH/VD/耐久试验数据、CAE 相关性分析、报告导出 |

**工具总计：180+ 个**

## 环境要求

- Python 3.10+
- Windows 10/11（64位）
- Ansys AEDT 2024 R1/R2（电磁/热/电路仿真必须）
- Ansys Motor-CAD 2024+（解析法初设计，可选）
- Ansys MAPDL 2024+（结构/NVH 分析，可选）
- Ansys Fluent 2023 R2+（流体分析，可选）
- Ansys LS-DYNA 2023+（碰撞安全仿真，可选）

## 安装

```bat
# 克隆项目
git clone <repo-url>
cd AnsysAgent

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖（含所有扩展库）
pip install -r requirements.txt
pip install -e .

# 配置 API Key（支持多提供商）
cp .env.example .env
# 编辑 .env，填入 LLM_PROVIDER / LLM_API_KEY / LLM_MODEL
```

## 使用

```bash
# 交互模式
ansys-agent

# 单次执行
ansys-agent -p "帮我建一个 36 槽 6 极 PMSM，外径 150mm"

# 查看版本
ansys-agent --version
```

### 内置命令

- `/help`：显示功能帮助
- `/config`：配置 LLM 提供商、API Key 和模型
- `/rules`：管理用户自定义规则（最多 5 个，每个最多 200 行）
- `/skills`：管理技能（查看内置/用户技能，添加、删除用户自定义技能）
- `/memory`：查看持久记忆索引和已保存条目
- `/mcp`：管理 MCP Server（查看已注册工具、添加/删除 server 配置）
- `/exit` / `/quit`：退出程序

### 日志查看

启动后自动在后台开启日志查看界面：

```
http://localhost:7788
```

支持实时刷新、INFO / WARNING / ERROR / DEBUG 四色染色。端口可通过环境变量 `ANSYS_LOG_PORT` 覆盖。

### 运行时数据目录

运行时可写数据统一保存在 `ANSYS_DATA_DIR`：

- 优先使用环境变量 `ANSYS_AGENT_HOME`
- 默认回退到 `~/.AnsysAgent`

目录结构示例：

```text
~/.AnsysAgent/
├── .env
├── memory/
│   ├── MEMORY.md
│   └── *.md
├── .rag/
│   └── keyword_index.json
├── knowledge/
│   ├── official/
│   └── internal/
├── logs/
├── roles/
├── skills/
└── mcp_servers.json
```

这意味着项目目录和打包后的 exe 同级目录都不再承担运行时写入职责。

### 切换 LLM 提供商

在对话中输入 `/config` 启动配置向导：

```
You: /config
[1] DeepSeek  [2] ChatGPT  [3] Qwen  [4] Gemini  [5] GLM  [6] MiniMax
请选择提供商 > 1
请输入 API Key > sk-...
配置已保存，Agent 已重新初始化。
```

> 支持的提供商：OpenRouter、DeepSeek、ChatGPT (OpenAI)、通义千问 (Qwen)、Gemini (Google)、GLM (智谱AI)、MiniMax。
> 默认提供商为 OpenRouter，默认模型为 `openai/gpt-oss-120b:free`。
> OpenRouter 内置免费模型：`openai/gpt-oss-120b:free`、`qwen/qwen3-next-80b-a3b-instruct:free`、`z-ai/glm-4.5-air:free`、`minimax/minimax-m2.5:free`。
> 主提供商限速时将自动按 OpenAI → GLM → MiniMax 顺序回退。

## 对话示例

### 电机设计示例
```
You: 用 Motor-CAD 快速估算一台 36 槽 6 极 PMSM，额定转速 3000rpm
  🔧 connect_motorcad → set_motorcad_geometry → run_motorcad_em_analysis
  ✓ 解析估算：效率 93.8%，转矩 47.2Nm，绕组温升 68°C

You: 生成效率 MAP，然后导出到 Maxwell 2D 做精确仿真
  🔧 get_motorcad_performance_map → export_motorcad_to_maxwell
  🔧 setup_length_mesh → setup_skin_depth_mesh → run_simulation
  ✓ 精确仿真完成，平均转矩：45.3 Nm

You: 提取 Ld/Lq，检查退磁风险，校核转子在 6000rpm 下的离心应力
  🔧 get_inductance → check_demagnetization → connect_mapdl → run_rotor_stress_analysis
  ✓ Ld=8.2mH Lq=12.4mH，无退磁风险；最大 von Mises 应力 187 MPa（安全）

You: 将电磁损耗耦合到 Icepak，迭代收敛后提取温度场做热应力分析
  🔧 link_maxwell_to_icepak → run_em_thermal_iteration
  🔧 export_dpf_results_to_csv → run_thermal_stress_analysis
  ✓ 迭代 3 轮收敛，绕组最高温升 82°C，热变形 0.03mm

You: 对气隙宽度做多目标优化，生成完整分析报告
  🔧 connect_optislang → run_optimization
  🔧 create_report_session → add_report_section → add_table_to_report → export_report
  ✓ 最优气隙 0.9mm，转矩提升 8.3%；报告已保存至 motor_report.html
```

### 整车级仿真示例
```
You: 为一辆电动车进行整车正面碰撞仿真，速度 50km/h
  🔧 create_crash_deck → load_vehicle_model → setup_frontal_crash
  🔧 add_initial_velocity → export_crash_model → run_crash_simulation
  ✓ 仿真完成，最大变形量 320mm，假人 HIC 值 245（满足 FMVSS 208 标准）

You: 分析整车空气动力学，计算风阻系数 Cd
  🔧 connect_vehicle_cfd → load_vehicle_cfd_mesh → setup_external_aero
  🔧 run_vehicle_cfd_simulation → get_aero_coefficients
  ✓ Cd=0.28，升力系数 Cl=0.12，满足设计要求

You: 进行整车模态分析，提取前 20 阶固有频率
  🔧 connect_vehicle_nvh_solver → load_vehicle_nvh_model
  🔧 setup_vehicle_modal_analysis → run_vehicle_nvh_simulation
  ✓ 第 1 阶弯曲模态 28.5Hz，第 1 阶扭转模态 35.2Hz

You: 对车身进行疲劳耐久分析
  🔧 connect_fatigue_solver → define_sn_curve → define_load_spectrum
  🔧 run_fatigue_analysis → get_fatigue_results
  ✓ 最小寿命 1.2e6 循环，最大损伤度 0.08（满足设计寿命要求）

You: 进行整车稳态回转分析，评估操稳性
  🔧 connect_vd_solver → define_vehicle_params → setup_steady_state_cornering
  🔧 run_vd_simulation → get_vd_results
  ✓ 侧向加速度 0.8g 时，横摆角速度 15.2°/s，侧倾角 3.5°

You: 对电池包进行液冷 CFD 热仿真
  🔧 setup_battery_thermal_cfd → define_vehicle_cfd_boundaries
  🔧 run_vehicle_cfd_simulation → get_thermal_results
  ✓ 最高温度 45.2°C，最大温差 5.8°C，满足热管理要求
```

## 本地知识库（RAG）

Agent 启动时会自动扫描以下目录，并将关键词索引写入 `ANSYS_DATA_DIR/.rag/keyword_index.json`：

| 目录 | 用途 | 来源类型标签 |
|------|------|------------|
| `docs/api/` | Ansys Python 库 API 速查表 PDF | `api` |
| `knowledge/official/` | Ansys 官方教程、课件、手册 | `official` |
| `knowledge/internal/` | 项目内内置内部文档 | `internal` |
| `~/.AnsysAgent/knowledge/official/` | 用户追加的官方文档 | `official` |
| `~/.AnsysAgent/knowledge/internal/` | 用户自定义经验文档、内部知识 | `internal` |

**支持的文件格式**：`.pdf`、`.pptx`、`.ipynb`、`.py`、`.md`、`.txt`、`.rst`

**首次使用 / 更新文档后**，删除旧 index 并重启 agent 触发重建：

```bash
rm ~/.AnsysAgent/.rag/keyword_index.json   # macOS / Linux
del %USERPROFILE%\.AnsysAgent\.rag\keyword_index.json  # Windows
ansys-agent                  # 重启后自动重建
```

如需自定义目录，可先设置 `ANSYS_AGENT_HOME`。

## Skill / Role / MCP

### Role

- 通过 `/rules` 交互式管理规则
- 规则文件保存在 `ANSYS_DATA_DIR/rules/`
- 每次对话前会动态注入到 system prompt

### Skill

- 内置技能随项目和打包文件分发
- 用户自定义技能放在 `ANSYS_DATA_DIR/skills/<skill-name>/SKILL.md`
- Agent 会在对话中按需调用 `use_skill`

### MCP

- MCP server 配置文件位于 `ANSYS_DATA_DIR/mcp_servers.json`
- 首次运行会自动生成默认配置
- 若安装了 `mcp` 和对应 server，MCP 工具会自动注册为可调用工具

## 打包（可执行文件）

```bat
# Windows
build.bat
# 输出：dist\ansys-agent.exe
```

打包时会自动将 `docs/api/`、`knowledge/`、`skills/` 目录内置到 exe 中，无需额外分发这些只读资源。

### 打包版知识库扩展

| 目录位置 | 说明 |
|---------|------|
| exe 内置（只读）| 打包时固化的 `docs/api` 和 `knowledge/official` 文件，随 exe 分发 |
| `ANSYS_DATA_DIR/knowledge/official/` | 用户可在此放置额外的官方文档 |
| `ANSYS_DATA_DIR/knowledge/internal/` | 用户自定义经验文档、内部知识 |
| `ANSYS_DATA_DIR/skills/` | 用户自定义技能目录 |
| `ANSYS_DATA_DIR/rules/` | 用户自定义规则目录 |
| `ANSYS_DATA_DIR/.env` | 用户覆盖的 LLM 配置 |

添加新文件后，删除 `ANSYS_DATA_DIR/.rag/keyword_index.json` 并重启 agent 即可触发重建，内置知识与自定义知识将同时生效。

## 目录结构

```
AnsysAgent/
├── main.py                        # CLI 入口（含 /config 向导）
├── agent/
│   ├── chat_agent.py              # Main Agent（流式 + 工具调用 + 自动回退）
│   ├── config_manager.py          # 多提供商 LLM 配置管理
│   ├── dispatcher.py              # Sub-Agent 分发器
│   ├── mcp_manager.py             # MCP 工具注册与调用
│   ├── paths.py                   # 统一运行时数据目录
│   ├── role_manager.py            # Role 管理
│   ├── skill_manager.py           # Skill 扫描与加载
│   ├── tool_definitions.py        # 工具注册表 + OpenAI function calling 定义
│   ├── prompt.py                  # Main Agent system prompt
│   ├── log_server.py              # 日志查看 HTTP server（默认端口 7788）
│   └── sub_agents/                # 18 个专业代理（含整车碰撞/CFD/NVH/疲劳/动力学/结构/网格/试验数据）
├── tools/
│   ├── maxwell_tools.py           # 电磁仿真（含自定义材料/B-H曲线）
│   ├── result_tools.py            # 结果提取（动态报告类别，含退磁校核）
│   ├── icepak_tools.py            # 热分析（幂等 setup 创建）
│   ├── circuit_tools.py           # 驱动器联仿
│   ├── ev_powertrain_tools.py     # EV 电驱系统联仿（电池+控制器+电机）
│   ├── nvh_tools.py               # NVH 完整链路（电磁力→结构→声学）
│   ├── cost_tools.py              # 电机成本估算
│   ├── mechanical_tools.py        # 结构振动/NVH
│   ├── sweep_tools.py             # 参数化扫描
│   ├── optislang_tools.py         # 参数优化
│   ├── report_tools.py            # Markdown 快速报告
│   ├── fluent_tools.py            # CFD 流体分析（PyFluent）
│   ├── project_tools.py           # 项目文件管理
│   ├── mesh_tools.py              # 网格控制
│   ├── coupling_tools.py          # 电磁-热-结构耦合（幂等迭代）
│   ├── rmxprt_tools.py            # RMXprt 快速初设计
│   ├── visualization_tools.py     # 场云图可视化
│   ├── motorcad_tools.py          # Motor-CAD 解析法初设计（PyMotorCAD）
│   ├── mapdl_tools.py             # MAPDL 结构强度/NVH（PyMAPDL）
│   ├── dpf_tools.py               # 仿真结果后处理（PyDPF-Post）
│   ├── dynamic_reporting_tools.py # 自动化报告生成（ADR/HTML 双轨）
│   ├── knowledge_tools.py         # 本地知识索引与检索
│   ├── skill_tools.py             # Skill 加载工具
│   ├── crash_tools.py             # LS-DYNA 整车碰撞安全仿真（PyDyna）
│   ├── vehicle_cfd_tools.py       # 整车 CFD 仿真（外流场/电池热管理）
│   ├── fatigue_tools.py           # 疲劳耐久仿真（S-N/E-N 曲线）
│   ├── vehicle_dynamics_tools.py  # 整车动力学 VD 仿真
│   ├── vehicle_structural_tools.py # 整车结构强度仿真
│   ├── advanced_meshing_tools.py  # 高级网格划分（结构/流体）
│   ├── vehicle_nvh_tools.py       # 整车 NVH 仿真
│   ├── test_data_tools.py         # 试验数据管理
│   └── utils.py                   # 共享辅助函数（_ok / _err）
├── skills/                        # 内置技能
├── docs/api/                      # Ansys Python 库 API 速查表 PDF
├── knowledge/
│   ├── official/                  # Ansys 官方教程、课件、手册（PDF / PPTX / ipynb）
│   └── internal/                  # 内部经验文档、自定义知识（MD / TXT / PY）
├── rag/
│   ├── config.py                  # RAG 路径配置
│   ├── ingest.py                  # 文档解析与 chunk 切分
│   ├── retriever.py               # 关键词检索（BM25-like）
│   └── service.py                 # index 构建 / 加载 / 检索服务（含内存缓存）
├── requirements.txt               # Python 依赖列表
├── build.bat                      # Windows 打包脚本
└── ansys-agent.spec               # PyInstaller 配置
```

## 注意事项

- `ansys-aedt-core`（Maxwell/Icepak/Circuit/RMXprt）仅支持 Windows，需本机安装 Ansys AEDT 2024
- `ansys-motorcad-core` 需要安装 Ansys Motor-CAD 并持有许可证
- `ansys-mapdl-core` 支持本地启动或远程 gRPC 连接，需 MAPDL 2021 R1+
- `ansys-dyna-core`（LS-DYNA）支持 Windows/Linux，需本机安装 Ansys LS-DYNA 2023+
- `ansys-dpf-post` 可独立后处理 .rst 文件，无需在线 MAPDL 实例
- `dynamic_reporting_tools` 在无 ADR 许可证时自动回退到内置 HTML 模板渲染，无需额外依赖
- Claude (Anthropic) 因 API 格式不兼容 OpenAI 客户端已移除，如需使用请自行实现 Anthropic 适配层
- 首次运行仿真前需确保对应 Ansys 软件已启动并处于就绪状态
- 运行时文件统一位于 `ANSYS_DATA_DIR`；如需自定义位置，请设置环境变量 `ANSYS_AGENT_HOME`
- RAG 知识索引位于 `ANSYS_DATA_DIR/.rag/keyword_index.json`；向用户知识目录添加新文档后需删除旧 index 并重启 agent 触发重建
- MCP 依赖为可选；未安装 `mcp` 或对应 MCP server 时会自动降级，不影响主流程
