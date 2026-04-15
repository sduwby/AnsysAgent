# AnsysAgent 架构说明

## 概览

AnsysAgent 是一个基于多 LLM 提供商 + 多 Agent 调度的 Ansys 仿真 AI 助手。用户输入自然语言，Main Agent 理解意图并通过工具调用或委托给专业 Sub-Agent 执行具体仿真操作。

```
用户输入 (CLI)
     │
     ▼
┌─────────────────────────────────────────────┐
│               ChatAgent (Main Agent)        │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
│  │ LLM 客户 │  │ RAG 检索  │  │ 工具注册表 │  │
│  │ + 回退链 │  │ 关键词触发 │  │ 92+ 工具  │  │
│  └─────────┘  └──────────┘  └───────────┘  │
│  ┌──────────────────────────────────────┐   │
│  │ OmAgent Workflow Runtime             │   │
│  │ Context + Node + ToolLoopNode        │   │
│  └──────────────────────────────────────┘   │
└────────────────────┬────────────────────────┘
                     │ delegate_to_agent
                     ▼
┌─────────────────────────────────────────────┐
│               Dispatcher                   │
│  Sub-Agent 注册表 {name → SubAgentBase}     │
└──┬──────┬───────┬──────┬───────┬────────┬──┘
   │      │       │      │       │        │
maxwell icepak fluent mapdl motorcad optimization reporting
   │
   ▼
SubAgent Workflow（OmAgent 风格 ToolLoopNode）
   └── 调用 Tools 层（tools/*.py）
```

---

## 功能介绍

### 自然语言驱动的电机仿真

用户用中文描述仿真需求，系统自动分解任务、路由到专业子 Agent、依次调用 Ansys API，最终返回结构化结果。无需手动操作 AEDT GUI，无需记忆繁琐的 PyAEDT API 名称。

```
用户: "帮我建一个36槽6极PMSM，外径150mm，然后跑磁静态仿真，提取转矩"
系统自动完成：
  create_2d_motor_model → set_stator_slots(36) → set_poles(6)
  → assign_material → create_winding → setup_mesh
  → run_simulation → get_torque_result
```

### 多 LLM 提供商支持与自动故障回退

- 运行时通过 `/config` 切换提供商，无需重启（`DeepSeek / ChatGPT / Qwen / Gemini / GLM / MiniMax`）
- 主提供商限速（429 / 503）时自动按 `GLM → MiniMax` 顺序回退，对话不中断
- API Key 和模型配置统一存储在 `~/.AnsysAgent/.env`

### 多 Agent 协作架构

7 个专业 Sub-Agent 分别对应不同仿真域，Main Agent 通过 `delegate_to_agent` 路由：

| Sub-Agent | 负责领域 | 典型任务 |
|-----------|---------|---------|
| `maxwell` | 电磁仿真（PyAEDT） | 建模、求解、结果提取 |
| `icepak` | 热分析 | 温升、冷却设计 |
| `fluent` | 流体分析（PyFluent） | CFD 冷却仿真 |
| `mapdl` | 结构/NVH（PyMAPDL） | 离心应力、热应力、谐响应 |
| `motorcad` | 解析法初设计（PyMotorCAD） | 快速估算效率/温升，导出到 Maxwell |
| `optimization` | 参数优化（optiSLang） | 敏感性分析、多目标优化 |
| `reporting` | 自动化报告 | HTML/PDF 双轨输出 |

单次对话可跨多个 Sub-Agent 完成端到端流程（Motor-CAD 初设计 → Maxwell 精化 → Icepak 热分析 → 优化 → 报告）。

### OmAgent 风格工作流内核

为减少入口层和执行层的强耦合，当前版本在项目内新增了一个轻量级 OmAgent 风格运行时（`agent/omagent_runtime.py`）：

