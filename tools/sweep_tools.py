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


# ---------------------------------------------------------------------------
# 工具：create_lhs_doe - 拉丁超立方试验设计（纯 Python，无第三方 DOE 库）
# ---------------------------------------------------------------------------

def create_lhs_doe(
    param_bounds: dict[str, list[float]],
    n_samples: int = 20,
    setup_name: str = "Setup1",
    result_expressions: list[str] | None = None,
    seed: int = 42,
) -> dict:
    """
    使用拉丁超立方采样（LHS）生成试验设计点，并在 PyAEDT 中创建参数扫描。

    Args:
        param_bounds: 参数名 -> [最小值, 最大值] 的字典，例如 {"SlotWidth": [2.0, 5.0], "AirGap": [0.5, 1.5]}
        n_samples: 采样点数，默认 20
        setup_name: 关联的求解设置名称，默认 "Setup1"
        result_expressions: 要计算的结果表达式列表；留空时自动推断
        seed: 随机种子，保证可重现性，默认 42
    """
    import random
    import math

    try:
        if not param_bounds:
            return _err("param_bounds 不能为空")
        if n_samples < 2:
            return _err("n_samples 必须 >= 2")
        for pname, bounds in param_bounds.items():
            if len(bounds) != 2 or bounds[0] >= bounds[1]:
                return _err(f"参数 '{pname}' 的 bounds 格式错误：应为 [min, max]，且 min < max")

        app = _app()
        known_variables = _collect_design_variable_names(app)
        if known_variables:
            missing = [p for p in param_bounds if p not in known_variables]
            if missing:
                return _err(f"参数变量不存在: {', '.join(missing)}；当前可用: {', '.join(sorted(known_variables))}")

        setup_names = _get_setup_names(app)
        if setup_names and setup_name not in setup_names:
            return _err(f"求解设置不存在: {setup_name}；当前可用: {', '.join(setup_names)}")

        expressions = _validate_sweep_expressions(
            app,
            setup_name,
            result_expressions or _default_sweep_expressions(app),
        )

        # ---------- 纯 Python LHS 实现 ----------
        rng = random.Random(seed)
        param_names = list(param_bounds.keys())
        n_params = len(param_names)

        # 生成每个参数的分层随机排列
        samples: list[list[float]] = []
        for _ in range(n_params):
            intervals = list(range(n_samples))
            rng.shuffle(intervals)
            col = [(i + rng.random()) / n_samples for i in intervals]
            samples.append(col)

        # 将 [0,1] 映射到实际 bounds
        doe_points: list[dict[str, float]] = []
        for i in range(n_samples):
            point: dict[str, float] = {}
            for j, pname in enumerate(param_names):
                lo, hi = param_bounds[pname]
                point[pname] = lo + samples[j][i] * (hi - lo)
            doe_points.append(point)

        # 汇总每个参数的值列表（供 PyAEDT 使用）
        param_value_lists: dict[str, list[float]] = {
            pname: [doe_points[i][pname] for i in range(n_samples)]
            for pname in param_names
        }

        # 创建第一个参数的扫描
        first_param = param_names[0]
        sweep = app.parametrics.add(
            variable=first_param,
            values_list=param_value_lists[first_param],
            variation_type="SingleValues",
        )
        # 添加其余参数
        for pname in param_names[1:]:
            sweep.add_variation(
                variable=pname,
                values_list=param_value_lists[pname],
                variation_type="SingleValues",
            )
        sweep.add_calculation(setup_name, "LastAdaptive", expressions)
        sweep.update()

        # 更新模型状态
        state = _get_model_state(app)
        state.setdefault("parametric_sweeps", {})[sweep.name] = {
            "type": "lhs",
            "setup_name": setup_name,
            "param_names": param_names,
            "param_bounds": param_bounds,
            "n_samples": n_samples,
            "doe_points": doe_points,
            "result_expressions": expressions,
            "analyzed": False,
        }

        return _ok({
            "sweep_name": sweep.name,
            "n_samples": n_samples,
            "n_params": n_params,
            "param_names": param_names,
            "doe_points": doe_points,
            "result_expressions": expressions,
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：build_rsm - 响应面模型（RSM），基于扫描结果拟合多项式代理模型
# ---------------------------------------------------------------------------

def build_rsm(
    sweep_name: str,
    result_expression: str = "Torque",
    poly_degree: int = 2,
) -> dict:
    """
    基于已执行的参数扫描结果构建响应面模型（RSM）。
    支持单参数（1D）和双参数（2D）扫描；多于两个参数时返回错误提示。

    Args:
        sweep_name: 已分析完成的参数扫描名称
        result_expression: 要拟合的结果表达式，默认 "Torque"
        poly_degree: 多项式阶数，默认 2（二次响应面）
    """
    try:
        import numpy as np

        app = _app()
        state = _get_model_state(app)
        sweep_meta = state.get("parametric_sweeps", {}).get(sweep_name)
        if not sweep_meta:
            return _err(f"未找到扫描 '{sweep_name}'，请先执行 create_parametric_sweep 或 create_lhs_doe")
        if not sweep_meta.get("analyzed"):
            return _err(f"扫描 '{sweep_name}' 尚未执行，请先调用 run_parametric_sweep")

        param_names: list[str] = sweep_meta.get("param_names", [])
        n_params = len(param_names)
        if n_params == 0:
            return _err("扫描元数据中未找到参数名称")
        if n_params > 2:
            return _err(f"build_rsm 目前仅支持 1~2 个参数，当前扫描含 {n_params} 个参数")

        query_expression = _normalize_result_expression(result_expression)
        setup_name = sweep_meta.get("setup_name", "Setup1")

        if n_params == 1:
            # -------- 1D 响应面 --------
            param_name = param_names[0]
            data = app.post.get_solution_data(
                expressions=[query_expression],
                setup_sweep_name=f"Parametric : {sweep_name}",
                primary_sweep_variable=param_name,
            )
            x = np.array(data.primary_sweep_values, dtype=float)
            y = np.array(data.data_real(query_expression), dtype=float)
            if len(x) < poly_degree + 1:
                return _err(f"数据点数 ({len(x)}) 不足以拟合 {poly_degree} 阶多项式，需至少 {poly_degree + 1} 个点")

            coeffs = np.polyfit(x, y, poly_degree)
            y_pred = np.polyval(coeffs, x)
            ss_res = float(np.sum((y - y_pred) ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

            # 最优点（多项式极值）
            deriv_coeffs = np.polyder(coeffs)
            roots = np.roots(deriv_coeffs)
            real_roots = roots[np.isreal(roots)].real
            bounds = sweep_meta.get("param_bounds", {}).get(param_name)
            if bounds:
                real_roots = real_roots[(real_roots >= bounds[0]) & (real_roots <= bounds[1])]
            candidate_x = np.concatenate([real_roots, x])
            candidate_y = np.polyval(coeffs, candidate_x)
            best_idx = int(np.argmax(candidate_y))

            return _ok({
                "type": "rsm_1d",
                "sweep_name": sweep_name,
                "param": param_name,
                "expression": result_expression,
                "poly_degree": poly_degree,
                "coefficients": coeffs.tolist(),
                "r_squared": round(r2, 6),
                "optimal_point": {
                    "param_value": round(float(candidate_x[best_idx]), 6),
                    "predicted_result": round(float(candidate_y[best_idx]), 6),
                },
                "data_points": int(len(x)),
            })

        else:
            # -------- 2D 响应面（二变量多项式，阶数固定为 poly_degree=2 的完全二次型） --------
            param1, param2 = param_names[0], param_names[1]

            # 获取扫描数据：遍历两个参数的组合
            data1 = app.post.get_solution_data(
                expressions=[query_expression],
                setup_sweep_name=f"Parametric : {sweep_name}",
                primary_sweep_variable=param1,
            )
            x1_vals = np.array(data1.primary_sweep_values, dtype=float)

            doe_points: list[dict] = sweep_meta.get("doe_points", [])
            if not doe_points:
                return _err("扫描元数据中未找到 doe_points，无法构建 2D RSM；请使用 create_lhs_doe 生成含 doe_points 的扫描")

            n = len(doe_points)
            X1 = np.array([pt[param1] for pt in doe_points], dtype=float)
            X2 = np.array([pt[param2] for pt in doe_points], dtype=float)
            Y = np.array(data1.data_real(query_expression), dtype=float)
            if len(Y) != n:
                Y = Y[:n]

            # 完全二次型特征矩阵 [1, x1, x2, x1², x1*x2, x2²]
            A = np.column_stack([
                np.ones(n),
                X1, X2,
                X1 ** 2, X1 * X2, X2 ** 2,
            ])
            coeffs, _, _, _ = np.linalg.lstsq(A, Y, rcond=None)
            Y_pred = A @ coeffs
            ss_res = float(np.sum((Y - Y_pred) ** 2))
            ss_tot = float(np.sum((Y - Y.mean()) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

            # 近似最优点（从 doe_points 中选取预测值最大的点）
            best_idx = int(np.argmax(Y_pred))

            return _ok({
                "type": "rsm_2d",
                "sweep_name": sweep_name,
                "params": [param1, param2],
                "expression": result_expression,
                "poly_degree": 2,
                "coefficients": {
                    "intercept": round(float(coeffs[0]), 6),
                    param1: round(float(coeffs[1]), 6),
                    param2: round(float(coeffs[2]), 6),
                    f"{param1}^2": round(float(coeffs[3]), 6),
                    f"{param1}*{param2}": round(float(coeffs[4]), 6),
                    f"{param2}^2": round(float(coeffs[5]), 6),
                },
                "r_squared": round(r2, 6),
                "optimal_point": {
                    param1: round(float(X1[best_idx]), 6),
                    param2: round(float(X2[best_idx]), 6),
                    "predicted_result": round(float(Y_pred[best_idx]), 6),
                },
                "data_points": n,
            })

    except Exception as e:
        return _err(str(e))
