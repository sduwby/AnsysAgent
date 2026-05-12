"""
CAD导入工具：支持多种CAD格式导入到Ansys仿真环境。

支持格式：
- STEP/STP：ISO 10303标准交换格式
- IGES/IGS：初始图形交换规范
- STL：立体光刻格式（用于3D打印和网格）
- Parasolid：.x_t, .x_b（Siemens格式）
- SolidWorks：.sldprt, .sldasm
- CATIA：.CATPart, .CATProduct
- NX：.prt

每个函数返回包含 'success'、'result' 和可选 'error' 字段的字典。
"""

from __future__ import annotations

import os
from pathlib import Path

from tools.utils import _ok, _err, ok_message, ensure_parent_dir

# 支持的CAD格式
_SUPPORTED_FORMATS = {
    "step": {
        "extensions": [".step", ".stp"],
        "description": "STEP格式（ISO 10303标准）",
    },
    "iges": {
        "extensions": [".iges", ".igs"],
        "description": "IGES格式（初始图形交换规范）",
    },
    "stl": {
        "extensions": [".stl"],
        "description": "STL格式（立体光刻）",
    },
    "parasolid": {
        "extensions": [".x_t", ".x_b"],
        "description": "Parasolid格式",
    },
    "solidworks": {
        "extensions": [".sldprt", ".sldasm"],
        "description": "SolidWorks格式",
    },
    "catia": {
        "extensions": [".catpart", ".catproduct"],
        "description": "CATIA格式",
    },
    "nx": {
        "extensions": [".prt"],
        "description": "NX格式",
    },
}


def _detect_format(file_path: str) -> str | None:
    """检测文件格式"""
    ext = Path(file_path).suffix.lower()
    for fmt, info in _SUPPORTED_FORMATS.items():
        if ext in info["extensions"]:
            return fmt
    return None


# ---------------------------------------------------------------------------
# 工具：import_cad_file - 导入CAD文件到AEDT
# ---------------------------------------------------------------------------