- `OmAgentContext`：统一承载任务、消息历史、步骤记录、共享状态和输出
- `OmAgentNode`：可组合的执行节点抽象
- `OmAgentWorkflow`：顺序编排多个节点
- `FunctionNode`：承载上下文准备、状态清洗、前置注入等轻量步骤
- `PlanningNode`：显式规划节点，负责生成执行计划和阶段元数据
- `SummaryNode`：显式总结节点，负责统一收尾和结果整形
- `ToolLoopNode`：封装 LLM → tool call → tool result → 下一轮 LLM 的循环
- `StreamingToolLoopNode`：封装流式 LLM → 工具调用 → 状态回传的循环

这层运行时目前先作为内部适配层使用，不要求安装外部 `omagent` 包，但已经把核心执行逻辑迁移为显式工作流，便于后续继续扩展成更复杂的 Node DAG、Hook、Trace 和异步调度。

### 工具调用循环（92+ 工具）

每个 Sub-Agent 在单次任务执行中可进行最多 30 轮工具调用，自主规划步骤：

- 判断前置条件（如仿真软件是否已启动）
- 按序调用多个 API（建模 → 材料设置 → 网格 → 求解 → 提取）
- 处理工具返回的警告并自动修正
- 在 30 轮内完成或返回失败原因

### 本地知识增强（RAG）

Agent 启动时自动索引 `docs/api/`（API 速查表）和 `knowledge/`（官方教程、内部文档），共支持 7 种文件格式（PDF / PPTX / ipynb / py / md / txt / rst）。

触发条件：用户消息含仿真相关关键词（`mesh`、`材料`、`如何`、`报错` 等）时自动检索，相关片段注入 system prompt 作为参考上下文。

### 多轮对话与上下文压缩

- 完整保留多轮对话历史，支持追加修改（"刚才那个仿真，改成外径160mm重跑"）
- 历史 token 超过阈值时自动调用 LLM 压缩旧对话为摘要，保留语义连续性

### Skill / Role / MCP 扩展机制

- **Skill**：`skills/*/SKILL.md` 中定义专业工作流，Agent 按需通过 `use_skill` 加载全文指导执行
- **Role**：`~/.AnsysAgent/rules/` 中自定义系统规则，每轮对话前动态注入 system prompt
- **MCP**：`mcp_servers.json` 配置外部 MCP Server，工具自动注册，运行时可扩展额外能力

---

## 组件详解

### 1. 入口层（`main.py`）

- 使用 Rich 库提供彩色交互式 CLI
- 解析命令行参数（`-p` 单次执行、`--version`）
- 处理内置命令：`/help` `/config` `/rules` `/skills` `/mcp` `/exit`
- 启动日志查看 HTTP server（守护线程，端口 7788）
- 管理向导：规则（`RoleManager`）、技能（`SkillManager`）、MCP（`MCPManager`）

### 2. ChatAgent（`agent/chat_agent.py`）

Main Agent，整个系统的核心协调器。

**初始化流程：**
```
ChatAgent.__init__
  ├── _init_client()          # 加载 LLM 配置，构建主客户端 + 回退链
  ├── _prepare_knowledge_index()  # 构建/加载 RAG 索引
  └── _init_sub_agents()      # 实例化 7 个 Sub-Agent 并注册到 Dispatcher
```

**每轮对话流程：**
```
用户输入
  ├── (可选) RAG 检索增强   # 触发词匹配 → search_index → 注入 system 消息
  ├── _maybe_compress_history()  # token 超阈值时压缩旧历史
  ├── _build_chat_workflow()
  │   ├── FunctionNode(prepare_chat_context)
  │   │   └── 负责用户消息入历史、压缩、知识注入和消息组装
  │   └── ToolLoopNode / StreamingToolLoopNode
  │       ├── _call_with_fallback() 调 LLM
  │       ├── 执行工具 / 委托 Sub-Agent
  │       └── 写回 history / steps / output
  └── 历史追加
```

**关键设计：**
- 流式输出（SSE），工具调用实时可见
- 主提供商失败 → 自动按 `FALLBACK_CHAIN`（GLM → MiniMax）顺序切换
- 历史 token 超过阈值时，旧消息交由 LLM 压缩为摘要（保留最近 N 条）

### 3. Dispatcher（`agent/dispatcher.py`）

轻量级路由层，维护一个全局注册表 `{name → SubAgentBase}`。

