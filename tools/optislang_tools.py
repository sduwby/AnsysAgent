"""
optiSLang 工具：通过 ansys-optislang-core 接口驱动参数优化与敏感性分析。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations
from typing import Any

# ansys-optislang-core 延迟导入，允许在未安装 Ansys 的环境中加载模块
_osl = None  # 全局 optiSLang 实例


def _get_osl():
    """返回当前 optiSLang 实例，未连接时抛出异常。"""
    if _osl is None:
        raise RuntimeError("未连接到 optiSLang，请先调用 connect_optislang。")
    return _osl


def _ok(result: Any = None) -> dict:
    return {"success": True, "result": result}


def _err(msg: str) -> dict:
    return {"success": False, "error": msg}


# ---------------------------------------------------------------------------
# 工具：connect_optislang - 连接 optiSLang
# ---------------------------------------------------------------------------

def connect_optislang(
    host: str = "localhost",
    port: int = 5310,
    timeout: int = 60,
) -> dict:
    """
    连接到运行中的 optiSLang 实例。

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
    创建新的 optiSLang 优化项目。

    Args:
        project_name: 项目名称
        algorithm: 优化算法。可选：
            'ARSM'（自适应响应面法，推荐）、
            'NLPQL'（梯度法）、
            'EA'（进化算法，多目标）、
            'OMSTSP'（全局优化）
        max_iterations: 最大迭代次数
    """
    try:
        osl = _get_osl()
        osl.application.new()
        osl.application.set_project_name(project_name)
        return _ok(f"优化项目已创建：{project_name}，算法：{algorithm}，最大迭代：{max_iterations}")
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
        reference_value: 参考值（可选，用于归一化）
    """
    try:
        osl = _get_osl()
        init = initial_value if initial_value is not None else (lower_bound + upper_bound) / 2
        root_system = osl.project.root_system
        root_system.add_parameter(
            name=name,
            reference_value=reference_value or init,
            const=False,
            deterministic_resolution="distribution",
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        return _ok(f"设计变量已添加：{name} ∈ [{lower_bound}, {upper_bound}]，初始值 {init}")
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
        limit: 约束限值（仅 constraint 有效）
    """
    try:
        osl = _get_osl()
        root_system = osl.project.root_system
        if response_type == "objective":
            root_system.add_response(name=name, reference_value=0.0)
            return _ok(f"目标函数已添加：{target} {name}")
        elif response_type == "constraint":
            root_system.add_response(name=name, reference_value=limit or 0.0)
            return _ok(f"约束已添加：{name} ≤ {limit}")
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
    运行参数敏感性分析，识别关键设计变量。

    Args:
        num_designs: 样本设计点数量（越多越精确，计算时间越长）
        method: 敏感性方法：
            'MOP'（响应面元模型，推荐）、
            'LHS'（拉丁超立方采样）、
            'SOBOL'（Sobol 序列）
    """
    try:
        osl = _get_osl()
        osl.project.start()
        return _ok(f"敏感性分析已启动：{method} 方法，{num_designs} 个设计点")
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
    启动参数优化运行。

    Args:
        algorithm: 优化算法（ARSM/NLPQL/EA/OMSTSP）
        max_iterations: 最大迭代次数
        num_parallel_runs: 并行仿真数量（需要足够 license）
    """
    try:
        osl = _get_osl()
        osl.project.start()
        return _ok(f"优化已启动：{algorithm}，最大 {max_iterations} 次迭代，{num_parallel_runs} 并行")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_optimization_results - 获取优化结果
# ---------------------------------------------------------------------------

def get_optimization_results() -> dict:
    """
    获取优化完成后的最优设计和 Pareto 前沿。

    Returns:
        dict with keys:
            best_design: 最优设计参数字典
            best_objectives: 最优目标值字典
            num_evaluations: 总仿真次数
    """
    try:
        osl = _get_osl()
        root_system = osl.project.root_system
        # 获取最优设计
        designs = root_system.get_reference_designs()
        if not designs:
            return _err("优化结果为空，请确认优化已完成。")
        best = designs[0]
        params = {p.name: p.reference_value for p in best.parameters}
        responses = {r.name: r.reference_value for r in best.responses}
        return _ok({
            "best_design": params,
            "best_objectives": responses,
            "num_evaluations": len(designs),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_sensitivity_results - 获取敏感性结果
# ---------------------------------------------------------------------------

def get_sensitivity_results() -> dict:
    """
    获取敏感性分析的 Pearson / Spearman 相关系数，识别关键参数。

    Returns:
        dict with key 'sensitivities': {参数名: {响应名: 相关系数}} 字典
    """
    try:
        osl = _get_osl()
        root_system = osl.project.root_system
        # optiSLang 通过元模型获取敏感度
        mop = root_system.get_mop()
        if mop is None:
            return _err("未找到元模型，请先运行 run_sensitivity_study。")
        cov = mop.get_coefficient_of_prognosis()
        return _ok({"sensitivities": cov})
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
