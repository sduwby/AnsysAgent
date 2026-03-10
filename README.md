# AnsysAgent

基于多 LLM 提供商 + PyAEDT / PyFluent 的电机全流程仿真 AI 助手，覆盖从快速初设计到电磁、热、流体、结构、驱动器联仿、参数优化的完整端到端自动化流水线。

## 功能特性

- **自然语言驱动**：用中文描述需求，Agent 自动调用 Ansys 工具执行
- **多 LLM 提供商**：运行时通过 `/config` 切换 DeepSeek / ChatGPT / Claude / Qwen / Gemini
- **多轮对话**：完整上下文保持，支持追加修改
- **流式输出**：实时显示回复内容
- **模块化工具**：79 个工具覆盖电机仿真全流程，支持全自动化运行

## 完整仿真流水线

```
RMXprt 初设计 → Maxwell 电磁精化 → 自定义材料/网格 → 结果提取
      ↓                                                    ↓
  export_to_maxwell                            get_inductance / get_efficiency_map
                                                           ↓
Icepak 热分析 ←── link_maxwell_to_icepak ←── get_losses
      ↓
run_em_thermal_iteration（迭代耦合收敛）
      ↓
Mechanical 热应力 ←── import_thermal_to_mechanical
      ↓
optiSLang 多目标优化 → Fluent CFD 流体分析 → 报告 + 场云图
```

## 工具模块

| 模块 | 文件 | 工具数 | 主要功能 |
|------|------|--------|---------|
| 电磁仿真 | `maxwell_tools.py` | 9 | 建模、材料（含 B-H 曲线）、绕组、求解 |
| 结果提取 | `result_tools.py` | 11 | 转矩、反电动势、电感、磁链、效率 MAP、退磁校核 |
| 热分析 | `icepak_tools.py` | 4 | 温升、冷却设计 |
| 驱动器联仿 | `circuit_tools.py` | 5 | 逆变器电路 + 电机联合仿真 |
| 结构振动 | `mechanical_tools.py` | 5 | 固有频率、NVH、谐响应分析 |
| 参数扫描 | `sweep_tools.py` | 5 | 单参数/二维笛卡尔积扫描、效率 MAP |
| 参数优化 | `optislang_tools.py` | 9 | 敏感性分析、ARSM/EA 多目标优化 |
| 报告生成 | `report_tools.py` | 2 | HTML/Markdown 报告 |
| 流体分析 | `fluent_tools.py` | 10 | CFD 网格、物理模型、边界条件、结果提取 |
| 项目管理 | `project_tools.py` | 5 | 保存/打开/关闭项目、列出/复制设计 |
| 网格控制 | `mesh_tools.py` | 4 | 长度细化、集肤深度、曲面近似、统计查询 |
| 耦合分析 | `coupling_tools.py` | 3 | 电磁-热自动耦合、迭代收敛、热-结构耦合 |
| RMXprt 初设计 | `rmxprt_tools.py` | 4 | 解析法快速建模、解析仿真、导出到 Maxwell |
| 场云图可视化 | `visualization_tools.py` | 3 | 创建/导出磁密/温度等场量云图 |

## 环境要求

- Python 3.10+
- Ansys AEDT 2024 R1/R2（Windows/Linux，仿真功能必须）
- Ansys Fluent 2023 R2+（流体分析可选）
- macOS 可用于对话测试和报告生成

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd AnsysAgent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
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
[1] DeepSeek   [2] ChatGPT   [3] Claude   [4] Qwen   [5] Gemini
请选择提供商 > 2
请输入 API Key > sk-...
配置已保存，Agent 已重新初始化。
```

## 对话示例

```
You: 用 RMXprt 快速估算一台 36 槽 6 极 PMSM 的初始参数，额定功率 5kW
  🔧 connect_rmxprt → create_motor_from_template → run_rmxprt_analysis
  ✓ 解析估算：效率 94.2%，额定转矩 47.8 Nm

You: 导出到 Maxwell 2D，添加硅钢片 M250-35A 的 B-H 曲线，建立精确仿真模型
  🔧 export_to_maxwell → create_custom_material → import_bh_curve
  🔧 setup_length_mesh → setup_skin_depth_mesh → run_simulation
  ✓ 精确仿真完成，平均转矩：45.3 Nm

You: 提取 Ld/Lq，生成效率 MAP，检查退磁风险
  🔧 get_inductance → get_efficiency_map → check_demagnetization
  ✓ Ld=8.2mH Lq=12.4mH，峰值效率区间 2000~4000rpm，无退磁风险

You: 将电磁损耗耦合到 Icepak，迭代收敛后做热应力分析
  🔧 link_maxwell_to_icepak → run_em_thermal_iteration → import_thermal_to_mechanical
  ✓ 迭代 3 轮收敛，绕组最高温升 82°C，转子最大热变形 0.03mm

You: 对气隙宽度做参数优化，目标最大转矩，约束温升 < 100°C
  🔧 connect_optislang → add_design_variable → add_response → run_optimization
  ✓ 最优气隙 0.9mm，转矩提升 8.3%

You: 导出磁密云图，生成 HTML 报告
  🔧 create_field_plot → export_field_image → generate_report
  ✓ 报告已保存至 /tmp/motor_report.html
```

## 打包（可执行文件）

```bash
# macOS
bash build.sh
# 输出：dist/ansys-agent

# Windows（需在 Windows 上运行）
build.bat
# 输出：dist\ansys-agent.exe
```

## 目录结构

```
AnsysAgent/
├── main.py                    # CLI 入口（含 /config 向导）
├── agent/
│   ├── chat_agent.py          # 对话主循环（流式 + 工具调用）
│   ├── config_manager.py      # 多提供商 LLM 配置管理
│   ├── tool_definitions.py    # 工具注册表 + OpenAI function calling 定义
│   └── prompt.py              # System prompt（含完整工具说明）
├── tools/
│   ├── maxwell_tools.py       # 电磁仿真（含自定义材料/B-H曲线）
│   ├── result_tools.py        # 结果提取（含电感/效率MAP/退磁校核）
│   ├── icepak_tools.py        # 热分析
│   ├── circuit_tools.py       # 驱动器联仿
│   ├── mechanical_tools.py    # 结构振动/NVH
│   ├── sweep_tools.py         # 参数化扫描
│   ├── optislang_tools.py     # 参数优化
│   ├── report_tools.py        # 报告生成
│   ├── fluent_tools.py        # CFD 流体分析（PyFluent）
│   ├── project_tools.py       # 项目文件管理
│   ├── mesh_tools.py          # 网格控制
│   ├── coupling_tools.py      # 电磁-热-结构耦合
│   ├── rmxprt_tools.py        # RMXprt 快速初设计
│   ├── visualization_tools.py # 场云图可视化
│   └── utils.py               # 共享辅助函数
├── docs/api/                  # PyAEDT/PyFluent API 速查表 PDF
├── build.sh                   # macOS 打包脚本
├── build.bat                  # Windows 打包脚本
└── ansys-agent.spec           # PyInstaller 配置
```

## 注意事项

- `ansys-aedt-core` 仅支持 Windows/Linux，macOS 只能进行纯对话
- `ansys-fluent-core` 需要 Fluent 2023 R2+（`ansys-fluent-core>=0.20.0`）
- optiSLang 工具需要额外安装 `ansys-optislang-core`
- 首次运行需要 AEDT/Fluent 已启动并处于运行状态
- `get_efficiency_map` 依赖 PyAEDT ≥ 0.13 的参数化扫描 API