def import_cad_file(
    file_path: str,
    import_type: str = "geometry",
    unit: str = "mm",
    simplify: bool = False,
    tolerance: float = 0.1,
) -> dict:
    """
    将CAD文件导入到Ansys AEDT中。

    Args:
        file_path: CAD文件路径
        import_type: 导入类型，"geometry"（几何）或 "mesh"（网格）
        unit: 长度单位，默认"mm"
        simplify: 是否简化几何，默认False
        tolerance: 简化公差（当前单位），默认0.1
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return _err(f"文件不存在: {file_path}")
        
        # 检测格式
        fmt = _detect_format(file_path)
        if fmt is None:
            return _err(f"不支持的文件格式: {Path(file_path).suffix}")
        
        # 获取AEDT应用
        from tools import maxwell_tools
        if maxwell_tools._aedt_app is None:
            return _err("未连接到AEDT，请先调用connect_aedt")
        
        app = maxwell_tools._aedt_app
        
        # 执行导入
        import_result = app.modeler.import_cad(
            file_path=file_path,
            import_type=import_type,
            unit=unit,
            simplify=simplify,
            tolerance=tolerance,
        )
        
        # 获取导入的对象数量
        obj_count = len(app.modeler.objects)
        
        return _ok({
            "file_path": file_path,
            "format": fmt,
            "format_description": _SUPPORTED_FORMATS[fmt]["description"],
            "import_type": import_type,
            "unit": unit,
            "object_count": obj_count,
            "message": f"CAD文件导入成功，共 {obj_count} 个对象",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：import_step_file - 导入STEP文件（便捷方法）
# ---------------------------------------------------------------------------

def import_step_file(
    file_path: str,
    unit: str = "mm",
    simplify: bool = False,
    tolerance: float = 0.1,
) -> dict:
    """
    导入STEP格式文件到AEDT。

    Args:
        file_path: STEP文件路径（.step 或 .stp）
        unit: 长度单位
        simplify: 是否简化几何
        tolerance: 简化公差
    """
    return import_cad_file(
        file_path=file_path,
        import_type="geometry",
        unit=unit,
        simplify=simplify,
        tolerance=tolerance,
    )


# ---------------------------------------------------------------------------
# 工具：import_stl_file - 导入STL文件（便捷方法）
# ---------------------------------------------------------------------------

def import_stl_file(
    file_path: str,
    unit: str = "mm",
) -> dict:
    """
    导入STL格式文件到AEDT。

    Args:
        file_path: STL文件路径
        unit: 长度单位
    """
    return import_cad_file(
        file_path=file_path,
        import_type="mesh",
        unit=unit,
        simplify=False,
        tolerance=0.1,
    )


# ---------------------------------------------------------------------------
# 工具：convert_cad_format - 转换CAD文件格式
# ---------------------------------------------------------------------------

def convert_cad_format(
    input_path: str,
    output_path: str,
    output_format: str = "step",
) -> dict:
    """
    将CAD文件转换为另一种格式。

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        output_format: 输出格式，支持 "step", "iges", "stl", "parasolid"
    """
    try:
        if not os.path.exists(input_path):
            return _err(f"输入文件不存在: {input_path}")
        
        if output_format not in _SUPPORTED_FORMATS:
            return _err(f"不支持的输出格式: {output_format}")
        
        ensure_parent_dir(output_path)
        
        # 添加正确的扩展名
        ext = _SUPPORTED_FORMATS[output_format]["extensions"][0]
        if not output_path.lower().endswith(tuple(_SUPPORTED_FORMATS[output_format]["extensions"])):
            output_path += ext
        
        # 使用AEDT进行转换
        from tools import maxwell_tools
        if maxwell_tools._aedt_app is None:
            return _err("未连接到AEDT，请先调用connect_aedt")
        
        app = maxwell_tools._aedt_app
        
        # 先导入再导出
        app.modeler.import_cad(file_path=input_path)
        
        # 导出为目标格式
        app.modeler.export_cad(
            file_path=output_path,
            export_format=output_format,
        )
        
        if not os.path.exists(output_path):
            return _err("格式转换失败，未生成输出文件")
        
        file_size = os.path.getsize(output_path)
        return _ok({
            "input_path": input_path,
            "output_path": output_path,
            "output_format": output_format,
            "file_size_kb": round(file_size / 1024, 1),
            "message": f"CAD文件已转换为 {output_format.upper()} 格式",
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：list_supported_cad_formats - 列出支持的CAD格式
# ---------------------------------------------------------------------------

def list_supported_cad_formats() -> dict:
    """
    列出所有支持的CAD导入格式。
    """
    formats = []
    for fmt, info in _SUPPORTED_FORMATS.items():
        formats.append({
            "format": fmt,
            "extensions": info["extensions"],
            "description": info["description"],
        })
    
    return _ok({
        "count": len(formats),
        "formats": formats,
        "message": f"支持 {len(formats)} 种CAD格式",
    })


# ---------------------------------------------------------------------------
# 工具：check_cad_file - 检查CAD文件有效性
# ---------------------------------------------------------------------------

def check_cad_file(file_path: str) -> dict:
    """
    检查CAD文件是否有效且可导入。

    Args:
        file_path: CAD文件路径
    """
    try:
        if not os.path.exists(file_path):
            return _err(f"文件不存在: {file_path}")
        
        file_size = os.path.getsize(file_path)
        fmt = _detect_format(file_path)
        
        if fmt is None:
            return _ok({
                "valid": False,
                "supported": False,
                "file_path": file_path,
                "file_size_kb": round(file_size / 1024, 1),
                "message": f"文件格式不支持: {Path(file_path).suffix}",
            })
        
        # 尝试读取文件头验证
        with open(file_path, 'rb') as f:
            header = f.read(100).decode('utf-8', errors='ignore')
        
        is_valid = False
        validation_info = ""
        
        if fmt == "step":
            is_valid = "ISO-10303" in header or "STEP" in header
            validation_info = "STEP文件格式验证"
        elif fmt == "iges":
            is_valid = "IGES" in header or "BDF" in header
            validation_info = "IGES文件格式验证"
        elif fmt == "stl":
            is_valid = "solid" in header.lower() or header[:6] == b'\x80\x00\x00\x00'
            validation_info = "STL文件格式验证"
        
        return _ok({
            "valid": is_valid,
            "supported": True,
            "format": fmt,
            "format_description": _SUPPORTED_FORMATS[fmt]["description"],
            "file_path": file_path,
            "file_size_kb": round(file_size / 1024, 1),
            "validation_info": validation_info,
            "message": f"文件检查完成，格式: {fmt}"
        })
    except Exception as e:
        return _err(str(e))


# ---------------------------------------------------------------------------
# 工具：batch_import_cad_files - 批量导入CAD文件
# ---------------------------------------------------------------------------

def batch_import_cad_files(
    file_paths: list[str],
    unit: str = "mm",
    simplify: bool = False,
) -> dict:
    """
    批量导入多个CAD文件到AEDT。

    Args:
        file_paths: CAD文件路径列表
        unit: 长度单位
        simplify: 是否简化几何
    """
    try:
        results = []
        success_count = 0
        fail_count = 0
        
        for file_path in file_paths:
            result = import_cad_file(
                file_path=file_path,
                unit=unit,
                simplify=simplify,
            )
            results.append({
                "file_path": file_path,
                "success": result["success"],
                "message": result.get("message") or result.get("error"),
            })
            
            if result["success"]:
                success_count += 1
            else:
                fail_count += 1
        
        return _ok({
            "total_files": len(file_paths),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results,
            "message": f"批量导入完成，成功 {success_count} 个，失败 {fail_count} 个",
        })
    except Exception as e:
        return _err(str(e))
