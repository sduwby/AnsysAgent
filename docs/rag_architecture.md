# AnsysAgent RAG 架构设计

## 目标

当前项目已经具备较强的 `执行层` 能力：

- 自然语言转工具调用
- 调用 PyAEDT / PyFluent / PyMAPDL / Motor-CAD / optiSLang 等接口
- 建模、求解、后处理、报告生成

但它缺一个稳定的 `知识层`，用于回答下面这类问题：

- 某个 Ansys 功能应该怎么用
- 某个 PyAnsys / PyAEDT API 的正确调用方式是什么
- 某个报错意味着什么
- 某类分析流程的推荐前置条件是什么
- 某个求解器/模块是否支持某类操作

RAG 的目标不是替代执行层，而是给执行层提供：

- 更可靠的知识依据
- 更好的工具选择与流程规划
- 更强的错误解释能力
- 更低的“模型瞎编 API / 流程”的概率


## 当前项目已具备的知识资产

当前项目并不是从零开始，`[docs/api](/Users/fittenwby/AnsysAgent/docs/api)` 下已经有一批 API 速查资料，可以直接作为第一阶段知识库输入：

- `[pyaedt_API_cheat_sheet.pdf](/Users/fittenwby/AnsysAgent/docs/api/pyaedt_API_cheat_sheet.pdf)`
- `[pyfluent_cheat_sheet.pdf](/Users/fittenwby/AnsysAgent/docs/api/pyfluent_cheat_sheet.pdf)`
- `[pymapdl_cheat_sheet.pdf](/Users/fittenwby/AnsysAgent/docs/api/pymapdl_cheat_sheet.pdf)`
- `[pymechanical_cheat_sheet.pdf](/Users/fittenwby/AnsysAgent/docs/api/pymechanical_cheat_sheet.pdf)`
- `[pymotorcad_cheat_sheet.pdf](/Users/fittenwby/AnsysAgent/docs/api/pymotorcad_cheat_sheet.pdf)`
- `[PyOptiSLang_cheat_sheet.pdf](/Users/fittenwby/AnsysAgent/docs/api/PyOptiSLang_cheat_sheet.pdf)`
- `[pydpf-core_cheat_sheet.pdf](/Users/fittenwby/AnsysAgent/docs/api/pydpf-core_cheat_sheet.pdf)`
- `[pydpf-post_cheat_sheet.pdf](/Users/fittenwby/AnsysAgent/docs/api/pydpf-post_cheat_sheet.pdf)`
- `[pydynamicreporting_cheat_sheet.pdf](/Users/fittenwby/AnsysAgent/docs/api/pydynamicreporting_cheat_sheet.pdf)`

这意味着：

- API 层资料已经有基础覆盖
- 第一版 RAG 不必再从 API 文档采集开始
- 现在更缺的是 `产品帮助文档`、`FAQ/错误库`、`最佳实践/workflow`、`版本兼容矩阵`

因此，后续知识库建设优先级建议调整为：

1. 先把 `docs/api` 中现有 PDF 做切块、建索引、加元数据
2. 再补官方帮助文档
3. 再补 FAQ / 错误说明
4. 再补最佳实践与兼容矩阵


## 总体架构

建议采用三层结构，而不是“纯向量检索 + LLM”。

### 1. 编排层

位置建议：

- 新增 `agent/knowledge_router.py`
- 或在 `[chat_agent.py](/Users/fittenwby/AnsysAgent/agent/chat_agent.py)` 中加入知识路由入口

职责：

- 判断当前问题属于：
  - `知识问答`
  - `执行请求`
  - `混合请求`
- 决定是否先查知识库，再决定是否调用工具

建议路由规则：

- “怎么做 / 什么意思 / 为什么报错 / 官方推荐 / 支持吗” -> 先走知识层
- “帮我创建 / 运行 / 导出 / 提取 / 优化” -> 优先走执行层
- “为什么这个工具失败 / 当前项目应该怎么改” -> 先查知识层，再结合执行状态回答


