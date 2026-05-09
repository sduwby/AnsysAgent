"""
PyPrime 独立网格工具：通过 ansys-meshing-prime 驱动 Ansys Prime 网格服务。
支持完整网格化工作流：启动 Prime 会话、导入 CAD 文件（FMD/PMDB 等）、
Scaffold 拓扑处理、曲面网格生成、体网格生成、网格导出（CDB/MSH）及会话关闭。

本模块与 AnsysAgent 已有的 mesh_tools.py（PyAEDT Maxwell 网格操作）互补：
- mesh_tools.py   → AEDT Maxwell/Icepak 内部网格控制（长度细化、集肤深度等）
- prime_mesh_tools.py → 独立 Prime 会话，处理来自 PyAnsys Geometry 的 CAD 文件

参考工作流：
  - pyansys-workflows/geometry-mesh/wf_gm_02_mesh.py
  - pyansys-workflows/geometry-mesh-fluent/wf_gmf_02_fluent_meshing.py
"""

from __future__ import annotations

from tools.utils import _ok, _err, ok_message

_prime_client = None  # 全局 Prime 客户端实例
_prime_model = None   # 全局 Prime Model 实例


def _client():
    if _prime_client is None:
        raise RuntimeError("未连接到 Prime，请先调用 connect_prime。")
    return _prime_client


def _model():
    if _prime_model is None:
        raise RuntimeError("Prime Model 未初始化，请先调用 connect_prime。")
    return _prime_model


# ---------------------------------------------------------------------------
# 工具：connect_prime - 启动 Prime 网格会话
# ---------------------------------------------------------------------------