```python
# Main Agent 通过 delegate_to_agent 工具调用此函数
delegate_to_agent(agent_name="maxwell", task="建模 36槽6极", context="...")
  └── _REGISTRY["maxwell"].execute(task, context)
```

Sub-Agent 在 `ChatAgent._init_sub_agents()` 中统一实例化并注册，共享 Main Agent 的 LLM 客户端和回退链。

### 4. Sub-Agent 层（`agent/sub_agents/`）

7 个专业 Sub-Agent，每个继承 `SubAgentBase`：

| Sub-Agent | 职责 |
|-----------|------|
| `MaxwellAgent` | 电磁仿真：建模、材料、求解、结果提取 |
| `IcepakAgent` | 热分析：耦合热仿真、温升计算 |
| `FluentAgent` | CFD 流体分析：网格、边界、求解 |
| `MapdlAgent` | 结构/NVH：离心应力、热应力、谐响应 |
| `MotorCADAgent` | 解析法初设计：电磁/热网络/NVH |
| `OptimizationAgent` | 多目标优化：敏感性分析、ARSM/EA |
| `ReportingAgent` | 报告生成：HTML/PDF 双轨输出 |

**SubAgentBase 工作流执行（`execute()` / `run()` 方法）：**

```
context = OmAgentContext(
    task=user_task,
)
workflow = OmAgentWorkflow([
    PlanningNode(prepare_run_context),
    ToolLoopNode(llm_invoke=_call_llm, tool_invoke=_execute_tool),
    SummaryNode(finalize_run_context),
])
result = workflow.run(context)
```

默认基类会把以下元数据写入 `metadata`：

- `agent_name`
- `workflow_stages`
- `execution_plan`
- `tool_count`
- `num_steps`
- `final_summary`

当前 7 个 Sub-Agent 都已接入领域化规划与总结：

- `MaxwellAgent`：识别 `model_building`、`transient_postprocess`、`performance_map`
- `IcepakAgent`：识别 `thermal_setup`、`em_thermal_coupling`、`thermal_postprocess`
- `FluentAgent`：识别 `mesh_preparation`、`cfd_solve`、`cfd_postprocess`
- `MapdlAgent`：识别 `structural_solve`、`nvh_analysis`、`structural_postprocess`
- `MotorCADAgent`：识别 `initial_design`、`analytical_performance`、`export_to_maxwell`
- `OptimizationAgent`：识别 `optimization_study`、`sensitivity_study`、`parametric_sweep`
- `ReportingAgent`：识别 `report_generation`、`report_composition`、`report_export`

统一行为：

- 在 planning 阶段写入 flow-specific `execution_plan`、`checklist`、`stage_guidance`
- 在 summary 阶段写入 `tools_used`
- 返回带 flow 前缀的最终摘要，便于上层 Dispatcher 和 Main Agent 做结构化集成

### 5. 工具层（`tools/`）

92+ 工具按仿真域分模块，每个函数返回标准结构 `{"success": bool, "result": ...}`。

各模块保持**无状态**设计（状态通过全局 `_app` / `_mcad_app` 等延迟实例化），方便 Sub-Agent 按需调用。

共享工具函数统一在 `tools/utils.py` 中：`_ok()` / `_err()` / `append_warnings()` 等。

### 6. RAG 系统（`rag/`）

基于关键词的本地知识检索，非向量检索。

```
build_index()                    # 扫描文档 → 解析 → chunk → 存 JSON
  └── rag/ingest.py              # 支持 PDF/PPTX/ipynb/py/md/txt/rst

search_index(query, top_k=4)     # BM25-like 关键词匹配
  └── rag/retriever.py

触发条件（chat_agent.py）：
  用户消息包含 _KNOWLEDGE_HINTS 中的词 → 检索 → 注入 system 消息
```

索引文件：`ANSYS_DATA_DIR/.rag/keyword_index.json`（延迟构建，存在即复用）

### 7. LLM 配置层（`agent/config_manager.py`）