### 2. 知识层

位置建议：

- `knowledge/` 目录存原始知识库
- `rag/` 或 `agent/rag/` 存索引、检索与重排代码

建议模块拆分：

- `rag/ingest.py`
  - 文档切块
  - 元数据清洗
  - 建立索引
- `rag/retriever.py`
  - 关键词检索
  - 向量检索
  - 混合召回
- `rag/reranker.py`
  - 对候选文档按相关性重排
- `rag/grounding.py`
  - 生成回答时附带来源、章节、版本
- `rag/knowledge_registry.py`
  - 记录知识源、版本、更新时间、适用模块

建议检索流程：

1. 用户问题进入路由器
2. 做问题分类
3. 生成检索查询
4. 混合召回：
   - BM25 / 关键词
   - 向量检索
5. 按文档类型重排
6. 拼接高质量上下文
7. LLM 生成回答
8. 如果回答涉及可执行动作，再交给执行层


### 3. 执行层

保持当前架构不变，核心仍然是：

- `[agent/tool_definitions.py](/Users/fittenwby/AnsysAgent/agent/tool_definitions.py)`
- `[agent/chat_agent.py](/Users/fittenwby/AnsysAgent/agent/chat_agent.py)`
- `[tools/](/Users/fittenwby/AnsysAgent/tools)`

但知识层接入后，执行层要多两类输入：

- `知识依据`
- `执行前置条件`

例如：

- 在调用 `create_field_plot` 前，先从知识层确认某类 quantity 是否适用于当前求解器
- 在回答 “为什么 get_back_emf 失败” 时，知识层补充 Maxwell 瞬态求解前置条件，执行层补充当前状态机判断


## 推荐的实际实现方式

## A. 检索方式

不要只做纯向量检索，建议：

- `关键词检索` 处理 API 名、报错码、精确术语
- `向量检索` 处理自然语言问题
- `规则过滤` 处理版本、产品、模块归属

推荐优先级：

1. 关键词检索召回 20 条
2. 向量检索召回 20 条
3. 合并去重
4. 按模块 / 产品 / 版本过滤
5. 重排取前 5 到 8 条


## B. 文档切块策略

不同类型文档不要统一切法。

### 1. API 文档

切块粒度：

- 一个函数 / 一个类方法 / 一个对象属性 为一个 chunk

元数据建议：

- `source_type=api`
- `product=Maxwell/Icepak/Fluent/...`
- `library=pyaedt/pyfluent/...`
- `module`
- `class`
- `method`
- `version`

### 2. 用户手册 / 帮助文档

切块粒度：

- 一个小节
- 或 300 到 800 中文字 / 400 到 1200 英文词

元数据建议：

- `source_type=manual`
- `product`
- `chapter`
- `section`
- `version`

### 3. FAQ / 错误说明 / 支持文档

切块粒度：

- 一问一答
- 一条错误说明

元数据建议：

- `source_type=faq`
- `product`
- `error_code`
- `symptom`

### 4. 最佳实践 / workflow 文档

切块粒度：

- 一条完整流程
- 一组前置条件 + 步骤 + 输出

元数据建议：

- `source_type=workflow`
- `analysis_type`
- `solver`
- `prerequisites`


## C. 知识层输出格式

建议知识层不要只返回一段文本，而是返回结构化结果：

```json
{
  "answer": "建议先做瞬态求解，再提取反电动势。",
  "sources": [
    {
      "title": "PyAEDT Maxwell transient setup",
      "path": "knowledge/pyaedt/maxwell/setup.md",
      "section": "Transient analysis",
      "score": 0.92
    }
  ],
  "constraints": [
    "Back EMF requires transient solution",
    "Winding must be defined before voltage extraction"
  ],
  "recommended_tools": [
    "setup_winding",
    "add_solution_setup",
    "run_simulation",
    "get_back_emf"
  ]
}
```