def connect_prime(timeout: int = 120) -> dict:
    """
    启动本地 Ansys Prime 网格服务并获取 Model 对象。

    Args:
        timeout: 等待服务启动的超时时间（秒），默认 120
    """
    global _prime_client, _prime_model
    try:
        from ansys.meshing import prime

        _prime_client = prime.launch_prime(timeout=timeout)
        _prime_model = _prime_client.model
        return _ok(ok_message(
            f"已启动 Prime 网格服务（timeout={timeout}s）",
            timeout=timeout,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_cad_to_prime - 导入 CAD 文件到 Prime
# ---------------------------------------------------------------------------

def import_cad_to_prime(cad_file_path: str) -> dict:
    """
    将 CAD 文件（FMD、PMDB、SCDOCX、STEP 等）导入到 Prime 模型中。

    Args:
        cad_file_path: CAD 文件的完整路径
    """
    try:
        from ansys.meshing import prime

        model = _model()
        file_io = prime.FileIO(model)
        file_io.import_cad(
            file_name=cad_file_path,
            params=prime.ImportCadParams(model=model),
        )

        # 获取导入后零件摘要
        parts = model.parts
        part_summaries = []
        for part in parts:
            summary = part.get_summary(
                prime.PartSummaryParams(model, print_mesh=False)
            )
            part_summaries.append({
                "part_name": part.name,
                "part_id": part.id,
                "summary": str(summary),
            })

        return _ok(ok_message(
            f"已导入 CAD 文件：{cad_file_path}（共 {len(parts)} 个零件）",
            cad_file_path=cad_file_path,
            part_count=len(parts),
            parts=part_summaries,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：scaffold_prime_part - 拓扑 Scaffold 处理
# ---------------------------------------------------------------------------

def scaffold_prime_part(
    part_name: str | None = None,
    element_size: float = 0.5,
    absolute_dist_tol_ratio: float = 0.1,
) -> dict:
    """
    对指定零件（或所有零件）执行 Scaffold 拓扑处理，
    用于修复几何间隙、相交面等问题，为表面网格做准备。

    Args:
        part_name: 目标零件名称；None 则处理模型中第一个零件
        element_size: 目标单元尺寸（模型长度单位），Scaffold 连接公差基于此值
        absolute_dist_tol_ratio: 绝对距离公差 = element_size × 此比例，默认 0.1
    """
    try:
        from ansys.meshing import prime

        model = _model()
        if part_name is not None:
            part = model.get_part_by_name(part_name)
            if part is None:
                return _err(f"未找到零件：{part_name}")
        else:
            if not model.parts:
                return _err("Prime 模型中没有零件，请先调用 import_cad_to_prime")
            part = model.parts[0]

        params = prime.ScaffolderParams(
            model,
            absolute_dist_tol=absolute_dist_tol_ratio * element_size,
            intersection_control_mask=prime.IntersectionMask.FACEFACEANDEDGEEDGE,
            constant_mesh_size=element_size,
        )

        faces = part.get_topo_faces()
        beams: list = []
        result = prime.Scaffolder(model, part.id).scaffold_topo_faces_and_beams(
            topo_faces=faces,
            topo_beams=beams,
            params=params,
        )

        return _ok(ok_message(
            f"Scaffold 完成：零件='{part.name}'，单元尺寸={element_size}",
            part_name=part.name,
            element_size=element_size,
            result_summary=str(result),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：generate_surface_mesh - 生成曲面网格
# ---------------------------------------------------------------------------

def generate_surface_mesh(
    part_name: str | None = None,
    element_size: float = 0.5,
    generate_quads: bool = True,
    size_field_type: str = "constant",
) -> dict:
    """
    在指定零件的拓扑面上生成曲面网格（Surfer 算法）。

    Args:
        part_name: 目标零件名称；None 则使用第一个零件
        element_size: 单元尺寸（模型长度单位）
        generate_quads: True 生成四边形主导网格，False 生成三角形网格
        size_field_type: 尺寸场类型，"constant"（均匀）或 "adaptive"（自适应）
    """
    try:
        from ansys.meshing import prime

        model = _model()
        if part_name is not None:
            part = model.get_part_by_name(part_name)
            if part is None:
                return _err(f"未找到零件：{part_name}")
        else:
            if not model.parts:
                return _err("Prime 模型中没有零件")
            part = model.parts[0]

        size_field_map = {
            "constant": prime.SizeFieldType.CONSTANT,
            "adaptive": prime.SizeFieldType.GEOMETRIC,
        }
        sf_type = size_field_map.get(size_field_type.lower(), prime.SizeFieldType.CONSTANT)

        surfer_params = prime.SurferParams(
            model=model,
            size_field_type=sf_type,
            constant_size=element_size,
            generate_quads=generate_quads,
        )

        faces = part.get_topo_faces()
        result = prime.Surfer(model).mesh_topo_faces(
            part.id,
            topo_faces=faces,
            params=surfer_params,
        )

        return _ok(ok_message(
            f"曲面网格生成完成：零件='{part.name}'，尺寸={element_size}，"
            f"四边形={'是' if generate_quads else '否'}",
            part_name=part.name,
            element_size=element_size,
            generate_quads=generate_quads,
            result_summary=str(result),
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：export_prime_mesh - 导出网格文件
# ---------------------------------------------------------------------------

def export_prime_mesh(
    output_path: str,
    export_format: str = "cdb",
) -> dict:
    """
    将 Prime 中生成的网格导出为下游仿真工具所需的格式。

    支持格式：
    - "cdb"     → MAPDL CDB 格式（供 PyMAPDL / MAPDL 使用）
    - "msh"     → Fluent MSH 格式（供 PyFluent 使用，推荐 .msh.h5）
    - "msh_h5"  → Fluent HDF5 MSH 格式（.msh.h5，现代 Fluent 首选）

    Args:
        output_path: 输出文件路径（含文件名，无需带扩展名）
        export_format: 导出格式，"cdb"、"msh" 或 "msh_h5"
    """
    try:
        from pathlib import Path
        from ansys.meshing import prime

        model = _model()
        file_io = prime.FileIO(model)

        ext_map = {"cdb": ".cdb", "msh": ".msh", "msh_h5": ".msh.h5"}
        fmt_key = export_format.lower()
        if fmt_key not in ext_map:
            return _err(f"不支持的格式：{export_format}，可用：{list(ext_map.keys())}")

        if not output_path.endswith(ext_map[fmt_key]):
            output_path = output_path + ext_map[fmt_key]

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if fmt_key == "cdb":
            file_io.export_mapdl_cdb(
                output_path,
                params=prime.ExportMapdlCdbParams(model),
            )
        else:
            # Fluent MSH / MSH.H5
            file_io.export_fluent_meshing_meshes(
                file_name=output_path,
                export_fluent_meshing_mesh_params=prime.ExportFluentMeshingMeshParams(model),
            )

        return _ok(ok_message(
            f"网格已导出：{output_path}（格式={export_format}）",
            output_path=output_path,
            export_format=export_format,
        ))
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：get_prime_part_summary - 获取零件网格摘要
# ---------------------------------------------------------------------------

def get_prime_part_summary(part_name: str | None = None) -> dict:
    """
    获取 Prime 模型中指定零件的网格摘要（节点数、单元数、质量指标等）。

    Args:
        part_name: 目标零件名称；None 则使用第一个零件
    """
    try:
        from ansys.meshing import prime

        model = _model()
        if part_name is not None:
            part = model.get_part_by_name(part_name)
            if part is None:
                return _err(f"未找到零件：{part_name}")
        else:
            if not model.parts:
                return _err("Prime 模型中没有零件")
            part = model.parts[0]

        summary = part.get_summary(prime.PartSummaryParams(model, print_mesh=True))
        return _ok({
            "part_name": part.name,
            "part_id": part.id,
            "summary": str(summary),
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：close_prime - 关闭 Prime 会话
# ---------------------------------------------------------------------------

def close_prime() -> dict:
    """
    关闭 Prime 网格服务会话并释放资源。
    每次完成网格划分后应调用此函数以避免内存泄漏。
    """
    global _prime_client, _prime_model
    try:
        if _prime_client is not None:
            _prime_client.exit()
            _prime_client = None
            _prime_model = None
        return _ok(ok_message("Prime 会话已关闭", closed=True))
    except Exception as e:
        return _err(str(e))
