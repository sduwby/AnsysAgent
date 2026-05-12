"""试验数据管理 Sub-Agent。"""
from __future__ import annotations

from agent.sub_agent_base import SubAgentBase
from agent.tool_definitions import TEST_DATA_TOOL_DEFINITIONS, TEST_DATA_TOOL_REGISTRY


class TestDataAgent(SubAgentBase):
    name = "test_data"
    workflow_stages = ("plan", "create_project", "import_data", "configure_tests", "correlate_cae", "summarize")
    description = (
        "试验数据管理专家，负责管理整车及零部件试验数据（NVH 试验、VD 试验、强耐试验、零部件试验），"
        "支持试验数据导入（CSV/RPC/UNV/UFF 格式）、试验工况配置、CAE-试验对标（MAC 频率误差），"
        "以及试验报告生成和试验-仿真关联分析"
    )

    def __init__(self, client, model, fallback_clients):
        super().__init__(
            client=client,
            model=model,
            fallback_clients=fallback_clients,
            tool_definitions=TEST_DATA_TOOL_DEFINITIONS,
            tool_registry=TEST_DATA_TOOL_REGISTRY,
        )

    def _infer_test_flow(self, task: str) -> tuple[str, list[str]]:
        text = task.lower()
        if any(token in text for token in ("导入", "import", "数据文件", "csv", "rpc", "unv", "uff")):
            return "data_import", [
                "确认数据文件路径和格式",
                "创建试验项目（如需）",
                "导入数据并配置通道信息",
            ]
        if any(token in text for token in ("nvh试验", "nvh test", "怠速", "wot", "路噪试验", "风噪试验")):
            return "nvh_test_setup", [
                "创建 NVH 试验项目",
                "描述试验工况配置",
                "导入试验数据",
                "配置 NVH 测点信息",
            ]
        if any(token in text for token in ("vd试验", "vd test", "操稳试验", "转向试验", "制动试验")):
            return "vd_test_setup", [
                "创建 VD 试验项目",
                "描述试验工况（ISO/GB 标准）",
                "导入 VD 试验数据",
            ]
        if any(token in text for token in ("强耐", "durability", "疲劳试验", "道路耐久")):
            return "durability_test_setup", [
                "创建强耐试验项目",
                "描述试验工况和路面条件",
                "导入结构应变/加速度数据",
            ]
        if any(token in text for token in ("对标", "correlat", "关联", "验证", "compare")):
            return "cae_test_correlation", [
                "准备仿真结果和试验数据",
                "配置对标方法（MAC/频率误差/FRF）",
                "执行 CAE-试验对标分析",
                "生成对标报告",
            ]
        if any(token in text for token in ("报告", "report", "导出", "export")):
            return "report_generation", [
                "选择试验项目",
                "汇总试验数据和分析结果",
                "生成试验报告",
            ]
        return "test_management", [
            "创建或选择试验项目",
            "导入试验数据",
            "配置试验工况",
            "关联试验与仿真结果",
        ]

    def build_execution_plan(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_test_flow(task)
        return f"[{flow_name}] {super().build_execution_plan(task, context)} 重点步骤: " + "；".join(checklist) + "。"

    def build_stage_guidance(self, task: str, context: str = "") -> str:
        flow_name, checklist = self._infer_test_flow(task)
        return (
            f"当前试验管理工作流类型：{flow_name}。\n"
            f"请按照 {' -> '.join(self.workflow_stages)} 推进。\n"
            f"执行检查清单：\n- " + "\n- ".join(checklist) + "\n"
            "试验数据管理支持多种工业标准格式，确保数据格式和通道信息正确配置。"
        )

    def prepare_run_context(self, run_context, task: str, context: str = "") -> None:
        super().prepare_run_context(run_context, task, context)
        flow_name, checklist = self._infer_test_flow(task)
        run_context.metadata["test_flow"] = flow_name
        run_context.metadata["test_checklist"] = checklist

    def finalize_run_context(self, run_context) -> None:
        super().finalize_run_context(run_context)
        if not run_context.success:
            return
        tool_names = [step.get("tool") for step in run_context.steps if step.get("tool")]
        if tool_names:
            run_context.metadata["tools_used"] = tool_names
        flow_name = run_context.metadata.get("test_flow", "test_management")
        run_context.output = f"[{flow_name}] {run_context.output}"
        run_context.metadata["final_summary"] = run_context.output
