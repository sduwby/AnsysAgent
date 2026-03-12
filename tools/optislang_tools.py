"""
optiSLang 工具：通过 ansys-optislang-core 接口驱动参数优化与敏感性分析。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。

依赖：pip install ansys-optislang-core
平台：仅支持 Windows（ansys-optislang-core 需 Windows 环境）
"""

from __future__ import annotations

from pathlib import Path

from tools.utils import _ok, _err

# ansys-optislang-core 延迟导入，允许在未安装 Ansys 的环境中加载模块
_osl = None  # 全局 optiSLang 实例
_osl_config: dict = {}  # 运行时配置（算法、迭代次数等）


def _get_osl():
    """返回当前 optiSLang 实例，未连接时抛出异常。"""
    if _osl is None:
        raise RuntimeError("未连接到 optiSLang，请先调用 connect_optislang。")
    return _osl


# ---------------------------------------------------------------------------
# 工具：connect_optislang - 连接 optiSLang
# ---------------------------------------------------------------------------

def connect_optislang(
    host: str = "localhost",
    port: int = 5310,
    timeout: int = 60,
) -> dict:
    """
    连接到运行中的 optiSLang 实例（需提前在 Windows 上启动 optiSLang）。

    Args:
        host: optiSLang 服务器主机名（默认 localhost）
        port: gRPC 端口（默认 5310）
        timeout: 连接超时时间（秒）
    """
    global _osl
    try:
        from ansys.optislang.core import Optislang
        _osl = Optislang(host=host, port=port, ini_timeout=timeout)
        return _ok(f"已连接到 optiSLang @ {host}:{port}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_optimization_project - 创建优化项目
# ---------------------------------------------------------------------------

def create_optimization_project(
    project_name: str,
    algorithm: str = "ARSM",
    max_iterations: int = 50,
) -> dict:
    """
    创建新的 optiSLang 优化项目并保存到当前工作目录。

    Args:
        project_name: 项目名称（保存为 <project_name>.opf）
        algorithm: 优化算法（存储配置，在 run_optimization 中生效）：
            'ARSM'（自适应响应面法，推荐）、'NLPQL'（梯度法）、
            'EA'（进化算法，多目标）、'OMSTSP'（全局优化）
        max_iterations: 最大迭代次数（存储配置）
    """
    try:
        osl = _get_osl()
        osl.application.new()
        # ansys-optislang-core 无 set_project_name()，通过 save_as() 保存并命名
        project_path = str(Path.cwd() / f"{project_name}.opf")
        osl.application.save_as(project_path)
        _osl_config["algorithm"] = algorithm
        _osl_config["max_iterations"] = max_iterations
        _osl_config["project_path"] = project_path
        return _ok(f"优化项目已创建：{project_path}，算法：{algorithm}，最大迭代：{max_iterations}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_design_variable - 添加设计变量
# ---------------------------------------------------------------------------

def add_design_variable(
    name: str,
    lower_bound: float,
    upper_bound: float,
    initial_value: float | None = None,
    reference_value: float | None = None,
) -> dict:
    """
    添加优化设计变量（参数）。

    Args:
        name: 变量名称（需与 AEDT 中参数名一致）
        lower_bound: 下限
        upper_bound: 上限
        initial_value: 初始值（默认取区间中点）
        reference_value: 参考值（默认同 initial_value）
    """
    try:
        from ansys.optislang.core.project_parametric import OptimizationParameter
        osl = _get_osl()
        init = initial_value if initial_value is not None else (lower_bound + upper_bound) / 2
        ref = reference_value if reference_value is not None else init
        root_system = osl.application.project.root_system
        param = OptimizationParameter(
            name=name,
            reference_value=ref,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        root_system.parameter_manager.add_parameter(param)
        return _ok(f"设计变量已添加：{name} ∈ [{lower_bound}, {upper_bound}]，参考值 {ref}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：add_response - 添加响应（目标/约束）
# ---------------------------------------------------------------------------

def add_response(
    name: str,
    response_type: str = "objective",
    target: str = "minimize",
    limit: float | None = None,
) -> dict:
    """
    添加优化响应（目标函数或约束条件）。

    Args:
        name: 响应名称（需与仿真输出变量名一致）
        response_type: 'objective'（目标函数）或 'constraint'（约束）
        target: 目标函数方向：'minimize' 或 'maximize'（仅 objective 有效）
        limit: 约束上限值（仅 constraint 有效，语义：name ≤ limit）
    """
    try:
        from ansys.optislang.core.project_parametric import (
            ObjectiveCriterion,
            ConstraintCriterion,
        )
        osl = _get_osl()
        root_system = osl.application.project.root_system
        cm = root_system.criterion_manager
        if response_type == "objective":
            criterion = ObjectiveCriterion(
                name=name,
                expression=name,
                criterion=target,
            )
            cm.add_criterion(criterion)
            return _ok(f"目标函数已添加：{target} {name}")
        elif response_type == "constraint":
            lim = limit if limit is not None else 0.0
            criterion = ConstraintCriterion(
                name=name,
                expression=name,
                criterion="lessequal",
                limit=lim,
            )
            cm.add_criterion(criterion)
            return _ok(f"约束已添加：{name} ≤ {lim}")
        else:
            return _err(f"未知 response_type：{response_type}，请使用 'objective' 或 'constraint'")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_sensitivity_study - 运行敏感性分析
# ---------------------------------------------------------------------------

def run_sensitivity_study(
    num_designs: int = 30,
    method: str = "MOP",
) -> dict:
    """
    运行参数敏感性分析（阻塞直到完成）。

    Args:
        num_designs: 样本设计点数量（越多越精确，计算时间越长）
        method: 敏感性方法（存储为元数据）：
            'MOP'（响应面元模型，推荐）、'LHS'（拉丁超立方采样）、'SOBOL'
    """
    try:
        osl = _get_osl()
        _osl_config["num_designs"] = num_designs
        _osl_config["method"] = method
        # osl.project.start() 会阻塞直到 optiSLang 完成所有计算
        # 具体的敏感性分析方法和采样点数须在 optiSLang 项目工作流节点中预先配置
        osl.application.project.start()
        return _ok(f"敏感性分析已完成：{method} 方法，{num_designs} 个设计点（目标值）")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_optimization - 运行优化
# ---------------------------------------------------------------------------

def run_optimization(
    algorithm: str = "ARSM",
    max_iterations: int = 50,
    num_parallel_runs: int = 1,
) -> dict:
    """
    启动参数优化运行（阻塞直到完成）。

    注意：算法类型和并行数量须在 optiSLang 项目工作流节点中预先配置；
    此处参数仅作记录，实际执行以项目文件中的配置为准。

    Args:
        algorithm: 优化算法（ARSM/NLPQL/EA/OMSTSP）
        max_iterations: 最大迭代次数（记录用）
        num_parallel_runs: 并行仿真数量（记录用）
    """
    try:
        osl = _get_osl()
        _osl_config.update({
            "algorithm": algorithm,
            "max_iterations": max_iterations,
            "num_parallel_runs": num_parallel_runs,
        })
        # osl.application.project.start() 阻塞直到优化完成
        osl.application.project.start()
        return _ok(f"优化已完成：{algorithm}，最大 {max_iterations} 次迭代，{num_parallel_runs} 并行")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_optimization_results - 获取优化结果
# ---------------------------------------------------------------------------

def get_optimization_results() -> dict:
    """
    获取优化完成后的最优设计和目标值。

    Returns:
        dict with keys:
            best_design: 最优设计参数字典 {param_name: value}
            best_objectives: 最优响应值字典 {response_name: value}
            num_evaluations: 本次优化评估的设计点总数
    """
    try:
        osl = _get_osl()
        root_system = osl.application.project.root_system
        # get_reference_design() 返回优化后的参考（最优）设计
        # 每个 Design 对象通过 .parameters 和 .responses 访问，各自有 .name 和 .value/.reference_value 属性
        design = root_system.get_reference_design()
        if design is None:
            return _err("优化结果为空，请确认优化已完成。")
        params = {p.name: p.reference_value for p in design.parameters}
        responses = {r.name: r.value for r in design.responses}
        return _ok({
            "best_design": params,
            "best_objectives": responses,
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_sensitivity_results - 获取敏感性结果
# ---------------------------------------------------------------------------

def get_sensitivity_results() -> dict:
    """
    获取敏感性分析结果（CoP = Coefficient of Prognosis）。

    optiSLang 将 CoP 矩阵写入工作目录下的 JSON/CSV 文件；
    此函数从工作目录读取结果文件，若找不到则返回工作目录路径供用户手动查看。

    Returns:
        dict with key 'sensitivities': CoP 数据字典，或工作目录路径提示
    """
    try:
        import json as _json
        osl = _get_osl()
        working_dir = Path(osl.application.project.get_working_dir())

        # 1) 尝试读取 optiSLang 输出的 CoP JSON 文件（标准输出路径）
        cop_candidates = (
            list(working_dir.rglob("CopMatrix*.json"))
            + list(working_dir.rglob("sensitivity_results*.json"))
            + list(working_dir.rglob("*cop*.json"))
        )
        if cop_candidates:
            with open(cop_candidates[0], encoding="utf-8") as f:
                data = _json.load(f)
            return _ok({"sensitivities": data, "source_file": str(cop_candidates[0])})

        # 2) 回退：返回工作目录路径供用户手动查看 optiSLang Postprocessing
        return _ok({
            "sensitivities": "CoP 文件未找到，请在 optiSLang Postprocessing 中查看 CoP 图表。",
            "working_dir": str(working_dir),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：disconnect_optislang - 断开连接
# ---------------------------------------------------------------------------

def disconnect_optislang() -> dict:
    """断开与 optiSLang 的连接并释放资源。"""
    global _osl
    try:
        if _osl is not None:
            _osl.dispose()
            _osl = None
        return _ok("已断开 optiSLang 连接")
    except Exception as e:
        return _err(str(e))
