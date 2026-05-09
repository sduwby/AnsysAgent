"""
PyDPF 工具：通过 Ansys PyDPF-Core 和 PyDPF-Post 对 MAPDL/Mechanical 仿真结果进行后处理。
支持：
  - PyDPF-Post：高层 API，加载 .rst 文件提取应力/温度/位移统计量
  - PyDPF-Core：底层 API，直接使用 dpf.Model、dpf.Operator 和插值算子，
                适用于子模型 DPF 插值（mapdl-dpf 工作流）和热分析 .rth 文件读取

参考工作流：
  - pyansys-workflows/mapdl-dpf/wf_mapdl-dpf.py（MapdlPool + DPF 插值）
  - pyansys-workflows/geometry-mechanical-dpf/wf_gmd_03_dpf.py（Mechanical 热分析后处理）

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

from tools.utils import _ok, _err, ensure_parent_dir

_dpf_solution = None   # 全局 DPF-Post 仿真结果对象
_dpf_model = None      # 全局 DPF-Core Model 对象（dpf.Model）
_dpf_server = None     # 全局 DPF 服务器连接


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


# ===========================================================================
# DPF-Core 底层工具（用于 MapdlPool 子模型工作流、热分析 .rth 读取）
# ===========================================================================

# ---------------------------------------------------------------------------
# 工具：connect_dpf_server - 连接到 DPF 服务器
# ---------------------------------------------------------------------------

def connect_dpf_server(
    port: int | None = None,
    local: bool = True,
) -> dict:
    """
    连接或启动 DPF 服务器（dpf.core）。
    - local=True：在本机启动本地 DPF Server（无需预先启动）
    - local=False：连接到远程 DPF Server（需提供 port）

    参考工作流：mapdl-dpf/wf_mapdl-dpf.py

    Args:
        port: DPF Server 端口号；local=False 时必填
        local: True 启动本地服务，False 连接远程服务
    """
    global _dpf_server
    try:
        from ansys.dpf import core as dpf

        if local:
            _dpf_server = dpf.server.start_local_server()
            return _ok(ok_message("已启动本地 DPF Server", local=True))
        else:
            if port is None:
                return _err("remote 模式必须提供 port 参数")
            _dpf_server = dpf.server.connect_to_server(port=port)
            return _ok(ok_message(f"已连接到远程 DPF Server（port={port}）", port=port))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：load_dpf_core_model - 使用 dpf.core.Model 加载结果文件
# ---------------------------------------------------------------------------

def load_dpf_core_model(
    result_file_path: str,
    domain_files: list[str] | None = None,
) -> dict:
    """
    使用 DPF-Core 底层 API 加载仿真结果文件（.rst 或 .rth）。
    支持多域（多核并行 MAPDL 结果，domain_files 列表）和单文件两种模式。

    参考工作流：
      - mapdl-dpf/wf_mapdl-dpf.py（多域 DataSources）
      - geometry-mechanical-dpf/wf_gmd_03_dpf.py（直接 dpf.Model）

    Args:
        result_file_path: 主结果文件路径（.rst 或 .rth）
        domain_files: 多核并行结果文件列表（如 file0.rst, file1.rst, ...）；
                      None 则以单文件模式加载
    """
    global _dpf_model
    try:
        from ansys.dpf import core as dpf

        if domain_files is not None:
            # 多域模式（MapdlPool 并行结果）
            data_sources = dpf.DataSources()
            for i, fpath in enumerate(domain_files):
                data_sources.set_domain_result_file_path(
                    path=fpath,
                    key="rst",
                    domain_id=i,
                )
            _dpf_model = dpf.Model(data_sources)
        else:
            _dpf_model = dpf.Model(result_file_path)

        info = str(_dpf_model)
        return _ok(ok_message(
            f"DPF Model 已加载：{result_file_path}",
            result_file=result_file_path,
            multi_domain=(domain_files is not None),
            domain_count=len(domain_files) if domain_files else 1,
            model_info=info[:500],
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_dpf_core_temperature - 通过 dpf.core.Model 提取热分析温度场
# ---------------------------------------------------------------------------

def get_dpf_core_temperature(
    result_file_path: str | None = None,
    time_step: str = "last",
) -> dict:
    """
    通过 DPF-Core 提取热分析温度场（支持 .rth 文件）。
    适用于 Mechanical 稳态/瞬态热分析结果后处理。

    参考工作流：geometry-mechanical-dpf/wf_gmd_03_dpf.py

    Args:
        result_file_path: .rth 文件路径；None 则使用已加载的 _dpf_model
        time_step: "last"（最终时间步）或整数字符串（如 "3"）
    """
    try:
        from ansys.dpf import core as dpf

        if result_file_path is not None:
            model = dpf.Model(result_file_path)
        elif _dpf_model is not None:
            model = _dpf_model
        else:
            return _err("未加载结果文件，请先调用 load_dpf_core_model 或提供 result_file_path")

        temp_op = model.results.temperature
        if time_step == "last":
            temp_fc = temp_op.on_last_time_freq.eval()
        else:
            temp_fc = temp_op.on_time_scoping([int(time_step)]).eval()

        field = temp_fc[0]
        data = list(field.data)

        return _ok({
            "result_file": result_file_path,
            "time_step": time_step,
            "max_temp_K": round(max(data), 3) if data else None,
            "min_temp_K": round(min(data), 3) if data else None,
            "avg_temp_K": round(sum(data) / len(data), 3) if data else None,
            "num_nodes": len(data),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：find_result_files - 递归搜索结果文件
# ---------------------------------------------------------------------------

def find_result_files(
    directory: str,
    extension: str = ".rth",
) -> dict:
    """
    在指定目录中递归搜索指定扩展名的仿真结果文件（.rst / .rth 等）。
    适用于 Mechanical 项目目录下自动定位结果文件。

    参考工作流：geometry-mechanical-dpf/wf_gmd_03_dpf.py（find_files 函数）

    Args:
        directory: 搜索根目录
        extension: 文件扩展名，如 ".rth"（热分析）或 ".rst"（结构分析）
    """
    try:
        import os
        found_files: list[str] = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(extension):
                    found_files.append(os.path.join(root, file))

        return _ok({
            "directory": directory,
            "extension": extension,
            "count": len(found_files),
            "files": found_files,
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：create_dpf_interpolator - 创建 DPF 位移插值算子（子模型工作流）
# ---------------------------------------------------------------------------

def create_dpf_interpolator(
    global_result_files: list[str],
    local_boundary_node_ids: list[int],
    local_boundary_coordinates: list[list[float]],
) -> dict:
    """
    创建 DPF 插值算子（on_coordinates），用于子模型工作流：
    从全局模型结果插值计算局部模型边界节点的位移。

    参考工作流：mapdl-dpf/wf_mapdl-dpf.py（disp_interpolator + initialize_dpf_interpolator）

    Args:
        global_result_files: 全局模型结果文件路径列表（支持多核并行）
        local_boundary_node_ids: 局部模型边界节点 ID 列表
        local_boundary_coordinates: 与节点 ID 对应的坐标列表，每项 [x, y, z]（单位：m）

    Returns:
        成功时返回 interpolator_ready=True，
        此后可调用 interpolate_boundary_displacements 执行插值
    """
    try:
        from ansys.dpf import core as dpf

        # 构建多域 DataSources
        data_sources = dpf.DataSources()
        for i, fpath in enumerate(global_result_files):
            data_sources.set_domain_result_file_path(
                path=fpath,
                key="rst",
                domain_id=i,
            )

        # 创建全局模型
        global_model = dpf.Model(data_sources)

        # 创建 DPF Field 存储边界坐标
        boundary_coords_field = dpf.fields_factory.create_3d_vector_field(
            num_entities=len(local_boundary_node_ids),
            location="Nodal",
        )
        for nid, coords in zip(local_boundary_node_ids, local_boundary_coordinates):
            boundary_coords_field.append(coords, nid)

        # 创建算子
        disp_op = dpf.operators.result.displacement()
        disp_op.inputs.data_sources.connect(data_sources)

        interp_op = dpf.operators.mapping.on_coordinates()
        my_mesh = global_model.metadata.meshed_region
        interp_op.inputs.coordinates.connect(boundary_coords_field)
        interp_op.inputs.mesh.connect(my_mesh)

        # 将算子和相关对象缓存到模块变量供后续调用
        import types
        _dpf_cache = getattr(
            __import__(__name__), "_dpf_interpolator_cache", None
        )
        if _dpf_cache is None:
            import sys
            mod = sys.modules[__name__]
            mod._dpf_interpolator_cache = {}

        sys_mod = __import__(__name__)
        sys_mod._dpf_interpolator_cache = {
            "global_model": global_model,
            "disp_op": disp_op,
            "interp_op": interp_op,
            "node_ids": local_boundary_node_ids,
        }

        return _ok(ok_message(
            f"DPF 插值算子已创建：全局结果={len(global_result_files)} 个文件，"
            f"边界节点数={len(local_boundary_node_ids)}",
            interpolator_ready=True,
            global_file_count=len(global_result_files),
            boundary_node_count=len(local_boundary_node_ids),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：interpolate_boundary_displacements - 插值获取边界节点位移
# ---------------------------------------------------------------------------

def interpolate_boundary_displacements(timestep: int = 1) -> dict:
    """
    使用已创建的 DPF 插值算子，从全局模型结果中插值计算
    局部模型边界节点在指定时间步的位移。

    必须先调用 create_dpf_interpolator 初始化算子。

    参考工作流：mapdl-dpf/wf_mapdl-dpf.py（interpolate_data）

    Args:
        timestep: 全局模型结果时间步编号（从 1 开始）

    Returns:
        包含各边界节点位移 {node_id: [ux, uy, uz]} 的字典
    """
    try:
        import sys
        mod = sys.modules[__name__]
        cache = getattr(mod, "_dpf_interpolator_cache", None)
        if cache is None:
            return _err("未找到 DPF 插值算子，请先调用 create_dpf_interpolator")

        disp_op = cache["disp_op"]
        interp_op = cache["interp_op"]
        node_ids = cache["node_ids"]

        # 指定时间步
        disp_op.inputs.time_scoping.connect([timestep])
        global_disp_fc = disp_op.outputs.fields_container.get_data()
        interp_op.inputs.fields_container.connect(global_disp_fc)
        local_disp = interp_op.outputs.fields_container.get_data()[0]

        raw_data = list(local_disp.data)
        result_map: dict[int, list[float]] = {}
        for i, nid in enumerate(node_ids):
            ux = raw_data[i * 3]
            uy = raw_data[i * 3 + 1]
            uz = raw_data[i * 3 + 2]
            result_map[nid] = [round(ux, 8), round(uy, 8), round(uz, 8)]

        return _ok({
            "timestep": timestep,
            "node_count": len(node_ids),
            "displacements": result_map,
        })
    except Exception as e:
        return _err(str(e))