这样执行层可以直接利用：

- `constraints` 做前置校验
- `recommended_tools` 做工具规划
- `sources` 给最终回答做引用


## 与当前项目的集成方式

## 方案 1：最小改造

在 `[agent/chat_agent.py](/Users/fittenwby/AnsysAgent/agent/chat_agent.py)` 中增加一个知识查询步骤。

建议流程：

1. 收到用户消息
2. 判断是否需要知识检索
3. 若需要，调用 `knowledge_query()`
4. 将知识结果作为额外 system/context 注入
5. 再进入现有 tool-calling 流程

适合：

- 快速落地
- 对现有工具层改动最小


## 方案 2：知识工具化

新增工具：

- `search_official_docs`
- `explain_ansys_error`
- `get_recommended_workflow`
- `get_api_usage_reference`

优点：

- 与当前工具调用机制统一
- 模型更容易决定“先查知识还是先执行”

缺点：

- 需要设计好工具输入输出


## 方案 3：知识层先行，执行层后置

适用于复杂任务：

1. 先生成“知识约束 + 执行计划”
2. 再决定是否真正调用工具

适合：

- 高风险流程
- 多求解器耦合
- 优化、热耦合、结构耦合这类长链任务


## 推荐你当前项目采用的路线

建议分 3 阶段做。

### 阶段 1：离线知识库 + 本地检索

先做：

- 官方文档落盘
- chunk + metadata
- BM25 + 向量检索
- 基础问答

此时不要急着让知识层直接控制执行层。


### 阶段 2：知识约束驱动工具规划

让知识层输出：

- 推荐流程
- 前置条件
- 风险提示

执行层继续负责真正调用工具。


### 阶段 3：知识层参与错误恢复

当工具失败时：

- 先把错误、参数、当前状态发给知识层
- 检索官方文档 / FAQ / API 说明
- 再生成“修复建议 + 下一步动作”

这一步会显著提升 Agent 的实用性。


## 你需要提供的官方知识库内容

下面这部分最关键。

如果你要做一个真正有用的知识层，建议你至少准备以下官方资料。

## 一、PyAnsys / Python API 文档

这是最优先的，因为你的项目本质上是 Python 执行代理。

补充说明：

- 当前项目的 `[docs/api](/Users/fittenwby/AnsysAgent/docs/api)` 已经覆盖了这部分的第一版输入
- 但这些 cheat sheet 更适合做 `API 速查层`
- 如果后面要提升知识层精度，仍建议补更完整的官方 API reference 页面或导出文档

你需要提供：

- PyAEDT 官方 API 文档
  - Maxwell
  - Icepak
  - Circuit
  - Mechanical
  - RMXprt
- PyFluent 官方 API 文档
- PyMAPDL 官方 API 文档
- PyDPF / DPF-Post 官方 API 文档
- Motor-CAD Python API 官方文档
- optiSLang Python 接口官方文档

至少要包含：

- 类 / 方法签名
- 参数说明
- 返回值
- 示例代码
- 版本信息


## 二、Ansys 产品帮助文档

这是流程和物理语义的主要来源。

你需要提供：

- Maxwell 帮助文档
  - 建模
  - 材料
  - 绕组
  - 求解设置
  - 后处理
  - 参数扫描
  - 退磁校核
- Icepak 帮助文档
  - 热源定义
  - 边界条件
  - 冷却模型
- Mechanical 帮助文档
  - 电磁力导入
  - 模态
  - 谐响应
- Fluent 帮助文档
  - 模型设置
  - 边界条件
  - 湍流模型
- Motor-CAD 帮助文档
  - EM
  - Thermal
  - NVH
  - Export
- optiSLang 帮助文档
  - 参数
  - 响应
  - 算法
  - workflow


## 三、官方 FAQ / 支持知识库

