# AnsysAgent

基于多 LLM 提供商 + PyAEDT / PyFluent / PyMotorCAD / PyMAPDL 的电机全流程仿真 AI 助手，覆盖从解析法快速初设计到电磁、热、流体、结构、NVH、驱动器联仿、参数优化和自动化报告的完整端到端自动化流水线。

## 功能特性

- **自然语言驱动**：用中文描述需求，Agent 自动调用 Ansys 工具执行
- **多 LLM 提供商**：运行时通过 `/config` 切换 DeepSeek / ChatGPT / Qwen / Gemini / GLM / MiniMax，并支持自动故障回退
- **多轮对话**：完整上下文保持，支持追加修改
- **流式输出**：实时显示回复内容，工具调用实时可见
- **模块化工具**：92 个工具覆盖电机仿真全流程，支持全自动化运行

## 完整仿真流水线

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

## 工具模块

### 核心仿真（PyAEDT）

| 模块 | 文件 | 工具数 | 主要功能 |
|------|------|--------|---------|
| 电磁仿真 | `maxwell_tools.py` | 9 | 建模、材料（含 B-H 曲线）、绕组、求解 |
| 结果提取 | `result_tools.py` | 11 | 转矩、反电动势、电感、磁链、效率 MAP、退磁校核 |
| 热分析 | `icepak_tools.py` | 4 | 温升、冷却设计 |
| 驱动器联仿 | `circuit_tools.py` | 5 | 逆变器电路 + 电机联合仿真 |
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

### 扩展仿真（PyMotorCAD / PyMAPDL / PyDPF）

| 模块 | 文件 | 工具数 | 主要功能 |
|------|------|--------|---------|
| Motor-CAD 初设计 | `motorcad_tools.py` | 8 | 解析法 EM/热网络/NVH 分析、效率 MAP、导出到 Maxwell |
| MAPDL 结构分析 | `mapdl_tools.py` | 6 | 转子离心应力、热应力、NVH 谐响应分析 |
| DPF 后处理 | `dpf_tools.py` | 6 | 加载 .rst 文件，提取应力/温度/位移场，导出 CSV |
| 自动化报告 | `dynamic_reporting_tools.py` | 9 | 文本/表格/图片插入，ADR 或内置 HTML 双轨输出 |

**工具总计：92 个**

## 环境要求

- Python 3.10+
- Windows 10/11（64位）
- Ansys AEDT 2024 R1/R2（电磁/热/电路仿真必须）
- Ansys Motor-CAD 2024+（解析法初设计，可选）
- Ansys MAPDL 2024+（结构/NVH 分析，可选）
- Ansys Fluent 2023 R2+（流体分析，可选）

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

### 切换 LLM 提供商

在对话中输入 `/config` 启动配置向导：

```
You: /config
[1] DeepSeek  [2] ChatGPT  [3] Qwen  [4] Gemini  [5] GLM  [6] MiniMax
请选择提供商 > 1
请输入 API Key > sk-...
配置已保存，Agent 已重新初始化。
```

> 支持的提供商：DeepSeek、ChatGPT (OpenAI)、通义千问 (Qwen)、Gemini (Google)、GLM (智谱AI)、MiniMax。
> 主提供商限速时将自动按 GLM → MiniMax 顺序回退。

## 对话示例

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

## 打包（可执行文件）

```bat
# Windows
build.bat
# 输出：dist\ansys-agent.exe
```

## 目录结构

```
AnsysAgent/
├── main.py                        # CLI 入口（含 /config 向导）
├── agent/
│   ├── chat_agent.py              # 对话主循环（流式 + 工具调用 + 自动回退）
│   ├── config_manager.py          # 多提供商 LLM 配置管理
│   ├── tool_definitions.py        # 工具注册表（92 个）+ OpenAI function calling 定义
│   └── prompt.py                  # System prompt
├── tools/
│   ├── maxwell_tools.py           # 电磁仿真（含自定义材料/B-H曲线）
│   ├── result_tools.py            # 结果提取（动态报告类别，含退磁校核）
│   ├── icepak_tools.py            # 热分析（幂等 setup 创建）
│   ├── circuit_tools.py           # 驱动器联仿
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
│   └── utils.py                   # 共享辅助函数（_ok / _err）
├── docs/api/                      # Ansys Python 库 API 速查表 PDF
├── requirements.txt               # Python 依赖列表
├── build.bat                      # Windows 打包脚本
└── ansys-agent.spec               # PyInstaller 配置
```

## 注意事项

- `ansys-aedt-core`（Maxwell/Icepak/Circuit/RMXprt）仅支持 Windows，需本机安装 Ansys AEDT 2024
- `ansys-motorcad-core` 需要安装 Ansys Motor-CAD 并持有许可证
- `ansys-mapdl-core` 支持本地启动或远程 gRPC 连接，需 MAPDL 2021 R1+
- `ansys-dpf-post` 可独立后处理 .rst 文件，无需在线 MAPDL 实例
- `dynamic_reporting_tools` 在无 ADR 许可证时自动回退到内置 HTML 模板渲染，无需额外依赖
- Claude (Anthropic) 因 API 格式不兼容 OpenAI 客户端已移除，如需使用请自行实现 Anthropic 适配层
- 首次运行仿真前需确保对应 Ansys 软件已启动并处于就绪状态
