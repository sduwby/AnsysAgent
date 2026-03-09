# AnsysAgent

基于 DeepSeek + PyAEDT 的电机全流程仿真 AI 助手，支持电磁、热、结构、驱动器联仿和参数优化。

## 功能特性

- **自然语言驱动**：用中文描述需求，Agent 自动调用 Ansys 工具执行
- **多轮对话**：完整上下文保持，支持追加修改
- **流式输出**：实时显示回复内容
- **模块化工具**：42 个工具覆盖电机仿真全流程

## 工具模块

| 模块 | 文件 | 工具数 | 功能 |
|------|------|--------|------|
| 电磁仿真 | `maxwell_tools.py` | 7 | 建模、材料、绕组、求解 |
| 结果提取 | `result_tools.py` | 6 | 转矩、反电动势、磁通、损耗 |
| 热分析 | `icepak_tools.py` | 4 | 温升、冷却设计 |
| 驱动器联仿 | `circuit_tools.py` | 5 | 逆变器电路 + 电机联合仿真 |
| 结构振动 | `mechanical_tools.py` | 5 | 固有频率、NVH、转子应力 |
| 参数扫描 | `sweep_tools.py` | 5 | 单参数扫描、效率 MAP |
| 参数优化 | `optislang_tools.py` | 9 | 敏感性分析、多目标优化 |
| 报告生成 | `report_tools.py` | 2 | HTML/Markdown 报告 |

## 环境要求

- Python 3.10+
- Ansys AEDT 2024（Windows/Linux，仿真功能必须）
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

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
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

## 对话示例

```
You: 帮我建一个 36 槽 6 极的永磁同步电机，定子外径 150mm，转子外径 85mm，气隙 1mm
Assistant: 好的，我来为您建立该 PMSM 模型...
  🔧 调用工具: connect_aedt
  🔧 调用工具: create_maxwell_project
  🔧 调用工具: create_motor_geometry
  ✓ 电机几何模型已建立

You: 运行磁静态仿真，获取额定转矩
Assistant: 正在配置并运行仿真...
  🔧 调用工具: add_solution_setup
  🔧 调用工具: run_simulation
  🔧 调用工具: get_torque
  平均转矩：45.3 Nm，转矩纹波：3.2%

You: 对气隙宽度做参数扫描，范围 0.5~2mm，步长 0.25mm
You: 生成仿真报告，保存到 /tmp/motor_report.html
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
├── main.py              # CLI 入口
├── agent/
│   ├── chat_agent.py    # 对话主循环
│   └── prompt.py        # System prompt
├── tools/
│   ├── maxwell_tools.py
│   ├── result_tools.py
│   ├── icepak_tools.py
│   ├── circuit_tools.py
│   ├── mechanical_tools.py
│   ├── sweep_tools.py
│   ├── optislang_tools.py
│   └── report_tools.py
├── build.sh             # macOS 打包脚本
├── build.bat            # Windows 打包脚本
└── ansys-agent.spec     # PyInstaller 配置
```

## 注意事项

- `ansys-aedt-core` 仅支持 Windows/Linux，macOS 只能进行纯对话
- 首次运行需要 AEDT 已启动并处于运行状态
- optiSLang 工具需要额外安装 `ansys-optislang-core`
