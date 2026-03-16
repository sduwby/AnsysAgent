"""
参数化扫描工具：通过 PyAEDT 在 Maxwell 中进行单参数或多参数扫描。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.maxwell_tools import _app, _get_model_state, _get_setup_names
from tools.utils import _ok, _err, ok_message


def _normalize_result_expression(result_expression: str) -> str:
    mapping = {
        "Torque": "Moving1.Torque",
        "Moving1.Torque": "Moving1.Torque",
        "CoreLoss": "CoreLoss",
        "OhmicLoss": "OhmicLoss",
    }
    return mapping.get(result_expression, result_expression)


def _collect_design_variable_names(app) -> set[str]:
    names = set()
    state = _get_model_state(app)
    geometry = state.get("geometry", {})
    names.update(geometry.get("geometry_design_variables", []))
    variable_manager = getattr(app, "variable_manager", None)
    for attr_name in ("variables", "updated"):
        values = getattr(variable_manager, attr_name, None)
        if isinstance(values, dict):
            names.update(values)
    return names


def _default_sweep_expressions(app) -> list[str]:
    state = _get_model_state(app)
    expressions = []
    if state.get("motion_configured"):
        expressions.append("Moving1.Torque")
    if state.get("winding_defined"):
        expressions.extend(["CoreLoss", "OhmicLoss"])
    if not expressions:
        raise RuntimeError("当前模型既没有运动语义也没有绕组语义，无法推断默认扫描结果表达式")
    return expressions


def _validate_sweep_expressions(app, setup_name: str, expressions: list[str]) -> list[str]:
    normalized = []
    state = _get_model_state(app)
    setup_info = state.get("setups", {}).get(setup_name, {})
    solver_type = setup_info.get("solver_type")
    for expr in expressions:
        normalized_expr = _normalize_result_expression(expr)
        if normalized_expr == "Moving1.Torque" and state.get("motion_configured") is False:
            raise RuntimeError("当前模型未配置旋转运动语义，不能将 Moving1.Torque 加入参数扫描")
        if normalized_expr in {"CoreLoss", "OhmicLoss"} and state.get("winding_defined") is False:
            raise RuntimeError("当前模型未配置绕组语义，不能将损耗表达式加入参数扫描")
        if normalized_expr == "Moving1.Torque" and solver_type == "EddyCurrent":
            raise RuntimeError("EddyCurrent 求解不应直接用于 Moving1.Torque 参数扫描")
        if normalized_expr not in normalized:
            normalized.append(normalized_expr)
    return normalized


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
        return _ok(ok_message(f"变量 '{name}' 已设置为 {value}{unit}", name=name, value=value, unit=unit))
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
    result_expressions: list[str] | None = None,
) -> dict:
    """
    创建单参数线性扫描。

    Args:
        param_name: 要扫描的参数名（需已通过 add_parametric_variable 定义）
        start: 扫描起始值
        stop: 扫描终止值
        step: 扫描步长
        setup_name: 关联的求解设置名称
        result_expressions: 要在扫描中计算的结果表达式列表；留空时根据模型状态自动推断
    """
    try:
        app = _app()
        if step == 0:
            return _err("参数扫描步长 step 不能为 0")
        if (stop - start) * step < 0:
            return _err("参数扫描步长方向错误：start/stop 与 step 的符号不一致")
        known_variables = _collect_design_variable_names(app)
        if known_variables and param_name not in known_variables:
            return _err(f"参数变量不存在: {param_name}；当前可用: {', '.join(sorted(known_variables))}")
        setup_names = _get_setup_names(app)
        if setup_names and setup_name not in setup_names:
            return _err(f"求解设置不存在: {setup_name}；当前可用: {', '.join(setup_names)}")
        expressions = _validate_sweep_expressions(
            app,
            setup_name,
            result_expressions or _default_sweep_expressions(app),
        )

        # 计算扫描点
        values = []
        current = start
        if step > 0:
            condition = lambda x: x <= stop + abs(step) * 0.001
        else:
            condition = lambda x: x >= stop - abs(step) * 0.001
        while condition(current):
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
        sweep.add_calculation(
            setup_name,
            "LastAdaptive",
            expressions,
        )
        sweep.update()
        state = _get_model_state(app)
        state.setdefault("parametric_sweeps", {})[sweep.name] = {
            "type": "1d",
            "setup_name": setup_name,
            "param_names": [param_name],
            "result_expressions": expressions,
            "analyzed": False,
        }

        return _ok({
            "sweep_name": sweep.name,
            "param": param_name,
            "num_points": len(values),
            "values": values,
            "result_expressions": expressions,
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
        state = _get_model_state(app)
        sweep_state = state.setdefault("parametric_sweeps", {})
        if sweep_name:
            if sweep_name in sweep_state:
                sweep_state[sweep_name]["analyzed"] = False
            app.parametrics[sweep_name].analyze()
            if sweep_name in sweep_state:
                sweep_state[sweep_name]["analyzed"] = True
        else:
            app.parametrics.analyze()
            for metadata in sweep_state.values():
                metadata["analyzed"] = True
        return _ok(ok_message(
            f"参数扫描 '{sweep_name or '全部'}' 已完成",
            sweep_name=sweep_name or "全部",
        ))
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
        query_expression = _normalize_result_expression(result_expression)
        state = _get_model_state(app)
        sweep_metadata = state.get("parametric_sweeps", {}).get(sweep_name) if sweep_name else None
        if sweep_metadata:
            if not sweep_metadata.get("analyzed"):
                return _err(f"参数扫描 '{sweep_name}' 尚未执行，请先调用 run_parametric_sweep")
            if param_name not in sweep_metadata.get("param_names", []):
                return _err(
                    f"参数扫描 '{sweep_name}' 不包含参数 '{param_name}'；"
                    f"当前参数: {', '.join(sweep_metadata.get('param_names', []))}"
                )
            if query_expression not in sweep_metadata.get("result_expressions", []):
                return _err(
                    f"参数扫描 '{sweep_name}' 未配置结果表达式 '{query_expression}'；"
                    f"当前表达式: {', '.join(sweep_metadata.get('result_expressions', []))}"
                )
        # 获取扫描数据
        data = app.post.get_solution_data(
            expressions=[query_expression],
            setup_sweep_name=f"Parametric : {sweep_name}" if sweep_name else "Parametric",
            primary_sweep_variable=param_name,
        )

        param_values = data.primary_sweep_values
        result_values = data.data_real(query_expression)

        # 找到最优点
        if result_values:
            max_idx = result_values.index(max(result_values))
            min_idx = result_values.index(min(result_values))
        else:
            max_idx = min_idx = 0

        return _ok({
            "param": param_name,
            "expression": result_expression,
            "queried_expression": query_expression,
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
    result_expressions: list[str] | None = None,
) -> dict:
    """
    创建二维参数扫描（笛卡尔积），适合绘制效率 MAP 等。

    Args:
        param1_name: 第一个参数名
        param1_values: 第一个参数取值列表
        param2_name: 第二个参数名
        param2_values: 第二个参数取值列表
        setup_name: 关联的求解设置
        result_expressions: 要在扫描中计算的结果表达式列表；留空时根据模型状态自动推断
    """
    try:
        app = _app()
        if not param1_values or not param2_values:
            return _err("二维参数扫描的两个参数取值列表都不能为空")
        known_variables = _collect_design_variable_names(app)
        missing_variables = [name for name in (param1_name, param2_name) if known_variables and name not in known_variables]
        if missing_variables:
            return _err(f"参数变量不存在: {', '.join(missing_variables)}；当前可用: {', '.join(sorted(known_variables))}")
        setup_names = _get_setup_names(app)
        if setup_names and setup_name not in setup_names:
            return _err(f"求解设置不存在: {setup_name}；当前可用: {', '.join(setup_names)}")
        expressions = _validate_sweep_expressions(
            app,
            setup_name,
            result_expressions or _default_sweep_expressions(app),
        )
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
        sweep.add_calculation(
            setup_name,
            "LastAdaptive",
            expressions,
        )
        sweep.update()
        state = _get_model_state(app)
        state.setdefault("parametric_sweeps", {})[sweep.name] = {
            "type": "2d",
            "setup_name": setup_name,
            "param_names": [param1_name, param2_name],
            "result_expressions": expressions,
            "analyzed": False,
        }

        return _ok({
            "sweep_name": sweep.name,
            "total_points": total,
            "param1": {"name": param1_name, "count": len(param1_values)},
            "param2": {"name": param2_name, "count": len(param2_values)},
            "result_expressions": expressions,
        })
    except Exception as e:
        return _err(str(e))