这部分对报错解释非常重要。

你需要提供：

- 官方 FAQ
- 常见错误码说明
- 已知限制
- 常见兼容性问题
- 许可证相关限制说明

最好按下面维度整理：

- 产品
- 版本
- 症状
- 根因
- 官方建议


## 四、官方最佳实践 / workflow 文档

这部分不是 API 文档，但对 Agent 非常关键。

你需要提供：

- PMSM 建模推荐流程
- 电磁-热耦合流程
- 参数扫描推荐流程
- 优化流程
- NVH 流程
- 退磁校核流程
- 结果验证流程

这类内容最适合转成：

- `workflow` 型 chunk
- `前置条件 -> 步骤 -> 结果 -> 风险`


## 五、版本兼容矩阵

这是很多 AI 助手最容易缺的。

你需要提供：

- Ansys 产品版本
- 对应 Python 库版本
- 支持的操作系统
- 依赖前置条件
- 已知不兼容组合

例如：

- AEDT 2024 R1 对应哪版 `ansys-aedt-core`
- Motor-CAD 哪些 API 在某版本后新增
- 哪些接口只支持 Windows


## 六、许可证与能力边界说明

这部分不是技术细节，但对 Agent 很重要。

你需要提供：

- 哪些功能需要额外 license
- 哪些模块没有 license 时会失败
- 哪些功能只能 GUI 模式
- 哪些功能支持非图形模式

这样知识层才能回答：

- “为什么这个功能不能用”
- “是不是许可证问题”


## 七、你们自己的内部知识

如果只用官方知识，Agent 仍然会缺“项目本地真实经验”。

建议你再补：

- 当前项目 tools 的使用约束
- 已知 bug 清单
- 你们常见电机模板
- 常见分析流程模板
- 内部推荐参数范围
- 内部失败案例与规避方式

这部分会让知识层真正服务于当前项目，而不是泛泛回答 Ansys 问题。


## 官方知识库内容的最小交付清单

如果你现在只想先做第一版，建议你至少先准备这些：

1. 现有 `docs/api` 下的 API cheat sheet
2. Maxwell / Icepak / Mechanical / Fluent / Motor-CAD / optiSLang 官方帮助文档
3. 官方 FAQ / 常见错误说明
4. 官方 workflow / best practices
5. 版本兼容表

如果资源有限，优先级建议：

1. `docs/api + Maxwell help`
2. `Icepak / Mechanical / Fluent help`
3. `Motor-CAD / optiSLang help`
4. `FAQ / 错误库`
5. `最佳实践 / 版本矩阵`


## 知识库目录建议

建议目录：

```text
knowledge/
├── official/
│   ├── pyaedt/
│   │   ├── maxwell/
│   │   ├── icepak/
│   │   ├── circuit/
│   │   └── mechanical/
│   ├── pyfluent/
│   ├── pymapdl/
│   ├── pydpf/
│   ├── motorcad/
│   ├── optislang/
│   ├── manuals/
│   ├── faq/
│   ├── workflows/
│   └── compatibility/
├── internal/
│   ├── tool_constraints/
│   ├── known_issues/
│   ├── workflow_templates/
│   └── troubleshooting/
└── indexes/
    ├── bm25/
    └── vector/
```


## 不建议的做法

不要做这些：

- 只丢一堆 PDF 给向量库，不做结构化元数据
- 不区分 API 文档和流程文档
- 不记录版本
- 不区分官方知识和内部知识
- 把知识层和执行层混成一个 prompt

这些做法短期能跑，长期一定会失控。


## 最终建议

对这个项目，最稳的方向不是“做一个通用 RAG”，而是做：

- `官方文档检索`
- `项目内部规则库`
- `执行前置条件约束`
- `错误恢复知识支持`

也就是：

- 知识层负责“说对”
- 执行层负责“做对”

两层分开，才是这个项目后面能持续演进的架构。
