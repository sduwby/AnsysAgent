"""
参数化扫描工具：通过 PyAEDT 在 Maxwell 中进行单参数或多参数扫描。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.maxwell_tools import _app
from tools.utils import _ok, _err


# ---------------------------------------------------------------------------
# 工具：add_parametric_variable - 添加参数化变量
# ---------------------------------------------------------------------------

def add_parametric_variable(
    name: str,
    value: float,
    unit: str = "mm",
) -> dict:
    """
    在 Maxwell 设计中添加/设置参数化变量。

    Args:
        name: 变量名，如 "air_gap"
        value: 变量初始值
        unit: 单位，如 "mm"、"deg"、"A"
    """
    try:
        app = _app()
        app.variable_manager.set_variable(name, f"{value}{unit}")
        return _ok(f"变量 '{name}' 已设置为 {value}{unit}")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_parametric_sweep - 创建参数扫描表
# ---------------------------------------------------------------------------

def create_parametric_sweep(
    param_name: str,
    start: float,
    stop: float,
    step: float,
    setup_name: str = "Setup1",
) -> dict:
    """
    创建单参数线性扫描。

    Args:
        param_name: 要扫描的参数名（需已通过 add_parametric_variable 定义）
        start: 扫描起始值
        stop: 扫描终止值
        step: 扫描步长
        setup_name: 关联的求解设置名称
    """
    try:
        app = _app()
        # 计算扫描点
        values = []
        current = start
        while current <= stop + step * 0.001:
            values.append(round(current, 6))
            current += step

        # 创建参数扫描设置
        sweep = app.parametrics.add(
            variable=param_name,
            start_point=start,
            end_point=stop,
            step=step,
            variation_type="LinearStep",
        )
        # Maxwell 2D 中转矩表达式须带运动体前缀 "Moving1."
        sweep.add_calculation(setup_name, "LastAdaptive", ["Moving1.Torque", "CoreLoss"])
        sweep.update()

        return _ok({
            "sweep_name": sweep.name,
            "param": param_name,
            "num_points": len(values),
            "values": values,
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：run_parametric_sweep - 执行参数扫描
# ---------------------------------------------------------------------------

def run_parametric_sweep(sweep_name: str = "") -> dict:
    """
    运行已定义的参数扫描。

    Args:
        sweep_name: 扫描名称，空字符串则运行全部扫描
    """
    try:
        app = _app()
        if sweep_name:
            app.parametrics[sweep_name].analyze()
        else:
            app.parametrics.analyze()
        return _ok(f"参数扫描 '{sweep_name or '全部'}' 已完成")
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_sweep_results - 获取扫描结果
# ---------------------------------------------------------------------------

def get_sweep_results(
    param_name: str,
    result_expression: str = "Torque",
    sweep_name: str = "",
) -> dict:
    """
    提取参数扫描结果，返回参数值与对应仿真结果的映射。

    Args:
        param_name: 扫描参数名
        result_expression: 要提取的结果表达式，如 "Torque"、"CoreLoss"
        sweep_name: 扫描名称
    """
    try:
        app = _app()
        # 获取扫描数据
        data = app.post.get_solution_data(
            expressions=[result_expression],
            setup_sweep_name=f"Parametric : {sweep_name}" if sweep_name else "Parametric",
            primary_sweep_variable=param_name,
        )

        param_values = data.primary_sweep_values
        result_values = data.data_real(result_expression)

        # 找到最优点
        if result_values:
            max_idx = result_values.index(max(result_values))
            min_idx = result_values.index(min(result_values))
        else:
            max_idx = min_idx = 0

        return _ok({
            "param": param_name,
            "expression": result_expression,
            "data": dict(zip(param_values, result_values)),
            "max_value": {"param": param_values[max_idx] if param_values else None,
                          "result": result_values[max_idx] if result_values else None},
            "min_value": {"param": param_values[min_idx] if param_values else None,
                          "result": result_values[min_idx] if result_values else None},
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_2d_sweep - 创建二维参数扫描（两个参数同时扫描）
# ---------------------------------------------------------------------------

def create_2d_sweep(
    param1_name: str,
    param1_values: list[float],
    param2_name: str,
    param2_values: list[float],
    setup_name: str = "Setup1",
) -> dict:
    """
    创建二维参数扫描（笛卡尔积），适合绘制效率 MAP 等。

    Args:
        param1_name: 第一个参数名
        param1_values: 第一个参数取值列表
        param2_name: 第二个参数名
        param2_values: 第二个参数取值列表
        setup_name: 关联的求解设置
    """
    try:
        app = _app()
        total = len(param1_values) * len(param2_values)

        # 创建统一参数扫描，将两个参数加入同一个 ParametricSetup 形成笛卡尔积
        sweep = app.parametrics.add(
            variable=param1_name,
            values_list=param1_values,
            variation_type="SingleValues",
        )
        # 将第二个参数加入同一扫描（与第一参数构成笛卡尔积）
        sweep.add_variation(
            variable=param2_name,
            values_list=param2_values,
            variation_type="SingleValues",
        )
        sweep.add_calculation(setup_name, "LastAdaptive", ["Moving1.Torque", "CoreLoss", "OhmicLoss"])
        sweep.update()

        return _ok({
            "sweep_name": sweep.name,
            "total_points": total,
            "param1": {"name": param1_name, "count": len(param1_values)},
            "param2": {"name": param2_name, "count": len(param2_values)},
        })
    except Exception as e:
        return _err(str(e))