- 配置持久化到 `ANSYS_DATA_DIR/.env`
- 运行时通过 `/config` 命令热切换，无需重启
- 支持 DeepSeek / ChatGPT / Qwen / Gemini / GLM / MiniMax

**回退链：** 主提供商限速（429/402/503）→ 自动按 `GLM → MiniMax` 顺序重试。

### 8. 支撑模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 日志 | `agent/logger.py` | 按天轮转写入 `ANSYS_DATA_DIR/logs/`，保留 30 天 |
| 日志查看 | `agent/log_server.py` | 后台 HTTP server，`http://localhost:7788` |
| 数据目录 | `agent/paths.py` | 统一 `ANSYS_DATA_DIR`（`~/.AnsysAgent` 或 `ANSYS_AGENT_HOME`）|
| 规则管理 | `agent/role_manager.py` | 加载 `roles/*.md`，每轮对话动态注入 system prompt |
| 技能管理 | `agent/skill_manager.py` | 扫描 `skills/*/SKILL.md`，按需加载全文供 LLM 使用 |
| MCP 管理 | `agent/mcp_manager.py` | 读取 `mcp_servers.json`，热注册 MCP 工具到工具注册表 |

---

## 请求完整生命周期

```
1. 用户输入 "设计一个 36槽6极 PMSM，然后做热分析"

2. main.py → ChatAgent.chat(message)

3. ChatAgent 判断是否需要 RAG 增强
   └─ 含 "仿真/温度/..." → search_index() → 注入知识片段

4. 历史压缩检查（token > 阈值 → LLM 压缩旧历史）

5. 构建消息列表：[system] + [roles] + [knowledge] + [history] + [user]

6. 流式调用 LLM（带 92+ 工具定义）
   └─ LLM 决策: 调用 delegate_to_agent(agent="maxwell", task="...")

7. Dispatcher 路由到 MaxwellAgent

8. MaxwellAgent.execute() 工具调用循环（最多 30 轮）：
   setup_material → create_geometry → setup_mesh → run_simulation → get_torque
   └─ 每步调用 maxwell_tools.py / result_tools.py

9. Maxwell 结果返回 Main Agent

10. Main Agent 继续：delegate_to_agent(agent="icepak", task="热分析")
    └─ IcepakAgent.execute() 调用 link_maxwell_to_icepak → run_icepak_simulation

11. 最终文本回复流式输出给用户
```

---

## 扩展指南

### 添加新 Sub-Agent

1. 在 `agent/sub_agents/` 新建文件，继承 `SubAgentBase`
2. 设置 `name` / `description`，传入专属工具
3. 在 `ChatAgent._init_sub_agents()` 中实例化并注册
4. 在 Main Agent 的 `tool_definitions.py` 中补充 `delegate_to_agent` 的 `agent_name` 枚举值

### 添加新工具

1. 在对应 `tools/xxx_tools.py` 中添加函数，返回 `{"success": bool, ...}`
2. 在 `agent/tool_definitions.py` 中添加 OpenAI function calling 定义
3. 在对应 Sub-Agent 或 Main Agent 的工具注册表中注册

### 添加新技能

在 `skills/<skill-name>/SKILL.md` 中按 frontmatter 格式写入即可，SkillManager 自动扫描。

### 扩展 LLM 提供商

在 `agent/config_manager.py` 的 `PROVIDERS` 字典中添加新提供商配置（`base_url`、`models`）。

---

## 关键设计决策

| 决策 | 理由 |
|------|------|
| Sub-Agent 共享 Main Agent 的 LLM 客户端 | 避免重复初始化，统一回退链管理 |
| 工具层无状态 + 延迟实例化 | 仿真软件启动慢，按需连接，避免不必要的 COM 调用 |
| RAG 用关键词而非向量 | 无需 embedding 服务，本地离线可用，适合仿真专业术语精确匹配 |
| 历史压缩用 LLM 而非截断 | 保留语义连续性，避免截断导致 "忘记" 已完成的仿真步骤 |
| ANSYS_DATA_DIR 统一数据目录 | 打包 exe 时只读/可写分离，兼容 PyInstaller frozen 模式 |
