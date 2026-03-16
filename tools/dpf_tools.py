"""
PyDPF-Post 工具：通过 Ansys PyDPF-Post 对 MAPDL/Mechanical 仿真结果进行后处理。
支持加载 .rst 结果文件，提取应力、温度、位移等场量，并导出为 CSV 供进一步分析。
每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, ensure_parent_dir

_dpf_solution = None  # 全局 DPF 仿真结果对象


# ---------------------------------------------------------------------------
# 工具：load_dpf_result - 加载仿真结果文件
# ---------------------------------------------------------------------------

def load_dpf_result(result_file_path: str) -> dict:
    """
    加载 MAPDL 或 Mechanical 仿真结果文件（.rst），初始化 DPF 后处理会话。

    Args:
        result_file_path: 结果文件绝对路径（.rst 格式）
    """
    global _dpf_solution
    try:
        from ansys.dpf import post
        _dpf_solution = post.load_solution(result_file_path)
        mesh = _dpf_solution.mesh
        return _ok({
            "file": result_file_path,
            "num_nodes": mesh.nodes.n_nodes,
            "num_elements": mesh.elements.n_elements,
            "result_sets": list(_dpf_solution.time_freq_support.time_frequencies.data
                                if hasattr(_dpf_solution, "time_freq_support") else []),
        })
    except Exception as e:
        return _err(str(e))


def _sol():
    """返回当前加载的 DPF 仿真结果，未加载时抛出异常。"""
    if _dpf_solution is None:
        raise RuntimeError("未加载结果文件，请先调用 load_dpf_result。")
    return _dpf_solution


# ---------------------------------------------------------------------------
# 工具：get_dpf_stress - 提取等效应力场
# ---------------------------------------------------------------------------

def get_dpf_stress(
    result_set: int = 1,
    component: str = "EQV",
    location: str = "Nodal",
) -> dict:
    """
    从已加载的 DPF 结果中提取应力场（von Mises 或单轴分量）。

    Args:
        result_set: 时间步/载荷步编号，从 1 开始
        component: "EQV"（等效/von Mises）/ "X"/"Y"/"Z"/"XY"/"YZ"/"XZ"
        location: "Nodal"（节点）或 "Elemental"（单元中心）
    """
    try:
        sol = _sol()
        comp_map = {
            "EQV": "von_mises_stress",
            "X": "stress_X", "Y": "stress_Y", "Z": "stress_Z",
            "XY": "stress_XY", "YZ": "stress_YZ", "XZ": "stress_XZ",
        }
        if component.upper() not in comp_map:
            return _err(f"未知分量：{component}，可选：{list(comp_map.keys())}")

        stress_field = sol.stress(set_number=result_set, location=location.lower())
        if component.upper() == "EQV":
            data = stress_field.von_mises_stress.get_data_at_field(0)
        else:
            data = getattr(stress_field, comp_map[component.upper()]).get_data_at_field(0)

        data_MPa = [v / 1e6 for v in data] if data else []
        return _ok({
            "component": component.upper(),
            "location": location,
            "result_set": result_set,
            "max_MPa": round(max(data_MPa), 3) if data_MPa else None,
            "min_MPa": round(min(data_MPa), 3) if data_MPa else None,
            "avg_MPa": round(sum(data_MPa) / len(data_MPa), 3) if data_MPa else None,
            "num_values": len(data_MPa),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_dpf_temperature - 提取温度场
# ---------------------------------------------------------------------------

def get_dpf_temperature(result_set: int = 1) -> dict:
    """
    从 DPF 结果中提取温度场分布（适用于热力耦合分析结果）。

    Args:
        result_set: 时间步/载荷步编号，从 1 开始
    """
    try:
        sol = _sol()
        temp_field = sol.temperature(set_number=result_set)
        data = temp_field.get_data_at_field(0)

        return _ok({
            "result_set": result_set,
            "max_temp_C": round(max(data), 2) if data else None,
            "min_temp_C": round(min(data), 2) if data else None,
            "avg_temp_C": round(sum(data) / len(data), 2) if data else None,
            "num_nodes": len(data),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_dpf_displacement - 提取位移/变形场
# ---------------------------------------------------------------------------

def get_dpf_displacement(
    result_set: int = 1,
    component: str = "NORM",
) -> dict:
    """
    从 DPF 结果中提取位移/变形场。

    Args:
        result_set: 时间步编号（从 1 开始）
        component: "NORM"（合位移模）/ "X"/"Y"/"Z"（轴向分量）
    """
    try:
        sol = _sol()
        disp_field = sol.displacement(set_number=result_set)

        comp = component.upper()
        if comp == "NORM":
            data = disp_field.norm.get_data_at_field(0)
        elif comp in ("X", "Y", "Z"):
            idx = {"X": 0, "Y": 1, "Z": 2}[comp]
            raw = disp_field.get_data_at_field(0)
            # 3D 向量场：每 3 个值为一个节点 [ux, uy, uz]
            data = [raw[i * 3 + idx] for i in range(len(raw) // 3)]
        else:
            return _err(f"未知分量：{component}，可选：NORM / X / Y / Z")

        data_mm = [v * 1000 for v in data]  # 转换为 mm
        return _ok({
            "component": comp,
            "result_set": result_set,
            "max_mm": round(max(data_mm), 4) if data_mm else None,
            "min_mm": round(min(data_mm), 4) if data_mm else None,
            "avg_mm": round(sum(data_mm) / len(data_mm), 4) if data_mm else None,
            "num_nodes": len(data_mm),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_dpf_field_statistics - 获取任意场量统计汇总
# ---------------------------------------------------------------------------

def get_dpf_field_statistics(
    field_name: str,
    result_set: int = 1,
) -> dict:
    """
    获取指定场量（应力、应变、温度等）在指定时间步的统计摘要。

    Args:
        field_name: 场量名称，如 "stress"、"temperature"、"displacement"、"elastic_strain"
        result_set: 时间步编号
    """
    try:
        sol = _sol()
        field_fn_map = {
            "stress": lambda: sol.stress(set_number=result_set),
            "temperature": lambda: sol.temperature(set_number=result_set),
            "displacement": lambda: sol.displacement(set_number=result_set),
            "elastic_strain": lambda: sol.elastic_strain(set_number=result_set),
        }
        fn = field_fn_map.get(field_name.lower())
        if fn is None:
            return _err(f"未知场量：{field_name}，可选：{list(field_fn_map.keys())}")

        field = fn()
        data = field.get_data_at_field(0)

        return _ok({
            "field_name": field_name,
            "result_set": result_set,
            "max": round(float(max(data)), 6) if data else None,
            "min": round(float(min(data)), 6) if data else None,
            "avg": round(float(sum(data) / len(data)), 6) if data else None,
            "num_values": len(data),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_dpf_results_to_csv - 导出场量数据到 CSV
# ---------------------------------------------------------------------------

def export_dpf_results_to_csv(
    output_path: str,
    field_name: str = "stress",
    result_set: int = 1,
) -> dict:
    """
    将指定场量数据导出为 CSV 文件，便于在 Excel/Python 中进一步处理或绘图。

    Args:
        output_path: 输出 CSV 文件路径（含文件名）
        field_name: 场量名称，如 "stress"、"temperature"、"displacement"
        result_set: 时间步编号
    """
    try:
        import csv as csv_mod
        sol = _sol()
        ensure_parent_dir(output_path)

        # 获取节点坐标
        mesh = sol.mesh
        node_coords = mesh.nodes.coordinates_field.get_data_at_field(0)

        # 获取场量数据
        field_fn_map = {
            "stress": lambda: sol.stress(set_number=result_set).von_mises_stress.get_data_at_field(0),
            "temperature": lambda: sol.temperature(set_number=result_set).get_data_at_field(0),
            "displacement": lambda: sol.displacement(set_number=result_set).norm.get_data_at_field(0),
        }
        fn = field_fn_map.get(field_name.lower())
        if fn is None:
            return _err(f"未知场量：{field_name}，支持：{list(field_fn_map.keys())}")

        values = fn()
        n = len(values)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv_mod.writer(f)
            writer.writerow(["node_index", "x_m", "y_m", "z_m", field_name])
            for i in range(n):
                x = node_coords[i * 3] if i * 3 < len(node_coords) else 0
                y = node_coords[i * 3 + 1] if i * 3 + 1 < len(node_coords) else 0
                z = node_coords[i * 3 + 2] if i * 3 + 2 < len(node_coords) else 0
                writer.writerow([i + 1, round(x, 6), round(y, 6), round(z, 6), round(values[i], 6)])

        return _ok({
            "output_path": output_path,
            "field_name": field_name,
            "result_set": result_set,
            "num_rows": n,
        })
    except Exception as e:
        return _err(str(e))
